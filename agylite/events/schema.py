"""Event envelope (spec §30, doc 15, D-017). One JSON object per line in the project's event log."""
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = 1
EVENT_TYPES = (
    # spec §30
    "SESSION_STARTED", "PROJECT_DETECTED", "DOMAIN_SELECTED", "CAPABILITIES_SELECTED", "CONTEXT_LOADED",
    "TASK_STARTED", "TASK_BLOCKED", "TASK_COMPLETED", "VERIFICATION_STARTED", "VERIFICATION_PASSED",
    "VERIFICATION_FAILED", "STATE_UPDATED", "PHASE_CHANGED", "DASHBOARD_STARTED", "DASHBOARD_SLEEPING",
    "UPSTREAM_UPDATED", "UPSTREAM_ROLLBACK",
    # doc 15 additions; D-035 replaced BROWSER_FALLBACK_ACTIVATED (no automatic browser fallback exists any more)
    "BROWSER_EXCEPTION_REQUESTED", "ISOLATION_VIOLATION_BLOCKED", "RISK_DETECTED",
    # plan task reached verification / was verified (distinct from `agylite verify` runs, which are VERIFICATION_*)
    "TASK_READY_FOR_VERIFICATION", "TASK_VERIFIED",
    # an upstream engine ran (Graphify, UI/UX Pro Max, BeyondSEO, Brag, Unlazy) — `agylite used` reports it
    "RUNTIME_USED",
)
SEVERITIES = ("info", "low", "medium", "high", "critical")
FIELDS = ("schema_version", "id", "ts", "event", "severity", "project_id", "session_id", "host", "capabilities",
          "bytes_loaded", "est_tokens", "duration_ms", "details")


class EventError(ValueError):
    pass


def envelope(event: str, *, project_id: str, session_id=None, host=None, capabilities=(), bytes_loaded=None,
             est_tokens=None, duration_ms=None, severity="info", details=None):
    if event not in EVENT_TYPES:
        raise EventError(f"unknown event type {event}")
    if severity not in SEVERITIES:
        raise EventError(f"unknown severity {severity}")
    return {"schema_version": SCHEMA_VERSION, "id": uuid.uuid4().hex,
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": event, "severity": severity, "project_id": project_id, "session_id": session_id, "host": host,
            "capabilities": list(capabilities), "bytes_loaded": bytes_loaded, "est_tokens": est_tokens,
            "duration_ms": duration_ms, "details": details or {}}


def validate(record) -> list:
    p = []
    missing = [f for f in FIELDS if f not in record]
    if missing:
        p.append(f"missing fields {missing}")
    if record.get("event") not in EVENT_TYPES:
        p.append(f"unknown event {record.get('event')!r}")
    if record.get("severity") not in SEVERITIES:
        p.append(f"unknown severity {record.get('severity')!r}")
    if not isinstance(record.get("details"), dict):
        p.append("details must be an object")
    return p
