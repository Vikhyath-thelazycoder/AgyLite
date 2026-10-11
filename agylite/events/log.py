"""Per-project append-only event log (doc 15): `$AGYLITE_HOME/projects/<id>/events/<YYYY-MM-DD>.jsonl`.

Every record is redacted before it is written. One `write()` of one line under the project's `events` lock, so
concurrent sessions never interleave partial lines. Emitting never raises into the caller: observability must not
break the work it observes.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

from ..isolation.guard import guard_for
from ..isolation.locks import project_lock
from .redact import redact
from .schema import envelope

DEFAULT_HOST = "cli"
CURRENT_SESSION = "current.json"     # written by `agylite bootstrap` (the host's SessionStart hook)
SESSION_TTL_S = 12 * 3600


def sessions_dir(project):
    return project.data_dir / "sessions"


def current_session(project):
    """The session id the host last bootstrapped for this project (within SESSION_TTL_S), else None.
    Host shells do not inherit AGYLITE_SESSION_ID from the hook, so CLI events fall back to this pointer; with two
    concurrent sessions on one project the newest bootstrap wins."""
    try:
        path = guard_for(project).check(sessions_dir(project) / CURRENT_SESSION)
        if time.time() - path.stat().st_mtime > SESSION_TTL_S:
            return None
        return json.loads(path.read_text(encoding="utf-8")).get("session_id")
    except (OSError, ValueError, AttributeError, PermissionError):
        return None


def events_dir(project):
    return project.data_dir / "events"


def emit(project, event, **fields):
    """Append one redacted event; returns the record written, or None if logging failed (reported on stderr)."""
    if project is None:
        return None
    try:
        if not fields.get("session_id"):
            fields["session_id"] = os.environ.get("AGYLITE_SESSION_ID") or current_session(project)
        if not fields.get("host"):
            fields["host"] = os.environ.get("AGYLITE_HOST", DEFAULT_HOST)
        record = redact(envelope(event, project_id=project.project_id, **fields))
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = guard_for(project).check(events_dir(project) / f"{day}.jsonl", "write")
        line = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with project_lock(project, "events"):
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
        return record
    except Exception as exc:   # noqa: BLE001 — never break the observed operation
        print(f"agylite: event {event} not logged: {exc}", file=sys.stderr)
        return None


def read(project, *, event=None, session_id=None, limit=None, days=None):
    """Events in time order, optionally filtered; the newest `limit` when given."""
    d = events_dir(project)
    files = sorted(d.glob("*.jsonl")) if d.is_dir() else []
    if days:
        files = files[-days:]
    out = []
    for f in files:
        for line in guard_for(project).check(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if event and rec["event"] != event:
                continue
            if session_id and rec.get("session_id") != session_id:
                continue
            out.append(rec)
    return out[-limit:] if limit else out


def _on_violation(project, path, reason, mode):
    emit(project, "ISOLATION_VIOLATION_BLOCKED", severity="high",
         details={"path": path, "reason": reason, "mode": mode})


def install_hooks():
    """Connect isolation violations to the event log (idempotent; called by the CLI)."""
    from ..isolation.guard import on_violation
    on_violation(_on_violation)
