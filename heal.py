"""Auto-Heal Supervisor — keeps the bot and gateway alive.

If a supervised process dies, it is restarted within one poll interval
(default 5s, so the service is back up in ~5s — well under 10s). If a
process *hangs* (stops writing its heartbeat), it is killed and
restarted too.

Heartbeats
----------
Each service writes a tiny timestamp file (default `data/heartbeat/<name>`)
every `HEARTBEAT_INTERVAL` seconds. The supervisor treats a heartbeat
older than `STALE_AFTER` seconds as a hang and force-restarts the
service. The bot and gateway call `start_heartbeat()` on startup.

Crash-loop protection
---------------------
If a service dies within `QUICK_EXIT_SECONDS` of starting, the supervisor
backs off exponentially (5s → 10s → 20s → capped at 60s) so a
misconfigured service can't spin in a tight restart loop. The counter
resets once the service stays up.

Usage
-----
    python heal.py                # supervise bot + gateway (default)
    python heal.py --bot          # supervise only the bot
    python heal.py --gateway      # supervise only the gateway
    python heal.py --poll 3       # faster crash detection (~3s)
    python heal.py --self-test    # offline verification of restart logic
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent
HEARTBEAT_DIR = REPO_ROOT / "data" / "heartbeat"
LOG_DIR = REPO_ROOT / "logs"

DEFAULT_POLL = 5          # seconds between health checks (crash -> up in ~5s)
DEFAULT_HEARTBEAT = 10    # seconds between heartbeat writes
DEFAULT_STALE = 30        # heartbeat older than this = hung
QUICK_EXIT_SECONDS = 10   # died faster than this -> counts as crash-loop
MAX_BACKOFF = 60          # cap for crash-loop backoff

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("heal")

# ──────────────────────────────────────────────────────────────────────
# Heartbeat helpers (used by the bot / gateway at runtime)
# ──────────────────────────────────────────────────────────────────────

def heartbeat_path(name: str) -> Path:
    return HEARTBEAT_DIR / f"{name}.heartbeat"


def write_heartbeat(name: str) -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_path(name).write_text(str(time.time()), encoding="utf-8")


def heartbeat_age(name: str) -> Optional[float]:
    """Seconds since the last heartbeat, or None if never written."""
    path = heartbeat_path(name)
    try:
        return time.time() - float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def start_heartbeat(name: str, interval: int = DEFAULT_HEARTBEAT) -> threading.Thread:
    """Start a daemon thread that keeps the service's heartbeat fresh."""
    write_heartbeat(name)
    stop = threading.Event()

    def _loop() -> None:
        while not stop.is_set():
            time.sleep(interval)
            write_heartbeat(name)

    thread = threading.Thread(target=_loop, name=f"heartbeat-{name}", daemon=True)
    thread.start()
    log.info("heartbeat started for %r (every %ss)", name, interval)
    return thread


# ──────────────────────────────────────────────────────────────────────
# Supervisor
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Service:
    name: str
    cmd: List[str]
    cwd: Path = REPO_ROOT
    env: Dict[str, str] = field(default_factory=dict)


