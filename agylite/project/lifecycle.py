"""Project lifecycle (spec §19, §25): completion states, new-vs-existing detection, stack detection, session start."""
import json
import re
from pathlib import Path

from .state import checked, now, read_yaml, write_yaml

# Spec §25: never just DONE / NOT DONE.
COMPLETION_STATES = ("NOT_STARTED", "PLANNED", "IN_PROGRESS", "PARTIALLY_COMPLETE", "BLOCKED",
                     "READY_FOR_VERIFICATION", "VERIFIED", "COMPLETED", "INTENTIONALLY_DEFERRED")
ACTIVE_STATES = ("IN_PROGRESS", "BLOCKED", "READY_FOR_VERIFICATION", "PARTIALLY_COMPLETE")
DONE_STATES = ("VERIFIED", "COMPLETED")
# COMPLETED only after verification evidence exists (spec §25, completion discipline).
TRANSITIONS = {
    "NOT_STARTED": {"PLANNED", "IN_PROGRESS", "INTENTIONALLY_DEFERRED", "BLOCKED"},
    "PLANNED": {"IN_PROGRESS", "BLOCKED", "INTENTIONALLY_DEFERRED", "NOT_STARTED"},
    "IN_PROGRESS": {"PARTIALLY_COMPLETE", "BLOCKED", "READY_FOR_VERIFICATION", "INTENTIONALLY_DEFERRED", "PLANNED"},
    "PARTIALLY_COMPLETE": {"IN_PROGRESS", "BLOCKED", "READY_FOR_VERIFICATION", "INTENTIONALLY_DEFERRED"},
    "BLOCKED": {"IN_PROGRESS", "PLANNED", "INTENTIONALLY_DEFERRED"},
    "READY_FOR_VERIFICATION": {"VERIFIED", "IN_PROGRESS", "BLOCKED"},
    "VERIFIED": {"COMPLETED", "IN_PROGRESS"},
    "COMPLETED": {"IN_PROGRESS"},
    "INTENTIONALLY_DEFERRED": {"PLANNED", "IN_PROGRESS"},
}

CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".swift",
                 ".vue", ".svelte", ".dart", ".c", ".cc", ".cpp", ".h", ".scala", ".ex", ".exs", ".html", ".css"}
MANIFESTS = ("package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "Gemfile", "pom.xml",
             "build.gradle", "build.gradle.kts", "composer.json", "pubspec.yaml", "Package.swift", "mix.exs")
SKIP_DIRS = {".git", ".agylite", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "docs", ".next"}
STACK_MARKERS = {   # dependency name → stack tag
    "react": "react", "next": "next", "vue": "vue", "nuxt": "nuxt", "svelte": "svelte", "@angular/core": "angular",
    "express": "express", "@nestjs/core": "nestjs", "fastify": "fastify", "prisma": "prisma", "@prisma/client": "prisma",
    "django": "django", "flask": "flask", "fastapi": "fastapi", "sqlalchemy": "sqlalchemy", "psycopg2": "postgres",
    "psycopg": "postgres", "pg": "postgres", "mongoose": "mongodb", "stripe": "stripe", "tailwindcss": "tailwind",
}
PYTHON_MARKERS = ("django", "flask", "fastapi", "sqlalchemy", "psycopg2", "psycopg", "stripe")


class TransitionError(ValueError):
    pass


def check_transition(old: str, new: str, evidence: str | None = None):
    if new not in COMPLETION_STATES:
        raise TransitionError(f"unknown status {new}; use one of {', '.join(COMPLETION_STATES)}")
    if old == new:
        return
    if old in TRANSITIONS and new not in TRANSITIONS[old]:
        raise TransitionError(f"{old} → {new} is not allowed (allowed: {', '.join(sorted(TRANSITIONS[old]))})")
    if new in DONE_STATES and not evidence:
        raise TransitionError(f"{new} needs verification evidence (--evidence)")


def _walk(root: Path, depth=3):
    stack = [(root, 0)]
    while stack:
        d, level = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if level < depth and e.name not in SKIP_DIRS and not e.name.startswith("."):
                    stack.append((e, level + 1))
            else:
                yield e


def detect_stage(root: Path, state=None) -> str:
    """Recorded stage wins; otherwise existing if a manifest or source file exists (spec §19.2)."""
    if state and state.get("project", {}).get("stage"):
        return state["project"]["stage"]
    if any((root / m).is_file() for m in MANIFESTS):
        return "existing"
    return "existing" if any(f.suffix in CODE_SUFFIXES for f in _walk(root)) else "new"


