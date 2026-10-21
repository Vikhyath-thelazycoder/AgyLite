"""Taste v2.1 runtime (MP4 §1.3, design/visual-quality): `agylite design taste <script> …` runs the bundled scripts.

Scripts come from the active bundle (`files/taste/skills/taste-skill/scripts/`) and run in the project, so their
working files land in the project's `.taste-skill/`. Every call sets:
- `TASTE_SKILL_TMP=<home>/tmp/taste`: inspect's throwaway Chrome profiles;
- `TASTE_SKILL_HISTORY=<home>/taste/history.json`: draw.mjs remembers recent draws so consecutive projects do not look
  alike. Upstream keeps it in ~/.taste-skill; it is cross-project by design, so it moves to an Agylite-owned file
  (never into another project) rather than per project, which would defeat it.
Credentials never reach the scripts (assets.mjs is the only one that uses the network, and needs no key).
Node >= 22 and a Chrome/Edge/Chromium are required (inspect, scenes); `status` says which is missing.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

SCRIPTS = ("draw", "inspect", "lint", "scenes", "assets")
SKILL_SCRIPTS = Path("files/taste/skills/taste-skill/scripts")
MIN_NODE = 22
BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge")
MAC_BROWSERS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
SECRET = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.I)


class TasteError(RuntimeError):
    pass


def scripts_dir(bundle_dir: Path | None) -> Path | None:
    d = Path(bundle_dir) / SKILL_SCRIPTS if bundle_dir else None
    return d if d and (d / "draw.mjs").is_file() else None


def node_version():
    node = shutil.which("node")
    if not node:
        return None
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v")
    try:
        return tuple(int(x) for x in out.split(".")[:3])
    except ValueError:
        return None


def find_browser() -> str | None:
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for name in BROWSERS:
        if shutil.which(name):
            return shutil.which(name)
    return next((p for p in MAC_BROWSERS if Path(p).exists()), None)


def health(bundle_dir: Path | None, home: Path) -> dict:
    if scripts_dir(bundle_dir) is None:
        return {"runtime": "taste", "status": "no-bundle", "reason": "no active bundle with Taste v2.1 scripts"}
    v = node_version()
    node = (f"node {'.'.join(map(str, v))}" if v and v[0] >= MIN_NODE else
            f"missing: node>={MIN_NODE}" + (f" (found {'.'.join(map(str, v))})" if v else ""))
    browser = find_browser()
    ok = node.startswith("node ") and browser
    return {"runtime": "taste", "status": "ready" if ok else "broken", "node": node,
            "browser": f"found {browser}" if browser else "missing",
            **({} if ok else {"reason": "inspect needs node>=22 and a Chrome/Edge/Chromium"})}


def env_for(home: Path) -> dict:
    tmp, hist = Path(home) / "tmp" / "taste", Path(home) / "taste" / "history.json"
    tmp.mkdir(parents=True, exist_ok=True)
    hist.parent.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k)}
    env.update(TASTE_SKILL_TMP=str(tmp), TASTE_SKILL_HISTORY=str(hist))
    browser = find_browser()
    if browser:
        env["CHROME_PATH"] = browser
    return env


def command(bundle_dir: Path | None, home: Path, script: str, args) -> tuple:
    if script not in SCRIPTS:
        raise TasteError(f"unknown taste command {script!r}; use one of {', '.join(SCRIPTS)}")
    d = scripts_dir(bundle_dir)
    if d is None:
        raise TasteError(health(bundle_dir, home)["reason"])
    return [shutil.which("node") or "node", str(d / f"{script}.mjs"), *args], env_for(home)


def run(bundle_dir, home, script, args, cwd: Path, capture=False) -> subprocess.CompletedProcess:
    argv, env = command(bundle_dir, home, script, args)
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=capture, text=True)


def self_test(bundle_dir: Path, home: Path, fixtures: Path) -> dict:
    """Bundle self-test (§1.4): lint exits 0 on the clean fixture and 1 on the one with known tells."""
    codes = {}
    for name in ("clean.html", "tell.html"):
        codes[name] = run(bundle_dir, home, "lint", [name], cwd=fixtures, capture=True).returncode
    return {"runtime": "taste", "exit_codes": codes, "ok": codes == {"clean.html": 0, "tell.html": 1}}
