"""Load, validate and match `config/routing.yaml` (v2) rules (spec §15 deterministic match)."""
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..paths import repo_root
from .classify import CHANGE_TYPES, find_phrases

PROJECT_STAGES = ("new", "existing", "unknown")
RULE_KEYS = {"id", "description", "any", "regex", "require_any", "unless", "project", "select", "suppress",
             "pipeline", "explicit", "weight", "browser_exception"}


@dataclass
class RuleHit:
    rule: str
    select: list
    weight: int
    matched: list
    suppress: list = field(default_factory=list)
    pipeline: list = field(default_factory=list)
    explicit: bool = False
    browser_exception: bool = False  # the user explicitly asked for browser-level validation (D-035)


def load_routing(root: Path | None = None):
    with open((root or repo_root()) / "config" / "routing.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_hierarchy(root: Path | None = None):
    """{role: level} from config/priorities.yaml conflict_hierarchy (level 1 wins)."""
    with open((root or repo_root()) / "config" / "priorities.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {e["source"]: e["level"] for e in data.get("conflict_hierarchy") or []}


def _glob_match(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/").lstrip("./")
    if fnmatch.fnmatchcase(path, pattern):
        return True
    # `**/x` also matches `x` at the top level.
    return pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:])


def validate_routing(cfg, cards, hierarchy):
    """Problems with a routing config against the capability cards and the conflict hierarchy."""
    p = []
    if cfg.get("version") != 2:
        return [f"config/routing.yaml version must be 2, got {cfg.get('version')!r}"]
    domains = {cid.split("/", 1)[0] for cid in cards}
    ct = cfg.get("change_types") or {}
    listed = [e.get("type") for e in ct.get("order") or []]
    if sorted(listed) != sorted(CHANGE_TYPES):
        p.append(f"change_types.order must list each spec §54 type once; missing {sorted(set(CHANGE_TYPES) - set(listed))}, "
                 f"unknown {sorted(set(listed) - set(CHANGE_TYPES))}")
    for e in ct.get("order") or []:
        if not e.get("keywords"):
            p.append(f"change type {e.get('type')}: keywords must be non-empty")
    for rx in ct.get("ignore") or []:
        try:
            re.compile(rx)
        except re.error as exc:
            p.append(f"change_types.ignore: bad regex {rx!r}: {exc}")
    for dom, t in (ct.get("default_by_domain") or {}).items():
        if dom not in domains or t not in CHANGE_TYPES:
            p.append(f"change_types.default_by_domain: {dom} → {t} is not a known domain/type")
    if ct.get("fallback") not in CHANGE_TYPES:
        p.append("change_types.fallback must be a spec §54 type")
    for r in cfg.get("roles") or []:
        if r.get("role") not in hierarchy:
            p.append(f"roles: {r.get('match')} → unknown hierarchy role {r.get('role')!r}")
    if not any(r.get("match") == "*" for r in cfg.get("roles") or []):
        p.append("roles: needs a final catch-all `*` entry")
    seen = set()
    for rule in cfg.get("rules") or []:
        rid = rule.get("id")
        if not rid or rid in seen:
            p.append(f"rule {rid!r}: id missing or duplicated")
        seen.add(rid)
        unknown = set(rule) - RULE_KEYS
        if unknown:
            p.append(f"rule {rid}: unknown keys {sorted(unknown)}")
        if not rule.get("any") and not rule.get("regex"):
            p.append(f"rule {rid}: needs `any` keywords or `regex`")
        for rx in rule.get("regex") or []:
            try:
                re.compile(rx)
            except re.error as exc:
                p.append(f"rule {rid}: bad regex {rx!r}: {exc}")
        if not rule.get("select"):
            p.append(f"rule {rid}: select must be non-empty")
        for cid in rule.get("select") or []:
            card = cards.get(cid)
            if card is None:
                p.append(f"rule {rid}: selects unknown capability {cid}")
                continue
            mode = card["activation_conditions"]["mode"]
            if mode in ("fallback", "explicit") and not rule.get("explicit"):
                p.append(f"rule {rid}: {cid} is {mode}-only; the rule must be `explicit: true`")
            if mode == "internal":
                p.append(f"rule {rid}: {cid} is internal and is reached through dependencies, never routed")
            if not card["enabled"] or card.get("runtime_status") == "DISABLED_BY_POLICY":
                p.append(f"rule {rid}: {cid} is disabled by policy and can never be routed (D-035)")
        for target in rule.get("suppress") or []:
            if target not in cards and target not in domains:
                p.append(f"rule {rid}: suppresses unknown domain/capability {target}")
        for dom in rule.get("pipeline") or []:
            if dom not in domains:
                p.append(f"rule {rid}: pipeline names unknown domain {dom}")
        for stage in rule.get("project") or []:
            if stage not in PROJECT_STAGES:
                p.append(f"rule {rid}: project stage {stage!r} not in {PROJECT_STAGES}")
        if not isinstance(rule.get("weight", 1), int) or rule.get("weight", 1) < 1:
            p.append(f"rule {rid}: weight must be a positive integer")
    for i, entry in enumerate(cfg.get("paths") or []):
        if not entry.get("glob") or not entry.get("select"):
            p.append(f"paths[{i}]: needs glob and select")
        p += [f"paths[{i}]: unknown capability {c}" for c in entry.get("select") or [] if c not in cards]
    proj = cfg.get("project") or {}
    p += [f"project.existing_adds: unknown capability {c}" for c in proj.get("existing_adds") or [] if c not in cards]
    p += [f"project.new_forbids_domains: unknown domain {d}" for d in proj.get("new_forbids_domains") or []
          if d not in domains]
    p += [f"project.existing_change_types: unknown type {t}" for t in proj.get("existing_change_types") or []
          if t not in CHANGE_TYPES]
    return p


def match_rules(text: str, cfg, stage: str):
    """Every rule whose conditions hold for normalized `text` and the project stage."""
    hits = []
    for rule in cfg.get("rules") or []:
        if rule.get("project") and stage not in rule["project"]:
            continue
        matched = find_phrases(text, rule.get("any") or [])
        matched += [f"/{rx}/" for rx in rule.get("regex") or [] if re.search(rx, text)]
        if not matched:
            continue
        if rule.get("require_any") and not find_phrases(text, rule["require_any"]):
            continue
        if rule.get("unless") and find_phrases(text, rule["unless"]):
            continue
        hits.append(RuleHit(rule=rule["id"], select=list(rule["select"]), weight=rule.get("weight", 1),
                            matched=matched, suppress=list(rule.get("suppress") or []),
                            pipeline=list(rule.get("pipeline") or []), explicit=bool(rule.get("explicit")),
                            browser_exception=bool(rule.get("browser_exception"))))
    return hits


def match_paths(paths, cfg):
    hits = []
    for entry in cfg.get("paths") or []:
        matched = sorted({p for p in paths for g in entry["glob"] if _glob_match(p, g)})
        if matched:
            hits.append(RuleHit(rule=f"path:{entry['glob'][0]}", select=list(entry["select"]), weight=3,
                                matched=matched[:5]))
    return hits


def role_of(cid: str, roles):
    for r in roles:
        if fnmatch.fnmatchcase(cid, r["match"]):
            return r["role"]
    return "domain-specialists"