def detect_stack(root: Path):
    """Stack tags from manifests (language + notable frameworks); reads only manifest files."""
    tags = []
    pkg = root / "package.json"
    if pkg.is_file():
        tags.append("node")
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        tags += [STACK_MARKERS[d] for d in deps if d in STACK_MARKERS]
        if "typescript" in deps:
            tags.append("typescript")
    py_text = ""
    for name in ("pyproject.toml", "requirements.txt"):
        if (root / name).is_file():
            py_text += (root / name).read_text(encoding="utf-8", errors="ignore").lower()
    if py_text:
        tags.append("python")
        tags += [STACK_MARKERS[dep] for dep in PYTHON_MARKERS
                 if re.search(rf"(?<![\w-]){re.escape(dep)}(?![\w-])", py_text)]
    for manifest, tag in (("go.mod", "go"), ("Cargo.toml", "rust"), ("Gemfile", "ruby"), ("pom.xml", "java"),
                          ("build.gradle", "java"), ("build.gradle.kts", "kotlin"), ("composer.json", "php"),
                          ("pubspec.yaml", "dart"), ("Package.swift", "swift"), ("mix.exs", "elixir")):
        if (root / manifest).is_file():
            tags.append(tag)
    return list(dict.fromkeys(tags))


def start_session(project, session_id: str, host: str):
    """Record a session (spec §19.1) under the project's machine-local data dir; returns the session record."""
    path = checked(project, project.data_dir / "sessions" / session_id / "session.yaml", "write")
    record = read_yaml(path)
    if record is None:
        record = {"session_id": session_id, "project_id": project.project_id, "host": host, "started": now(),
                  "root": str(project.root)}
        write_yaml(path, record)
        record = dict(record, new=True)
    from ..events.log import CURRENT_SESSION, sessions_dir
    from ..isolation import atomic
    pointer = checked(project, sessions_dir(project) / CURRENT_SESSION, "write")
    atomic.write_text(pointer, json.dumps({"session_id": session_id, "host": host, "at": now()}))
    return record


# ── Engineering lifecycle (P13, config/lifecycle.yaml) ──────────────────────────────────────────────────────────
STEP_ORDER = ("UNDERSTAND", "PLAN", "IMPLEMENT", "TEST", "VERIFY", "RECONCILE")
OPTIONAL_STEPS = ("INSPIRATION",)   # MP4 §3.2: inserted by steps_for when the route needs it, never listed per type


def load_lifecycle(root: Path | None = None):
    import yaml

    from ..paths import repo_root
    with open((root or repo_root()) / "config" / "lifecycle.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_lifecycle(cfg, change_types=()) -> list:
    """Every step defined with purpose/commands/exit; every change-type entry uses known steps and ends in RECONCILE."""
    p = []
    if cfg.get("version") != 1:
        p.append("lifecycle.yaml version must be 1")
    steps = cfg.get("steps") or {}
    if tuple(s for s in steps if s not in OPTIONAL_STEPS) != STEP_ORDER:
        p.append(f"steps must be {' → '.join(STEP_ORDER)}")
    for name, step in steps.items():
        for key in ("purpose", "commands", "exit"):
            if not (step or {}).get(key):
                p.append(f"step {name}: missing {key}")
    types = cfg.get("change_types") or {}
    if "default" not in types:
        p.append("change_types.default missing")
    for t, entry in types.items():
        if t != "default" and change_types and t not in change_types:
            p.append(f"change_types.{t}: unknown change type")
        seq = (entry or {}).get("steps") or []
        bad = [s for s in seq if s not in steps]
        if bad:
            p.append(f"change_types.{t}: unknown steps {bad}")
        if not seq or seq[-1] != "RECONCILE":
            p.append(f"change_types.{t}: must end with RECONCILE")
        for s in ((entry or {}).get("rules") or {}):
            if s not in seq:
                p.append(f"change_types.{t}: rule for {s}, which is not one of its steps")
    return p


def steps_for(cfg, change_type: str, stage: str = "unknown", capabilities=()):
    """The ordered lifecycle for one request: step, purpose, the OS commands for this project stage, exit, rule.
    MP4 §3.2: a DESIGN_CHANGE that routes design/inspiration-extract gets INSPIRATION before PLAN."""
    types = cfg.get("change_types") or {}
    entry = types.get(change_type) or types.get("default") or {}
    rules = entry.get("rules") or {}
    names = list(entry.get("steps") or [])
    if "design/inspiration-extract" in capabilities and "INSPIRATION" in cfg["steps"] and "INSPIRATION" not in names:
        names.insert(names.index("PLAN") if "PLAN" in names else 0, "INSPIRATION")
    out = []
    for name in names:
        step = cfg["steps"][name]
        cmds = step["commands"]
        chosen = cmds.get(stage) or cmds.get("any") or cmds.get("existing" if stage != "new" else "new") or []
        item = {"step": name, "commands": list(chosen), "exit": step["exit"]}
        if name in rules:
            item["rule"] = rules[name]
        out.append(item)
    return out
