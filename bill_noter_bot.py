"""Entry point for the Bill Noter Telegram bot.

Run:
    python bill_noter_bot.py                 # real bot (needs BILL_NOTER_TOKEN)
    python bill_noter_bot.py --self-test     # offline test of parsing + storage
    python bill_noter_bot.py --dry-run       # read messages from stdin, print notes

Set BILL_NOTER_TOKEN (and optionally BILL_NOTER_STORE) in the environment or a .env file.
"""

import argparse
import asyncio
import sys

from bill_noter import NotesStore, parse_prices, extract_label


SAMPLE_MESSAGES = [
    "Lunch at the restaurant 12.50",
    "Taxi from airport €23,40",
    "Groceries 1,250.75 USD",
    "Internet bill 45",
    "Just chatting, no price here",
    "Beer 5 and snacks 3.20",
    "Rent 1.200,00",
]


def self_test(store_path: str) -> int:
    print("=== Bill Noter self-test ===")
    store = NotesStore(store_path)
    for text in SAMPLE_MESSAGES:
        prices = parse_prices(text)
        if not prices:
            print(f"[skip] {text!r}: no price")
            continue
        for p in prices:
            label = extract_label(text, [p])
            print(f"[note] {label!r} -> {p.value} {p.currency!r} (raw={p.raw!r})")
    print("=== done ===")
    return 0


def dry_run(store_path: str) -> int:
    print("Dry-run: type messages, Ctrl-D to end.")
    store = NotesStore(store_path)
    for line in sys.stdin:
        text = line.rstrip("\n")
        if not text:
            continue
        prices = parse_prices(text)
        if not prices:
            print(f"  no price found in: {text!r}")
            continue
        for p in prices:
            label = extract_label(text, [p])
            store.add(__make_note(text, label, p))
            print(f"  NOTED: {label} = {p.value} {p.currency}")
    return 0


def __make_note(text, label, price):
    from bill_noter import Note
    return Note(
        chat_id=0, chat_title="dry-run", message_id=0, author_id=0,
        author_name="dry-run", label=label, value=price.value,
        currency=price.currency, raw=text,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bill Noter Telegram bot")
    parser.add_argument("--self-test", action="store_true",
                        help="offline test of parsing and storage")
    parser.add_argument("--dry-run", action="store_true",
                        help="read messages from stdin and store notes")
    parser.add_argument("--store", default="notes.json", help="notes JSON path")
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.store)
    if args.dry_run:
        return dry_run(args.store)

    from bill_noter.bot import main as bot_main
    bot_main()
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
