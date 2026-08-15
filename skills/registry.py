import importlib
import pkgutil
from typing import Any, Dict, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_frontmatter(path: Path):
    """Parse `name:` / `description:` from a SKILL.md YAML frontmatter block."""
    name, description = "", ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return name, description
    if not text.startswith("---"):
        return name, description
    body = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    for line in body.splitlines():
        if line.startswith("name:") and not name:
            name = line.split(":", 1)[1].strip()
        elif line.startswith("description:") and not description:
            description = line.split(":", 1)[1].strip()
    return name, description


class SkillRegistry:
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            self.skills_dir = Path(__file__).parent
        else:
            self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> None:
        """Discovers all skills in the skills directory."""
        for finder, name, ispkg in pkgutil.iter_modules([str(self.skills_dir)]):
            if ispkg:
                try:
                    module = importlib.import_module(f"skills.{name}")
                    if hasattr(module, "skill_info"):
                        self.skills[name] = module.skill_info
                        self.skills[name]["module"] = module
                        # Surface progressive-disclosure skill sets.
                        self.skills[name]["units"] = self.discover_skill_units(name)
                        logger.info(f"Discovered skill: {name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {name}: {e}")

    def discover_skill_units(self, parent: str) -> List[Dict[str, Any]]:
        """Discover progressive-disclosure SKILL.md units under a skill dir.

        Walks `skills/<parent>/skills/**` for SKILL.md files and parses their
        frontmatter so the registry can list every skill set a skill ships.
        """
        units = []
        base = self.skills_dir / parent / "skills"
        if not base.is_dir():
            return units
        for skill_md in sorted(base.rglob("SKILL.md")):
            name, description = _parse_frontmatter(skill_md)
            if not name:
                continue
            units.append({
                "name": name,
                "description": description,
                "path": str(skill_md.relative_to(self.skills_dir)),
            })
        return units

    def load(self, skill_name: str) -> Any:
        """Loads a specific skill by name."""
        if skill_name not in self.skills:
            raise ValueError(f"Skill {skill_name} not found")
        
        skill_info = self.skills[skill_name]
        module = skill_info["module"]
        entry_point = skill_info.get("entry_point")
        
        if not entry_point:
            return module
            
        module_name, class_name = entry_point.split(":")
        entry_module = importlib.import_module(f"skills.{skill_name}.{module_name}")
        entry_class = getattr(entry_module, class_name)
        
        return entry_class()
