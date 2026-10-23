"""Browser runtime (D-049, IMPLEMENTATION_PLAN §2.2): pinned Playwright (npm, exact version) and its Chromium in
`runtimes/browser-<version>/` (`PLAYWRIGHT_BROWSERS_PATH` inside it), started per check with a throwaway context per
viewport — never the user's profile.

`check()` is `agylite verify --browser`: it uses the given URL, or serves/starts the project (a static `index.html`,
else the `preview`/`dev`/`start` script of package.json), waits for it, runs `browser_check.mjs`, writes evidence to
`<project>/.agylite/evidence/browser/<run-id>/` (screenshots, console.json, network.json, flows.json, report.json with
sha256 of each artefact) and stops what it started. It FAILS on console errors, failed requests to the app itself,
horizontal overflow at 390 px, images without alt text and failing flows.
Flows (`.agylite/flows.yaml`) are plain data: goto, click {role, name}, fill {label | role+name, value}, expect_text,
expect_url. Any other step (e.g. eval/script) is rejected before the browser starts.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

PLAYWRIGHT = "1.64.0"   # released 2026-10-07; exact pin
WIDTHS = (1440, 768, 390)
STEP_KEYS = {"goto", "click", "fill", "expect_text", "expect_url"}
SCRIPTS = ("preview", "dev", "start")
URL_IN_OUTPUT = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[::1\]|0\.0\.0\.0)(?::\d+)?[^\s\"'<>]*")
CHECK_JS = Path(__file__).with_name("browser_check.mjs")


class BrowserError(RuntimeError):
    pass


def runtime_dir(home) -> Path:
    return Path(home) / "runtimes" / f"browser-{PLAYWRIGHT}"


def _env(home) -> dict:
    env = {k: v for k, v in os.environ.items() if not re.search(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", k, re.I)}
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(runtime_dir(home) / "browsers")
    env["PLAYWRIGHT_SKIP_BROWSER_GC"] = "1"
    return env


def install(home, log=print) -> dict:
    """npm install --ignore-scripts playwright@<pin>, then its Chromium (headless shell) into the runtime."""
    final = runtime_dir(home)
    info_path = final / "runtime.json"
    if info_path.is_file():
        return json.loads(info_path.read_text(encoding="utf-8"))
    if not shutil.which("npm"):
        raise BrowserError("npm is not installed (Node.js ≥ 18 is required for the browser runtime)")
    final.mkdir(parents=True, exist_ok=True)
    (final / "package.json").write_text(json.dumps({"name": "agylite-browser", "private": True}), encoding="utf-8")
    log(f"installing the browser runtime: playwright@{PLAYWRIGHT} + Chromium …")
    for argv in (["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--silent", f"playwright@{PLAYWRIGHT}"],
                 [str(final / "node_modules" / ".bin" / "playwright"), "install", "chromium"]):
        p = subprocess.run(argv, cwd=final, env=_env(home), capture_output=True, text=True, timeout=1800)
        if p.returncode:
            raise BrowserError(f"{' '.join(argv[:3])} failed: {(p.stderr or p.stdout).strip()[-500:]}")
    info = {"runtime": "browser", "playwright": PLAYWRIGHT, "path": str(final),
            "installed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    info_path.write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
    return info


def health(home) -> dict:
    final = runtime_dir(home)
    if not (final / "runtime.json").is_file():
        return {"runtime": "browser", "status": "not-installed", "reason": "run `agylite runtime install browser`"}
    return {"runtime": "browser", "status": "ready", "playwright": PLAYWRIGHT, "path": str(final)}


# ── flows ──────────────────────────────────────────────────────────────────────────────────────────────────────
def load_flows(path) -> list:
    """Validated flows: a list of {name, steps}; every step has exactly one known key; anything else is rejected."""
    if not path or not Path(path).is_file():
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    flows = data.get("flows", data) if isinstance(data, dict) else data
    if not isinstance(flows, list):
        raise BrowserError("flows.yaml: expected a list of flows ({name, steps})")
    out = []
    for f in flows:
        if not isinstance(f, dict) or not f.get("name") or not isinstance(f.get("steps"), list):
            raise BrowserError("flows.yaml: every flow needs a name and a list of steps")
        for i, step in enumerate(f["steps"], 1):
            keys = set(step) if isinstance(step, dict) else {"?"}
            if len(keys) != 1 or not keys <= STEP_KEYS:
                raise BrowserError(f"flows.yaml: {f['name']} step {i}: only one of {sorted(STEP_KEYS)} is allowed "
                                   f"(got {sorted(keys)}); flows are plain data, never scripts")
        out.append({"name": str(f["name"]), "steps": f["steps"]})
    return out


# ── the app under test ─────────────────────────────────────────────────────────────────────────────────────────
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url, timeout=60) -> bool:
    import urllib.request
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:   # noqa: BLE001 — not up yet
            time.sleep(0.5)
    return False


def start_app(root: Path):
    """(url, process) for the project: a static index.html is served here; else the first package.json script of
    preview/dev/start is started and its printed localhost URL used. Raises when nothing fits (ask for --url)."""
    root = Path(root)
    pkg = root / "package.json"
    scripts = (json.loads(pkg.read_text(encoding="utf-8")).get("scripts") or {}) if pkg.is_file() else {}
    script = next((s for s in SCRIPTS if s in scripts), None)
    if script is None:
        site = next((d for d in (root, root / "dist", root / "build", root / "public", root / "out")
                     if (d / "index.html").is_file()), None)
        if site is None:
            raise BrowserError("no URL given and nothing to start (no index.html, no preview/dev/start script): "
                               "pass --url")
        port = _free_port()
        proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=site,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        url = f"http://127.0.0.1:{port}/"
        if not _wait(url, 20):
            proc.terminate()
            raise BrowserError("the static server did not start")
        return url, proc
    log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    proc = subprocess.Popen(["npm", "run", script], cwd=root, stdout=log, stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    end = time.time() + 90
    while time.time() < end:
        time.sleep(0.5)
        m = URL_IN_OUTPUT.search(Path(log.name).read_text(encoding="utf-8", errors="ignore"))
        if m and _wait(m.group(0).replace("0.0.0.0", "127.0.0.1"), 10):
            return m.group(0).replace("0.0.0.0", "127.0.0.1"), proc
        if proc.poll() is not None:
            break
    stop_app(proc)
    raise BrowserError(f"`npm run {script}` did not print a reachable localhost URL in 90 s: pass --url")


def stop_app(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, 15)
    except (OSError, AttributeError):
        proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── the check ──────────────────────────────────────────────────────────────────────────────────────────────────
def defects(r: dict) -> list:
    out = [f"console error: {e['text']}" for e in r["console_errors"]]
    out += [f"failed request: {f['url']} ({f.get('status') or f.get('error')})" for f in r["failed_requests"]]
    if r.get("overflow"):
        o = r["overflow"]
        out.append(f"horizontal overflow at {o['width']} px (scrollWidth {o['scrollWidth']} > {o['clientWidth']})")
    out += [f"image without alt text: {src}" for src in r["images_without_alt"]]
    out += [f"flow failed: {f['error']}" for f in r["flows"] if not f["ok"]]
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(project_root: Path, home, *, url=None, flows=None, widths=WIDTHS, out=None) -> dict:
    """Run the browser check; returns the report (result PASSED or FAILED) and writes the evidence folder."""
    rt = runtime_dir(home)
    if not (rt / "runtime.json").is_file():
        raise BrowserError("the browser runtime is not installed: run `agylite runtime install browser`")
    if not shutil.which("node"):
        raise BrowserError("node is not installed")
    root = Path(project_root)
    flows_path = Path(flows) if flows else root / ".agylite" / "flows.yaml"
    flow_list = load_flows(flows_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(out) if out else root / ".agylite" / "evidence" / "browser" / run_id
    out.mkdir(parents=True, exist_ok=True)
    proc = None
    try:
        if not url:
            url, proc = start_app(root)
        cfg = {"url": url, "widths": list(widths), "flows": flow_list, "out": str(out), "runtime": str(rt)}
        cfg_path = out / ".config.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        p = subprocess.run(["node", str(CHECK_JS), str(cfg_path)], cwd=out, env=_env(home), capture_output=True,
                           text=True, timeout=600)
        cfg_path.unlink(missing_ok=True)
        if p.returncode:
            raise BrowserError(f"browser check crashed: {(p.stderr or p.stdout).strip()[-600:]}")
        r = json.loads(p.stdout)
    finally:
        stop_app(proc)
    for name, key in (("console.json", "console_errors"), ("network.json", "failed_requests"), ("flows.json", "flows")):
        (out / name).write_text(json.dumps(r[key], indent=1), encoding="utf-8")
    found = defects(r)
    arts = [out / f"screenshot-{w}.png" for w in widths] + [out / n for n in ("console.json", "network.json", "flows.json")]
    report = {"schema_version": 1, "url": r["url"], "result": "FAILED" if found else "PASSED", "defects": found,
              "widths": list(widths), "overflow": r["overflow"], "flows": r["flows"], "at": run_id,
              "artifacts": [{"path": a.name, "sha256": _sha(a)} for a in arts if a.is_file()]}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    report["dir"] = str(out)
    return report
