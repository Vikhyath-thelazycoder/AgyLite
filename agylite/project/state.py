"""Compact, cheap-to-read project state (spec §18, D-011): `<project>/.agylite/`.

state.yaml (identity, stage, stack, plan pointer, answers, last verification) · plan-index.yaml (P10 plan_index) ·
decisions.yaml (P10 decisions) · verification.yaml (verification history). Full documents stay in docs/ and are read
by section only when needed (spec §48–49).
"""
from datetime import datetime, timezone

import yaml

from ..events.log import emit
from ..isolation import atomic
from ..isolation.guard import guard_for
from ..isolation.locks import project_lock
from ..verify import policy

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)    # libyaml when available: state reads stay cheap

STATE_FILE = "state.yaml"
VERIFICATION_FILE = "verification.yaml"
SCHEMA_VERSION = 1
DEFAULT_PLAN = "docs/IMPLEMENTATION_PLAN.md"
STAGES = ("new", "existing")


class StateError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_yaml(path):
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_LOADER)  # noqa: S506 — a SafeLoader variant


def write_yaml(path, data):
    """Atomic write (P11): no partial file is ever visible to a concurrent reader."""
    atomic.write_yaml(path, data)


def checked(project, path, mode="read"):
    """Every project-scoped path goes through the isolation guard (P11, doc 14 §4)."""
    return guard_for(project).check(path, mode)


def state_path(project):
    return project.state_dir / STATE_FILE


def load_state(project):
    return read_yaml(checked(project, state_path(project)))


def require_state(project):
    state = load_state(project)
    if state is None:
        raise StateError(f"no project state in {project.state_dir} (run `agylite project init`)")
    return state


def new_state(project, stage: str, stack=(), plan_path: str = DEFAULT_PLAN):
    if stage not in STAGES:
        raise StateError(f"stage must be one of {STAGES}")
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {"name": project.name, "project_id": project.project_id, "created": now(), "stage": stage},
        "stack": list(stack),
        "plan": {"path": plan_path, "current_phase": None},
        "answers": {},
        "verification": verification_block(),
        "updated": now(),
    }


def verification_block(existing=None):
    """state.yaml `verification`: the global policy (D-035) + this project's last result. Policy fields are always
    re-derived from config/verification.yaml, so no project can carry a different mode."""
    block = policy.state_block(policy.load_policy())
    block["last"] = (existing or {}).get("last")
    block["last_task"] = (existing or {}).get("last_task")     # newest result tied to a plan task; kept across runs
    return block


def save_state(project, state):
    with project_lock(project, "state"):
        state["updated"] = now()
        write_yaml(checked(project, state_path(project), "write"), state)


def update_state(project, mutate):
    """Locked read-modify-write of state.yaml (no lost update between concurrent sessions); returns the new state."""
    with project_lock(project, "state"):
        state = require_state(project)
        mutate(state)
        save_state(project, state)
        return state


def record_verification(project, task: str | None, result: str, evidence: str | None):
    entry = {"task": task, "result": result, "evidence": evidence, "at": now()}
    path = checked(project, project.state_dir / VERIFICATION_FILE, "write")
    with project_lock(project, "verification"):
        data = read_yaml(path) or {"schema_version": SCHEMA_VERSION, "results": []}
        data["results"].append(entry)
        write_yaml(path, data)
    def apply(s):
        block = {**verification_block(s.get("verification")), "last": entry}
        if task:
            block["last_task"] = entry
        s["verification"] = block
    update_state(project, apply)
    return entry



def summary_lines(state, index=None, pending=()):
    """Compact lines for L0 (spec §19.1): stage/stack, phase + active tasks, pending questions, last verification."""
    lines = [f"{state['project']['stage']} project · stack {', '.join(state.get('stack') or []) or 'unknown'}"]
    if index:
        cur = next((p for p in index["phases"] if p["phase_id"] == index.get("current_phase")), None)
        if cur:
            active = ", ".join(cur["active_tasks"]) or "none"
            lines.append(f"phase {cur['phase_id']} {cur['phase_name']} ({cur['status']}) · active tasks: {active}")
        counts = {}
        for p in index["phases"]:
            counts[p["status"]] = counts.get(p["status"], 0) + 1
        lines.append("phases: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
    open_blocking = [q for q in state.get("pending_questions") or [] if q not in (state.get("answers") or {})]
    if open_blocking and not pending:
        lines.append(f"unanswered BLOCKING questions: {', '.join(open_blocking)} (`agylite project answer <id> …`)")
    if pending:
        by = {}
        for q in pending:
            by[q["priority"]] = by.get(q["priority"], 0) + 1
        lines.append("pending questions: " + ", ".join(f"{n} {p}" for p, n in by.items()))
    ver = state.get("verification") or {}
    lines.append(f"verification: {ver.get('mode') or policy.MODE} (UI work also needs `agylite verify --browser`)")
    last = ver.get("last")
    if last:
        lines.append(" ".join(f"last verification: {last['result']} {last.get('task') or ''} at {last['at']}".split()))
    last_task = ver.get("last_task")
    if last_task and last_task != last:
        lines.append(f"last task verification: {last_task['task']} {last_task['result']} at {last_task['at']}")
    return lines
