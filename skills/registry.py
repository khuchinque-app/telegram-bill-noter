import importlib
import pkgutil
import inspect
from typing import Dict, Any, Type
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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
                        logger.info(f"Discovered skill: {name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {name}: {e}")

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
