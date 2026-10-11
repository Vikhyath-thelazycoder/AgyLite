"""Agent Office state machine (P23, D-043): project events → each seat's state, speech bubble and last event.

Pure functions over the layout (config/dashboard.yaml), the registry's source repos and the event list, so the whole
mapping is unit-tested from fixture events. States: working · waiting · blocked · idle · off · disabled.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from ..paths import repo_root

STATES = ("working", "waiting", "blocked", "idle", "off", "disabled")


def load_layout(root: Path | None = None) -> dict:
    with open((root or repo_root()) / "config" / "dashboard.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_layout(layout, capability_ids) -> list:
    p = []
    seen = {}
    rooms = {r["id"] for r in layout.get("rooms", [])}
    for s in layout.get("seats", []):
        if s["room"] not in rooms:
            p.append(f"seat {s['id']}: unknown room {s['room']}")
        if s.get("fixed") and s["fixed"] not in STATES:
            p.append(f"seat {s['id']}: unknown fixed state {s['fixed']}")
        for c in s.get("caps", []):
            if c in seen:
                p.append(f"{c} seated twice ({seen[c]}, {s['id']})")
            seen[c] = s["id"]
            if c not in capability_ids:
                p.append(f"seat {s['id']}: unknown capability {c}")
    p += [f"{c} has no seat" for c in sorted(set(capability_ids) - set(seen))]
    return p


def _ts(rec):
    return datetime.fromisoformat(rec["ts"])


def _short(repo: str) -> str:
    return repo.rsplit("/", 1)[-1]


def derive(layout, events, sources=None, now=None):
    """Seats with state/say/last from events in time order. `sources`: capability id → [source repos]."""
    sources = sources or {}
    now = now or datetime.now(timezone.utc)
    idle_after = timedelta(minutes=layout.get("idle_after_minutes", 10))
    seats = {s["id"]: {**s, "caps": list(s.get("caps", [])), "state": s.get("fixed", "idle"), "say": "",
                       "last": None, "at": None,
                       "sources": sorted({_short(r) for c in s.get("caps", []) for r in sources.get(c, [])})}
             for s in layout["seats"]}
    by_cap = {c: sid for sid, s in seats.items() for c in s["caps"]}
    agency = [sid for sid, s in seats.items() if s.get("sources_any")]
    change_type = None

    def set_(sid, state, say, rec):
        s = seats.get(sid)
        if s is None:
            return
        if s.get("fixed") == "disabled":
            state = "disabled"   # policy beats events: the desk stays dark, the bubble still reports the request
        s.update(state=state, say=say, at=rec["ts"], last=f"{rec['ts'][11:19]} · {say or rec['event']}")

    def seats_for(caps):
        out = []
        for c in caps:
            sid = by_cap.get(c)
            if sid and sid not in out:
                out.append(sid)
        return out

    for rec in events:
        ev, caps, d = rec["event"], rec.get("capabilities") or [], rec.get("details") or {}
        if ev == "DOMAIN_SELECTED":
            change_type = d.get("change_type")
            set_("router", "working", f"routing {change_type or ''} → {', '.join(d.get('domains', []))}".strip(), rec)
        elif ev == "CAPABILITIES_SELECTED":
            chosen = seats_for(caps)
            for sid in chosen:
                set_(sid, "working", f"selected for {change_type or 'this task'}", rec)
            for sid in seats_for(d.get("dependencies", [])):
                if sid not in chosen:
                    set_(sid, "waiting", "needed by " + ", ".join(seats[x]["name"] for x in chosen[:2]), rec)
            for sid in agency:
                pat = seats[sid]["sources_any"]
                if any(any(p in r.lower() for p in pat) for c in caps for r in sources.get(c, [])):
                    set_(sid, "working", "specialist perspective", rec)
            set_("router", "idle", f"routed → {len(chosen)} agents", rec)
        elif ev == "CONTEXT_LOADED":
            tok = rec.get("est_tokens")
            for sid in seats_for(caps):
                set_(sid, "working", f"reading context (~{tok:,} tokens)" if tok else "reading context", rec)
        elif ev == "VERIFICATION_STARTED":
            set_("qa", "working", f"verifying: {d.get('checks', '?')} checks", rec)
        elif ev == "VERIFICATION_PASSED":
            set_("qa", "idle", "verify: PASSED", rec)
        elif ev == "VERIFICATION_FAILED":
            failed = ", ".join(d.get("failed", [])[:3]) or d.get("result", "FAILED")
            set_("qa", "blocked", f"verify failed: {failed}", rec)
        elif ev == "TASK_STARTED":
            set_("planner", "working", f"{d.get('item') or d.get('task', 'task')} in progress", rec)
        elif ev == "TASK_BLOCKED":
            set_("planner", "blocked", f"{d.get('item') or d.get('task', 'task')} blocked: {d.get('reason', 'see plan')}", rec)
        elif ev == "TASK_COMPLETED":
            set_("planner", "idle", f"{d.get('item') or d.get('task', 'task')} done", rec)
        elif ev == "TASK_READY_FOR_VERIFICATION":
            set_("planner", "waiting", f"{d.get('item', 'task')} ready for verification", rec)
        elif ev == "TASK_VERIFIED":
            set_("planner", "idle", f"{d.get('item', 'task')} VERIFIED", rec)
        elif ev == "PHASE_CHANGED":
            set_("planner", "idle" if d.get("to") in ("VERIFIED", "COMPLETED") else "working",
                 f"phase {d.get('item', '?')} → {d.get('to', '?')}", rec)
        elif ev == "RISK_DETECTED":
            set_("beacon", "blocked", f"risk: {d.get('rule') or d.get('title') or 'detected'}", rec)
        elif ev == "ISOLATION_VIOLATION_BLOCKED":
            set_("beacon", "blocked", "blocked a cross-project read", rec)
        elif ev == "BROWSER_EXCEPTION_REQUESTED":
            set_("browser", "disabled", "exception recorded (user operates the browser)", rec)

    for s in seats.values():
        if s.get("fixed") and s["state"] not in ("disabled",):
            if s["fixed"] == "off" and not (s["at"] and now - datetime.fromisoformat(s["at"]) < idle_after):
                s["state"], s["say"] = "off", ""
        if s["state"] in ("working", "waiting", "blocked") and s["at"] and \
                now - datetime.fromisoformat(s["at"]) > idle_after:
            s["state"], s["say"] = "idle", ""
    return list(seats.values())


def activity(events, limit=40):
    """Readable activity lines, newest first."""
    out = []
    for rec in events[-limit:][::-1]:
        d = rec.get("details") or {}
        caps = rec.get("capabilities") or []
        text = {
            "DOMAIN_SELECTED": lambda: f"Routed {d.get('change_type', '')} → {', '.join(d.get('domains', []))}"
                                       f" ({d.get('method', '')}, {d.get('confidence', '')})",
            "CAPABILITIES_SELECTED": lambda: "Selected " + ", ".join(caps),
            "CONTEXT_LOADED": lambda: f"Context loaded for {', '.join(caps)} (~{rec.get('est_tokens') or 0:,} tokens)",
            "VERIFICATION_STARTED": lambda: f"Verification started: {d.get('checks', '?')} checks",
            "VERIFICATION_PASSED": lambda: f"Verification PASSED · {d.get('evidence', '')}",
            "VERIFICATION_FAILED": lambda: f"Verification {d.get('result', 'FAILED')}: {', '.join(d.get('failed', []))}",
            "RISK_DETECTED": lambda: f"Risk: {d.get('rule') or d.get('title') or ''} ({rec['severity']})",
            "TASK_READY_FOR_VERIFICATION": lambda: f"{d.get('item', 'Task')} ready for verification",
            "TASK_VERIFIED": lambda: f"{d.get('item', 'Task')} VERIFIED · {d.get('evidence') or ''}".rstrip(" ·"),
            "PHASE_CHANGED": lambda: f"Phase {d.get('item', '?')}: {d.get('from', '?')} → {d.get('to', '?')}"
                                     + (f" ({d['reason']})" if d.get("reason") else ""),
        }.get(rec["event"], lambda: rec["event"].replace("_", " ").capitalize())()
        out.append({"ts": rec["ts"], "event": rec["event"], "severity": rec["severity"], "text": text})
    return out
