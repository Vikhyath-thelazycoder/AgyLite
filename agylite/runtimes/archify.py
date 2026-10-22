"""Archify runtime (MP5 §3.3, engineering/diagrams): `agylite diagram <archify-command> …` runs the bundled CLI
(`files/archify/archify/bin/archify.mjs`, Node >= 18, no npm dependencies) from the project root, exit code preserved.

Every call:
- sets `ARCHIFY_UPDATE_CHECK_DISABLED=1`: Agylite owns updates (MP6), Archify never checks or nags;
- passes the Chrome it found as `ARCHIFY_CHROME`, and strips credentials from the environment.
The browser-check (headless Chrome, owner approval 2026-10-22, config/verification.yaml `diagram_verification`) is
required whenever Chrome is present: `finalize` of an explainer gets `--browser-check` added (native diagrams always
run it). Without Chrome, `finalize` runs validate → deliver → check itself and reports "browser-check skipped", which
`agylite verify` records as NOT_RUN (BLOCKED), never as a pass.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .taste import MAC_BROWSERS, BROWSERS

CLI = Path("files/archify/archify/bin/archify.mjs")
MIN_NODE = 18
TYPES = ("architecture", "workflow", "sequence", "dataflow", "lifecycle", "erd", "class", "tree", "timeline",
         "waterfall", "explainer")
SECRET = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.I)
SKIPPED = "browser-check skipped: no Chrome/Chromium found (set ARCHIFY_CHROME to its executable)"


class ArchifyError(RuntimeError):
    pass


def cli_path(bundle_dir: Path | None) -> Path | None:
    p = Path(bundle_dir) / CLI if bundle_dir else None
    return p if p and p.is_file() else None


def node_version():
    node = shutil.which("node")
    if not node:
        return None
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v")
    try:
        return tuple(int(x) for x in out.split(".")[:3])
    except ValueError:
        return None


def find_chrome(env=None) -> str | None:
    """Archify's own order: ARCHIFY_CHROME when set, then the macOS app paths, then PATH commands."""
    env = os.environ if env is None else env
    if "ARCHIFY_CHROME" in env:
        given = env["ARCHIFY_CHROME"]
        return given if given and Path(given).exists() else None
    found = next((p for p in MAC_BROWSERS if Path(p).exists()), None)
    return found or next((shutil.which(n) for n in BROWSERS if shutil.which(n)), None)


def health(bundle_dir: Path | None) -> dict:
    if cli_path(bundle_dir) is None:
        return {"runtime": "archify", "status": "no-bundle", "reason": "no active bundle with files/archify"}
    v = node_version()
    node = (f"node {'.'.join(map(str, v))}" if v and v[0] >= MIN_NODE else
            f"missing: node>={MIN_NODE}" + (f" (found {'.'.join(map(str, v))})" if v else ""))
    chrome = find_chrome()
    ok = node.startswith("node ")
    return {"runtime": "archify", "status": "ready" if ok else "broken", "node": node,
            "browser_check": f"on ({chrome})" if chrome else "skipped (no Chrome)",
            **({} if ok else {"reason": f"Archify needs node>={MIN_NODE}"})}


def env_for(chrome) -> dict:
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k)}
    env["ARCHIFY_UPDATE_CHECK_DISABLED"] = "1"
    if chrome:
        env["ARCHIFY_CHROME"] = chrome
    else:
        env.pop("ARCHIFY_CHROME", None)
    return env


def _option(args, name):
    """The value after `name` in args (e.g. --quality), else None."""
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def plan(bundle_dir: Path | None, args, chrome) -> list:
    """The argv list(s) to run: one command, or (finalize without Chrome) validate, deliver and check in order."""
    cli = cli_path(bundle_dir)
    if cli is None:
        raise ArchifyError(health(bundle_dir)["reason"])
    if not args:
        raise ArchifyError("name an Archify command, e.g. `agylite diagram guide \"<scenario>\"` or "
                           "`agylite diagram finalize <type> <candidate.json> <output.html> --json`")
    node = [shutil.which("node") or "node", str(cli)]
    args = list(args)
    if args[0] != "finalize":
        return [node + args]
    if len(args) < 4 or args[1] not in TYPES:
        raise ArchifyError("finalize needs <type> <candidate.json> <output.html>")
    kind, candidate, output = args[1:4]
    if chrome:
        if kind == "explainer" and "--browser-check" not in args:
            args.append("--browser-check")   # required whenever Chrome is present (config/verification.yaml)
        return [node + args]
    shared = [a for name in ("--quality", "--repo-root") if _option(args, name) for a in (name, _option(args, name))]
    json_flag = ["--json"] if "--json" in args else []
    return [node + ["validate", kind, candidate, *shared, *json_flag],
            node + ["deliver", kind, candidate, output, *shared, *json_flag],
            node + ["check", output, "--require-provenance", *json_flag]]


def run(bundle_dir, args, cwd: Path, capture=False, log=print):
    """Run in the project; the exit code is Archify's (the first failing step's, for the no-Chrome finalize)."""
    chrome = find_chrome()
    steps = plan(bundle_dir, args, chrome)
    env = env_for(chrome)
    if len(steps) > 1:
        log(SKIPPED)
    out = []
    for argv in steps:
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=capture, text=True)
        out.append(p)
        if p.returncode:
            break
    return out[-1], {"browser_check": "on" if chrome else "skipped", "steps": len(out), "planned": len(steps)}


def self_test(bundle_dir: Path) -> dict:
    """Bundle self-test (MP5 §3.4): `archify validate <type> <example>` for each preserved JSON example — no browser."""
    examples = Path(bundle_dir) / "files" / "archify" / "archify" / "examples"
    codes = {}
    for f in sorted(examples.glob("*.json")):
        kind = f.name.rsplit(".", 2)[-2]
        if kind not in TYPES or ".base." in f.name or ".head." in f.name:
            continue
        p = subprocess.run([shutil.which("node") or "node", str(cli_path(bundle_dir)), "validate", kind, str(f), "--json"],
                           cwd=examples, env=env_for(None), capture_output=True, text=True)
        codes[f.name] = p.returncode
    return {"runtime": "archify", "exit_codes": codes, "ok": bool(codes) and not any(codes.values())}


def receipts(html: Path) -> list:
    """Evidence next to a delivered diagram: its receipts and screenshots, with sha256."""
    import hashlib
    folder = Path(html).parent
    stem = Path(html).stem
    found = sorted({p for p in folder.rglob("*") if p.is_file() and p != Path(html)
                    and (p.name.startswith(stem) or p.suffix.lower() in (".png", ".webp", ".jpg"))
                    and p.suffix.lower() in (".json", ".png", ".webp", ".jpg")})
    return [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in found]


def summary(stdout: str) -> dict:
    """The compact receipt fields of a `--json` finalize/check run (best-effort)."""
    try:
        data = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
    except (json.JSONDecodeError, IndexError):
        return {}
    return {k: data.get(k) for k in ("ok", "status", "command", "visualReview") if k in data}
