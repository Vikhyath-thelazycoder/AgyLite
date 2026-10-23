"""gstack, full (D-049, IMPLEMENTATION_PLAN §2.2; owner decisions 2026-10-22): gstack's /qa and browse run from gstack's
own install, exactly as gstack documents it — `~/.claude/skills/gstack` + `./setup` — pinned to the audited commit.

Owner settings applied before setup: telemetry off and gstack's update check off (Agylite owns updates, MP6); the
optional global hooks are skipped (`--no-plan-tune-hooks --no-timeline-stop-hook`). Bun (gstack's requirement) comes
from Homebrew. What setup changed in `~/.claude/settings.json` is reported (added/removed hook commands).
browse runs a daemon only while a QA task uses it; `browse stop` ends it (the testing/browser-qa guide says so).
"""
import json
import shutil
import subprocess
from pathlib import Path

REPO = "https://github.com/garrytan/gstack.git"
MIN_BUN = (1, 3, 3)   # gstack's setup refuses older Bun (compiled tools could read a project's .env)
SETUP_FLAGS = ("--host", "claude", "--no-plan-tune-hooks", "--no-timeline-stop-hook", "--quiet")


class GstackError(RuntimeError):
    pass


def install_dir(user_home: Path | None = None) -> Path:
    return (user_home or Path.home()) / ".claude" / "skills" / "gstack"


def pin() -> str:
    from ..bundle.rules import evidence_dir, load_yaml
    return load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"]["gstack"]["head"]


def bun_version():
    bun = shutil.which("bun")
    if not bun:
        return None
    out = subprocess.run([bun, "--version"], capture_output=True, text=True).stdout.strip()
    try:
        return tuple(int(x) for x in out.split(".")[:3])
    except ValueError:
        return None


def _hooks(settings: Path) -> list:
    if not settings.is_file():
        return []
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except ValueError:
        return []
    return sorted(f"{event}: {h.get('command')}" for event, groups in (data.get("hooks") or {}).items()
                  for g in groups or [] for h in g.get("hooks") or [] if isinstance(h, dict))


def health(user_home: Path | None = None) -> dict:
    d = install_dir(user_home)
    if not (d / "setup").is_file():
        return {"runtime": "gstack", "status": "not-installed", "reason": "run `agylite runtime install gstack`"}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    browse = d / "browse" / "dist" / "browse"
    return {"runtime": "gstack", "status": "ready" if browse.exists() else "broken", "commit": head[:7],
            "pinned": head == pin(), "bun": ".".join(map(str, bun_version() or ())) or "missing", "path": str(d),
            **({} if browse.exists() else {"reason": "browse binary missing: re-run `agylite runtime install gstack`"})}


def install(home=None, user_home: Path | None = None, log=print) -> dict:
    user_home = user_home or Path.home()
    v = bun_version()
    if v is None or v < MIN_BUN:
        if not shutil.which("brew"):
            raise GstackError("gstack needs Bun ≥ 1.3.3 and Homebrew is not installed: install Bun from bun.sh first")
        log("installing Bun with Homebrew (gstack's requirement) …")
        p = subprocess.run(["brew", "install", "oven-sh/bun/bun"], capture_output=True, text=True, timeout=1800)
        if p.returncode or (bun_version() or (0,)) < MIN_BUN:
            raise GstackError(f"brew install oven-sh/bun/bun failed: {(p.stderr or p.stdout).strip()[-400:]}")
    d, sha = install_dir(user_home), pin()
    if not (d / ".git").is_dir():
        d.parent.mkdir(parents=True, exist_ok=True)
        log(f"cloning gstack into {d} …")
        subprocess.run(["git", "clone", "--quiet", REPO, str(d)], check=True, capture_output=True, timeout=1800)
    subprocess.run(["git", "fetch", "--quiet", "origin", sha], cwd=d, capture_output=True, timeout=600)
    subprocess.run(["git", "checkout", "--quiet", "--detach", sha], cwd=d, check=True, capture_output=True)
    config = d / "bin" / "gstack-config"
    for key, value in (("telemetry", "off"), ("update_check", "false")):   # owner decision 2026-10-22; MP6
        subprocess.run([str(config), "set", key, value], cwd=d, check=True, capture_output=True, text=True)
    settings = user_home / ".claude" / "settings.json"
    before = _hooks(settings)
    log(f"running gstack ./setup {' '.join(SETUP_FLAGS)} (pinned {sha[:7]}) …")
    p = subprocess.run(["./setup", *SETUP_FLAGS], cwd=d, capture_output=True, text=True, timeout=3600)
    if p.returncode:
        raise GstackError(f"gstack ./setup failed: {(p.stderr or p.stdout).strip()[-800:]}")
    after = _hooks(settings)
    return {**health(user_home), "telemetry": "off", "update_check": "false",
            "settings_json": {"added": [h for h in after if h not in before], "removed": [h for h in before if h not in after]}}
