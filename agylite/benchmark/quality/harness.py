"""MP2 Tier 1 harness: real headless Claude Code sessions, three arms, the pilot's isolation (AUDIT_REPORT §9).

Every session: `claude -p --setting-sources project,local --strict-mcp-config` (no user plugins, no MCP) in a fresh
workspace outside any git repository. Arms:
- baseline  — nothing extra
- upstream  — the upstream the way its authors benchmark it (a plugin via --plugin-dir, Addy's --append-system-prompt,
  or project skills copied into the workspace's .claude/skills)
- agylite   — this checkout via --plugin-dir, with its own AGYLITE_HOME (the installed bundle and runtimes linked, no
  `core`), so `bin/agylite` runs this checkout's code and its events stay out of ~/.agylite
Isolation is verified from the stream-json `init` event, never assumed. Paid sessions need `--yes-spend`.
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from ...paths import agylite_home, repo_root

BUILTIN_SOURCE = "@builtin"
DEFAULT_MODEL = "claude-opus-5-5"


class SpendRefused(RuntimeError):
    pass


class IsolationError(RuntimeError):
    pass


@dataclass
class ArmSetup:
    """How one arm differs: extra CLI args, env, files copied into the workspace, expected non-builtin plugins."""
    name: str
    args: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    plugins: tuple = ()           # expected plugin names besides Claude Code's builtins
    project_skills: tuple = ()    # skill folders copied into <workspace>/.claude/skills/


def fresh_workspace(prefix: str) -> Path:
    """A new directory outside any git repository (Claude Code shows a repo's branch and commits to the model)."""
    ws = Path(tempfile.mkdtemp(prefix=f"agy-q-{prefix}-"))
    probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ws, capture_output=True, text=True)
    if probe.returncode == 0:
        raise IsolationError(f"workspace {ws} is inside git repo {probe.stdout.strip()}")
    return ws


def agylite_home_for(run_dir: Path) -> Path:
    """A per-run engine home: the installed bundles and runtimes linked read-only, no `core` (so the plugin's launcher
    runs this checkout's source), its own projects/cache/events."""
    home = run_dir / "agylite-home"
    home.mkdir(parents=True, exist_ok=True)
    real = agylite_home()
    for name in ("bundles", "runtimes", "staging"):
        link = home / name
        if (real / name).exists() and not link.exists():
            link.symlink_to(real / name)
    return home


def agylite_arm(run_dir: Path, python: str | None = None) -> ArmSetup:
    home = agylite_home_for(run_dir)
    env = {"AGYLITE_HOME": str(home), "AGYLITE_NO_AUTO_UPDATE": "1"}
    if python:
        env["AGYLITE_PYTHON"] = python
    return ArmSetup("agylite", args=["--plugin-dir", str(repo_root())], env=env, plugins=("agylite",))


def base_cmd(model: str | None) -> list:
    return ["claude", "-p", "--verbose", "--output-format", "stream-json", "--setting-sources", "project,local",
            "--strict-mcp-config", "--model", model or DEFAULT_MODEL]


def check_isolation(trace_lines, arm: ArmSetup) -> dict:
    """The session's `init` event lists exactly the arm's plugins (plus builtins), only their namespaced skills, and
    no MCP servers. Returns the init facts; raises IsolationError on a mismatch."""
    init = None
    for line in trace_lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            init = e
            break
    if init is None:
        raise IsolationError("no init event in the trace")
    plugins = sorted(p["name"] for p in init.get("plugins") or [] if not str(p.get("source", "")).endswith(BUILTIN_SOURCE))
    if plugins != sorted(arm.plugins):
        raise IsolationError(f"arm {arm.name}: plugins {plugins} != expected {sorted(arm.plugins)}")
    spaces = sorted({s.split(":", 1)[0] for s in init.get("skills") or [] if ":" in s})
    if set(spaces) - set(arm.plugins):
        raise IsolationError(f"arm {arm.name}: skills from unexpected plugins {sorted(set(spaces) - set(arm.plugins))}")
    if init.get("mcp_servers"):
        raise IsolationError(f"arm {arm.name}: MCP servers present {[m.get('name') for m in init['mcp_servers']]}")
    return {"model": init.get("model"), "claude_code_version": init.get("claude_code_version"), "plugins": plugins,
            "skills": len(init.get("skills") or [])}


