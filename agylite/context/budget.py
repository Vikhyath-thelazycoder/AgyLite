"""Context budgets (spec §47, D-014): load and validate config/budgets.yaml; track spending per assembly."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..paths import repo_root

LEVEL_KEYS = {"L0": "max_tokens", "L1": "max_tokens_per_domain", "L2": "max_tokens_per_task", "L3": "max_tokens_per_fetch"}
OTHER_KEYS = ("reference_depth", "code_files_per_task", "project_doc_sections_per_turn", "semantic_results")


def load_budgets(root: Path | None = None):
    with open((root or repo_root()) / "config" / "budgets.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_budgets(cfg):
    """Every limit present, a positive integer, and documented with a `why` (spec §47 "document why each limit exists")."""
    p = []
    if cfg.get("version") != 1:
        p.append("budgets.yaml version must be 1")
    levels = cfg.get("levels") or {}
    for level, key in LEVEL_KEYS.items():
        entry = levels.get(level) or {}
        if not (isinstance(entry.get(key), int) and entry[key] > 0):
            p.append(f"levels.{level}.{key} must be a positive integer")
        if not str(entry.get("why") or "").strip():
            p.append(f"levels.{level}: missing `why`")
    l2 = levels.get("L2") or {}
    if not (isinstance(l2.get("max_whole_skills_per_task"), int) and l2["max_whole_skills_per_task"] > 0):
        p.append("levels.L2.max_whole_skills_per_task must be a positive integer")
    if l2.get("primary_skill") != "whole":
        p.append("levels.L2.primary_skill must be `whole` (IMPLEMENTATION_PLAN §2.1: skills are never sliced)")
    if (levels.get("L3") or {}).get("explicit_only") is not True:
        p.append("levels.L3.explicit_only must be true (spec §16: never default to Level 3)")
    for key in OTHER_KEYS:
        entry = cfg.get(key) or {}
        if not (isinstance(entry.get("value"), int) and entry["value"] > 0) or not str(entry.get("why") or "").strip():
            p.append(f"{key} needs a positive integer `value` and a `why`")
    return p


@dataclass
class Budget:
    limit: int
    used: int = 0

    @property
    def left(self) -> int:
        return max(self.limit - self.used, 0)

    def fits(self, tokens: int) -> bool:
        return self.used + tokens <= self.limit

    def take(self, tokens: int) -> None:
        self.used += tokens
