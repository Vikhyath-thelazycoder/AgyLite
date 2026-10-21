"""Unlazy runtime (P13, engineering/completion): acceptance-gate ledgers run from the bundle with Node.

`agylite gates <mode> <ledger>` runs `scripts/gate-check.mjs` / `gate-lint.mjs` from the active bundle in the
project directory. The optional Claude Code Stop hook is registered only centrally (`~/.claude/settings.json`, via
Unlazy's own installer with `--global`), never in a project, and only on an explicit `--enable` (§2.5, SEC-01).
The hook command points at `bundles/current`, so it keeps working across bundle updates and rollbacks.
"""
import shutil
import subprocess
from pathlib import Path

MODES = {"status": ["--status"], "check": [], "approve": ["--approve"], "reverify": ["--reverify"]}


class UnlazyError(RuntimeError):
    pass


def scripts_dir(home: Path) -> Path | None:
    """Via the `current` pointer (not the resolved bundle id) so registered hooks survive updates."""
    d = Path(home) / "bundles" / "current" / "files" / "unlazy" / "scripts"
    return d if (d / "gate-check.mjs").is_file() else None


def health(home: Path) -> dict:
    node = shutil.which("node")
    d = scripts_dir(home)
    if d is None:
        return {"runtime": "unlazy", "status": "no-bundle", "reason": "no active bundle with files/unlazy"}
    if node is None:
        return {"runtime": "unlazy", "status": "broken", "reason": "node not found on PATH (Unlazy needs Node 16+)"}
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    return {"runtime": "unlazy", "status": "ready", "version": f"node {version}", "path": str(d)}


def _node(home):
    node = shutil.which("node")
    d = scripts_dir(home)
    if node is None or d is None:
        raise UnlazyError(health(home)["reason"])
    return node, d


def gates(home: Path, mode: str, files, cwd: Path, extra=()) -> subprocess.CompletedProcess:
    node, d = _node(home)
    if mode == "lint":
        cmd = [node, str(d / "gate-lint.mjs"), *extra, *files]
    elif mode in MODES:
        cmd = [node, str(d / "gate-check.mjs"), *MODES[mode], *extra, *files]
    else:
        raise UnlazyError(f"unknown gates mode {mode}; use {', '.join([*MODES, 'lint'])}")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def stop_hook_commands(path: Path | None = None) -> list:
    """Unlazy's Stop-hook commands in the global settings (its packaged `scripts/stop-hook.mjs`), nothing else."""
    import json
    path = path or settings_path()
    try:
        groups = (json.loads(path.read_text(encoding="utf-8")).get("hooks") or {}).get("Stop") or []
    except (OSError, ValueError, AttributeError):
        return []
    return [h.get("command", "") for g in groups if isinstance(g, dict) for h in g.get("hooks") or []
            if isinstance(h, dict) and "stop-hook.mjs" in str(h.get("command", ""))]


def stop_hook_state(path: Path | None = None) -> str:
    return "enabled" if stop_hook_commands(path) else "disabled"


def stop_hook(home: Path, enable: bool) -> subprocess.CompletedProcess:
    """Install or remove Unlazy's Stop hook in the user's global Claude Code settings (never project-local)."""
    node, d = _node(home)
    cmd = [node, "--preserve-symlinks", "--preserve-symlinks-main", str(d / "install-hooks.mjs"), "--global"]
    if not enable:
        cmd.append("--uninstall")
    return subprocess.run(cmd, cwd=Path.home(), capture_output=True, text=True)