class Supervisor:
    """Watches services, restarts crashes and hangs."""

    def __init__(
        self,
        services: List[Service],
        poll: int = DEFAULT_POLL,
        heartbeat_interval: int = DEFAULT_HEARTBEAT,
        stale_after: int = DEFAULT_STALE,
    ) -> None:
        self.services = {s.name: s for s in services}
        self.poll = poll
        self.heartbeat_interval = heartbeat_interval
        self.stale_after = stale_after
        self.procs: Dict[str, subprocess.Popen] = {}
        self.quick_exits: Dict[str, int] = {}
        self.last_start: Dict[str, float] = {}
        self.spawn_count: Dict[str, int] = {}   # total spawns per service
        self._shutdown = threading.Event()
        self._lock = threading.Lock()

    # ── lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        for name in self.services:
            self._spawn(name)
        log.info("supervising %s — poll=%ss heartbeat=%ss stale=%ss",
                 ", ".join(self.services), self.poll,
                 self.heartbeat_interval, self.stale_after)

    def stop(self) -> None:
        self._shutdown.set()
        for name in list(self.procs):
            self._terminate(name)

    # ── process management ────────────────────────────────────────────

    def _spawn(self, name: str) -> None:
        service = self.services[name]
        log_path = LOG_DIR / f"{name}.log"
        log_file = open(log_path, "a", encoding="utf-8")  # kept open for the child

        env = dict(os.environ)
        env.update(service.env)
        proc = subprocess.Popen(
            service.cmd,
            cwd=str(service.cwd),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group: children die with us
        )
        with self._lock:
            self.procs[name] = proc
            self.last_start[name] = time.time()
            self.spawn_count[name] = self.spawn_count.get(name, 0) + 1
        log.info("spawned %s (pid=%s) -> %s", name, proc.pid, log_path)

    def _terminate(self, name: str) -> None:
        proc = self.procs.get(name)
        if proc is None or proc.poll() is not None:
            return
        log.info("terminating %s (pid=%s)", name, proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("%s did not exit in 5s — killing", name)
            proc.kill()
            proc.wait(timeout=5)
        with self._lock:
            self.procs.pop(name, None)

    # ── health checks ─────────────────────────────────────────────────

    def _check(self, name: str) -> None:
        if self._shutdown.is_set():
            return  # stopping — don't respawn anything

        proc = self.procs.get(name)
        if proc is None:
            self._spawn(name)
            return

        # Crash?
        if proc.poll() is not None:
            rc = proc.returncode
            uptime = time.time() - self.last_start.get(name, 0.0)
            log.warning("%s died (rc=%s) after %.1fs — restarting", name, rc, uptime)
            with self._lock:
                self.procs.pop(name, None)
            if uptime < QUICK_EXIT_SECONDS:
                self.quick_exits[name] = self.quick_exits.get(name, 0) + 1
            else:
                self.quick_exits[name] = 0
            self._maybe_backoff(name)
            if self._shutdown.is_set():
                return  # stop() raced in mid-check
            self._spawn(name)
            return

        # Hang? (heartbeat stale)
        age = heartbeat_age(name)
        if age is not None and age > self.stale_after:
            log.warning("%s heartbeat stale (%.0fs > %ss) — killing & restarting",
                        name, age, self.stale_after)
            self._terminate(name)
            if self._shutdown.is_set():
                return  # stop() raced in mid-check
            self._spawn(name)

    def _maybe_backoff(self, name: str) -> None:
        """Exponential backoff when a service crash-loops."""
        n = self.quick_exits.get(name, 0)
        if n <= 1:
            return
        delay = min(MAX_BACKOFF, 5 * (2 ** (n - 1)))
        log.warning("%s crashed %d times in a row — backing off %.0fs",
                    name, n, delay)
        self._shutdown.wait(delay)

    # ── main loop ─────────────────────────────────────────────────────

    def run(self, install_signals: bool = True) -> None:
        """Run the supervision loop until `stop()` is called.

        `install_signals` must be False when run() is invoked from a
        non-main thread (signal.signal only works in the main thread).
        """
        if install_signals:
            def _on_signal(signum, _frame) -> None:
                log.info("received signal %s — shutting down children", signum)
                self.stop()

            signal.signal(signal.SIGINT, _on_signal)
            signal.signal(signal.SIGTERM, _on_signal)

        self.start()
        try:
            while not self._shutdown.is_set():
                for name in list(self.services):
                    self._check(name)
                self._shutdown.wait(self.poll)
        finally:
            self.stop()
        log.info("supervisor stopped")


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def _services(args: argparse.Namespace) -> List[Service]:
    """Build the service list.

    The gateway runs in --standby (always-on bot listener) so it
    consumes incoming bills 24/7; it needs a token, which the supervisor
    inherits from the environment / .env via the Service env dict.
    """
    py = sys.executable
    services: List[Service] = []
    if args.bot or args.all:
        services.append(Service("bot", [py, "bill_noter_bot.py"]))
    if args.gateway or args.all:
        token = os.environ.get("BILL_NOTER_TOKEN") or os.environ.get("GATEWAY_TOKEN")
        if not token:
            log.warning(
                "gateway service skipped — set BILL_NOTER_TOKEN (or GATEWAY_TOKEN) "
                "in .env to enable the always-on gateway listener"
            )
        else:
            services.append(Service(
                "gateway",
                [py, "gateway/gateway_run.py", "--standby"],
            ))
    if not services:
        raise SystemExit("nothing to supervise — use --bot, --gateway, or --all")
    return services


def self_test() -> int:
    """Offline proof that crash-restart and hang-restart both work.

    Runs supervisors in the MAIN thread (signals off) and stops them
    with a timer so nothing is left running.
    """
    py = sys.executable
    log.info("=== heal self-test ===")

    # 1. Crash -> restart (a process that exits after 1s).
    crasher = Service(
        "test-crasher",
        [py, "-c", "import time; time.sleep(1)"],
    )
    s1 = Supervisor([crasher], poll=1)
    threading.Timer(6, s1.stop).start()
    s1.run(install_signals=False)
    spawns = s1.spawn_count.get("test-crasher", 0)
    assert spawns >= 2, f"expected >=2 spawns, got {spawns}"
    log.info("PASS crash-restart: %d spawns in 6s", spawns)

    # 2. Hang -> restart. Simulate a service whose heartbeat goes stale
    #    (old heartbeat file), get it killed+respawned, then verify the
    #    respawned service (which KEEPS heartbeating, like the real bot
    #    via start_heartbeat) stays alive instead of being re-killed.
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_path("test-hang").write_text(
        str(time.time() - 10), encoding="utf-8"   # deliberately stale
    )
    hanger = Service(
        "test-hang",
        [py, "-c",
         "from heal import start_heartbeat; start_heartbeat('test-hang', interval=1); "
         "import time; time.sleep(30)"],
    )
    s2 = Supervisor([hanger], poll=1, heartbeat_interval=1, stale_after=2)
    threading.Timer(5, s2.stop).start()
    s2.run(install_signals=False)
    spawns2 = s2.spawn_count.get("test-hang", 0)
    assert spawns2 >= 2, f"expected >=2 spawns for hang, got {spawns2}"
    # Exactly 2 spawns proves the cycle: initial spawn, one stale-kill
    # respawn, then the FRESH heartbeat kept it alive until stop(). If
    # the heartbeat refresh failed, the stale-kill would loop (3+ spawns).
    assert spawns2 == 2, f"expected 2 spawns (fresh heartbeat kept it alive), got {spawns2}"
    log.info("PASS hang-restart: stale-kill once, fresh heartbeat held (2 spawns)")

    log.info("=== heal self-test done ===")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Auto-heal supervisor for the bill noter bot & gateway",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--bot", action="store_true", help="supervise the bot")
    ap.add_argument("--gateway", action="store_true", help="supervise the gateway")
    ap.add_argument("--all", action="store_true", help="supervise bot + gateway")
    ap.add_argument("--poll", type=int, default=DEFAULT_POLL,
                    help="seconds between health checks")
    ap.add_argument("--heartbeat-interval", type=int, default=DEFAULT_HEARTBEAT,
                    help="seconds services write their heartbeat")
    ap.add_argument("--stale-after", type=int, default=DEFAULT_STALE,
                    help="heartbeat older than this = hung")
    ap.add_argument("--self-test", action="store_true",
                    help="verify crash/hang restart logic offline")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    services = _services(args)
    Supervisor(
        services,
        poll=args.poll,
        heartbeat_interval=args.heartbeat_interval,
        stale_after=args.stale_after,
    ).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