def summarize_trace(trace_lines) -> dict:
    """Cost, time, turns, tool calls and Agylite usage from a stream-json trace."""
    out = {"cost": None, "duration_ms": None, "turns": None, "agylite_calls": [], "tool_calls": 0, "skill_loads": []}
    for line in trace_lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for c in (e.get("message") or {}).get("content") or []:
                if c.get("type") != "tool_use":
                    continue
                out["tool_calls"] += 1
                cmd = (c.get("input") or {}).get("command", "")
                if c.get("name") == "Bash" and "agylite" in cmd:
                    out["agylite_calls"].append(cmd[:200])
                if c.get("name") == "Skill":
                    out["skill_loads"].append((c.get("input") or {}).get("skill"))
        elif e.get("type") == "result":
            out.update(cost=e.get("total_cost_usd"), duration_ms=e.get("duration_ms"), turns=e.get("num_turns"),
                       result=e.get("result", "")[:4000])
    return out


def run_session(prompt: str, workspace: Path, arm: ArmSetup, *, model=None, allowed_tools=None, permission_mode="acceptEdits",
                append_system=None, timeout=900, extra_args=(), out_dir: Path | None = None, label="session") -> dict:
    """One paid session. The trace is stored gzipped under `out_dir` (outside the repo)."""
    import gzip
    for skill in arm.project_skills:
        dest = workspace / ".claude" / "skills" / Path(skill).name
        shutil.copytree(skill, dest, dirs_exist_ok=True)
    cmd = base_cmd(model) + ["--permission-mode", permission_mode] + list(arm.args) + list(extra_args)
    if allowed_tools:
        cmd += ["--allowedTools", allowed_tools]
    if append_system:
        cmd += ["--append-system-prompt", append_system]
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", **arm.env}
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, cwd=workspace, env=env, timeout=timeout)
        stdout, killed = proc.stdout, False
    except subprocess.TimeoutExpired as exc:
        stdout, killed = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""), True
    lines = stdout.splitlines()
    rec = {"label": label, "arm": arm.name, "wall_s": round(time.time() - t0, 1), "killed": killed,
           "workspace": str(workspace)}
    try:
        rec["init"] = check_isolation(lines, arm)
    except IsolationError as exc:
        rec["isolation_error"] = str(exc)
    rec.update(summarize_trace(lines))
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(out_dir / f"{label}.trace.jsonl.gz", "wt", encoding="utf-8") as f:
            f.write(stdout)
    rec["_trace"] = stdout
    return rec


def ask(prompt: str, *, model=None, timeout=600) -> str:
    """A plain one-shot model call (graders, judges), in an empty directory, no plugins, no MCP."""
    with tempfile.TemporaryDirectory() as d:
        return subprocess.run(["claude", "-p", "--setting-sources", "project,local", "--strict-mcp-config",
                               "--model", model or DEFAULT_MODEL], input=prompt, text=True, capture_output=True,
                              cwd=d, timeout=timeout).stdout


def require_spend(yes_spend: bool, sessions: int, max_sessions: int | None):
    if not yes_spend:
        raise SpendRefused(f"{sessions} paid sessions planned; pass --yes-spend to run them (or --dry-run to see them)")
    if max_sessions is not None and sessions > max_sessions:
        raise SpendRefused(f"{sessions} sessions planned > --max-sessions {max_sessions}")


def agylite_usage(home: Path, workspace: Path) -> dict:
    """What Agylite did in one session, from the arm's own event log: prompt routes, context loads, unmatched."""
    counts = {"prompt_routed": 0, "context_loaded": 0, "route_unmatched": 0, "capabilities_selected": 0}
    target = str(Path(workspace).resolve())
    for log in Path(home).glob("projects/*/events/*.jsonl"):
        lines = log.read_text(encoding="utf-8").splitlines()
        events = [json.loads(x) for x in lines if x.strip()]
        roots = {str(Path(e["details"].get("root", "")).resolve()) for e in events
                 if e["event"] == "SESSION_STARTED" and e.get("details", {}).get("root")}
        if target not in roots:
            continue
        for e in events:
            key = e["event"].lower()
            if key in counts:
                counts[key] += 1
    return counts
