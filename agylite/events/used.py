"""`agylite used`: what one session actually used — routed capabilities, upstream projects whose content was loaded,
engines that ran, and the core steps (route, plan, verify) — read from the project's event log."""
import re

# Bundle folder (files/<key>/…) → the upstream project's name as people know it.
UPSTREAMS = {
    "ecc": "ECC", "addy": "Addy Osmani agent-skills", "agency": "Agency Agents", "gstack": "gstack",
    "karpathy": "Karpathy Skills", "unlazy": "Unlazy", "ponytail": "Ponytail", "graphify": "Graphify",
    "opendesign": "Open Design", "taste": "Taste", "uiuxpromax": "UI/UX Pro Max", "brag": "Brag",
    "beacon": "Agent Beacon", "beyondseo": "BeyondSEO", "appllama": "Appllama",
}
# CLI command → the upstream engine it runs.
ENGINES = {"codebase": "graphify", "design": "uiuxpromax", "seo": "beyondseo", "media": "brag", "gates": "unlazy"}
FILE_RE = re.compile(r"^files/([^/]+)/")


def upstream_counts(paths) -> dict:
    """{upstream key: files} for bundle paths like `files/ecc/skills/…/SKILL.md`."""
    out = {}
    for p in paths:
        m = FILE_RE.match(p)
        if m:
            out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def session_events(events, session_id=None):
    """The events of one session: the given id, else the newest session in the log (by its SESSION_STARTED)."""
    if not session_id:
        starts = [e for e in events if e["event"] == "SESSION_STARTED" and e.get("session_id")]
        session_id = starts[-1]["session_id"] if starts else None
    if not session_id:
        return None, events
    return session_id, [e for e in events if e.get("session_id") == session_id]


def summarize(events) -> dict:
    caps, upstreams, engines, tasks = [], {}, {}, {}
    routes, verifies = 0, []
    for e in events:
        d = e.get("details") or {}
        if e["event"] == "DOMAIN_SELECTED":
            routes += 1
        elif e["event"] == "CAPABILITIES_SELECTED":
            caps += [c for c in e.get("capabilities") or [] if c not in caps]
        elif e["event"] == "CONTEXT_LOADED":
            for key, n in (d.get("upstreams") or {}).items():
                upstreams[key] = upstreams.get(key, 0) + n
        elif e["event"] == "RUNTIME_USED":
            key = d.get("engine")
            if key:
                engines.setdefault(key, [])
                if d.get("command") and d["command"] not in engines[key]:
                    engines[key].append(d["command"])
        elif e["event"] in ("VERIFICATION_PASSED", "VERIFICATION_FAILED"):
            verifies.append(d.get("result") or ("PASSED" if e["event"] == "VERIFICATION_PASSED" else "FAILED"))
        if d.get("item", "").startswith("T-") and d.get("to"):
            tasks[d["item"]] = d["to"]
        if d.get("change") == "task_added" and d.get("task"):
            tasks.setdefault(d["task"], "PLANNED")
    return {"capabilities": caps, "upstreams": upstreams, "engines": engines, "routes": routes, "tasks": tasks,
            "verifications": verifies}


def render(summary, session_id=None) -> str:
    s = summary
    ups = sorted(s["upstreams"].items(), key=lambda kv: (-kv[1], kv[0]))
    lines = [f"Agylite used{f' (session {session_id})' if session_id else ''}:"]
    lines.append("- Capabilities: " + (", ".join(s["capabilities"]) or "none routed"))
    lines.append("- Upstream content loaded: " + (", ".join(
        f"{UPSTREAMS.get(k, k)} ({n} file{'s' if n != 1 else ''})" for k, n in ups) or "none"))
    lines.append("- Engines run: " + (", ".join(
        f"{UPSTREAMS.get(k, k)} ({', '.join(cmds)})" if cmds else UPSTREAMS.get(k, k)
        for k, cmds in s["engines"].items()) or "none"))
    core = [f"route ×{s['routes']}"] if s["routes"] else []
    if s["tasks"]:
        core.append("plan " + ", ".join(f"{t} {st}" for t, st in s["tasks"].items()))
    if s["verifications"]:
        core.append(f"verify ×{len(s['verifications'])} (last {s['verifications'][-1]})")
    lines.append("- Agylite core: " + (", ".join(core) or "none"))
    return "\n".join(lines)
