"""Browser verification in `agylite verify` (D-049, IMPLEMENTATION_PLAN §2.2): UI or website work — any style/markup
change, or `--browser` — is done only when the project's tests pass AND the browser check passes. Without the browser
runtime the check is NOT_RUN (BLOCKED), never a pass. The check's report.json, screenshots and logs are artefacts."""
import sys
from pathlib import Path

from ..paths import agylite_home
from ..runtimes import browser
from .design import design_files
from .detect import Check


def checks(project, changed, *, requested=False, url=None, flows=None) -> list:
    files = design_files(changed)
    if not (requested or files):
        return []
    why = "browser check requested" if requested else f"UI changed: {', '.join(files[:5])}"
    if browser.health(agylite_home())["status"] != "ready":
        return [(Check("browser", "browser check", [], "node",
                       notes=["NOT_RUN: browser runtime missing (`agylite runtime install browser`)"]), None, why, [])]
    cmd = [sys.executable, "-m", "agylite.cli", "browser-check", "--project", str(project.root)]
    cmd += ["--url", url] if url else []
    cmd += ["--flows", str(flows)] if flows else []
    return [(Check("browser", "browser check", [], "node"), cmd, why, [])]


def result(project_root: Path, r: dict) -> dict:
    """Defects and artefacts (with sha256) from the newest browser evidence folder."""
    import json
    base = Path(project_root) / ".agylite" / "evidence" / "browser"
    runs = sorted(p for p in base.glob("*") if (p / "report.json").is_file()) if base.is_dir() else []
    if not runs:
        return {}
    rep = json.loads((runs[-1] / "report.json").read_text(encoding="utf-8"))
    rel = runs[-1].relative_to(project_root).as_posix()
    return {"defects": rep["defects"], "artifacts": [{"path": f"{rel}/{a['path']}", "sha256": a["sha256"]}
                                                    for a in rep["artifacts"]] + [{"path": f"{rel}/report.json"}]}
