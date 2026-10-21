"""designlang runtime (MP4 §2.2, design/inspiration-extract): an isolated npm install, `runtimes/designlang-<version>`.

The version is the audited pin (`package` in docs/audit/evidence/upstream-staging-snapshot.yaml). `npm install
--ignore-scripts` (designlang ships no install script; supply-chain safety), then Playwright's Chromium into the
runtime's own `browsers/` (PLAYWRIGHT_BROWSERS_PATH). lock.json records the version and npm integrity hash.
Not used: `--smart` (paid third-party APIs), `designlang mcp`, the extensions. Network: install and every extraction.
"""
import json
import shutil
import subprocess
from pathlib import Path

MIN_NODE = 20


class DesignlangError(RuntimeError):
    pass


def pinned_version() -> str:
    from ..bundle.rules import evidence_dir, load_yaml
    snap = load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"]["designlang"]
    return snap["package"].split("@", 1)[1]


def node_version():
    from .taste import node_version as nv
    return nv()


def runtime_dir(home: Path, version: str | None = None) -> Path:
    return Path(home) / "runtimes" / f"designlang-{version or pinned_version()}"


class Runtime:
    """What `agylite design extract` needs: the CLI, node, the package dir (for fuse_design_md.mjs), the env."""

    def __init__(self, home: Path):
        self.dir = runtime_dir(home)
        self.version = pinned_version()
        self.bin = str(self.dir / "node_modules" / ".bin" / "designlang")
        self.node = shutil.which("node") or "node"
        self.pkg = self.dir / "node_modules" / "designlang"

    def env(self) -> dict:
        return {"PLAYWRIGHT_BROWSERS_PATH": str(self.dir / "browsers")}


def runtime(home: Path) -> Runtime:
    if health(home)["status"] != "ready":
        raise DesignlangError("designlang is not installed: run `agylite runtime install designlang` (network, ~150 MB)")
    return Runtime(home)


def health(home: Path) -> dict:
    d = runtime_dir(home)
    lock = d / "lock.json"
    if not lock.is_file():
        return {"runtime": "designlang", "status": "not-installed",
                "reason": "run `agylite runtime install designlang` (network: npm + Chromium)"}
    info = json.loads(lock.read_text(encoding="utf-8"))
    browser = any((d / "browsers").glob("chromium*"))
    ok = (d / "node_modules" / ".bin" / "designlang").exists() and browser
    return {"runtime": "designlang", "status": "ready" if ok else "broken", "version": info.get("version"),
            "browser": "chromium present" if browser else "chromium missing", "lock": info.get("integrity"),
            "path": str(d)}


def install(home: Path, log=print) -> dict:
    v = node_version()
    if not v or v[0] < MIN_NODE:
        raise DesignlangError(f"designlang needs node>={MIN_NODE}" + (f" (found {'.'.join(map(str, v))})" if v else ""))
    npm = shutil.which("npm")
    if not npm:
        raise DesignlangError("npm not found on PATH")
    version = pinned_version()
    d = runtime_dir(home, version)
    d.mkdir(parents=True, exist_ok=True)
    log(f"  npm install designlang@{version} (no install scripts) → {d}")
    p = subprocess.run([npm, "install", "--prefix", str(d), "--no-audit", "--no-fund", "--ignore-scripts",
                        f"designlang@{version}"], capture_output=True, text=True)
    if p.returncode != 0:
        raise DesignlangError(f"npm install failed: {(p.stderr or p.stdout).strip()[-300:]}")
    env = {"PATH": str(Path(npm).parent), "HOME": str(d), "PLAYWRIGHT_BROWSERS_PATH": str(d / "browsers")}
    log("  playwright install chromium (once, ~150 MB)")
    p = subprocess.run([str(d / "node_modules" / ".bin" / "playwright"), "install", "chromium"], env=env,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise DesignlangError(f"playwright install chromium failed: {(p.stderr or p.stdout).strip()[-300:]}")
    entry = json.loads((d / "package-lock.json").read_text(encoding="utf-8"))["packages"]["node_modules/designlang"]
    if entry.get("version") != version:
        raise DesignlangError(f"npm resolved designlang {entry.get('version')}, expected the audited {version}")
    (d / "lock.json").write_text(json.dumps({"version": version, "integrity": entry.get("integrity")}, indent=1),
                                 encoding="utf-8")
    return health(home)
