"""browser-qa: QA the planted-defect fixture site in three arms; count defects reported and defects fixed."""
import re
import shutil
import tempfile
from pathlib import Path

from ....paths import agylite_home, repo_root
from ....runtimes import browser
from .. import harness

METRICS = {"defects_reported": False, "defects_fixed": False}
TOOLS = "Read,Glob,Grep,Edit,Write,Bash"
FIXTURE = Path("tests") / "fixtures" / "browser" / "broken-site"
PROMPT = ("QA the small website in this folder (index.html, a lamp shop; serve it locally to test it). Find every bug, "
          "fix each one in the files here, and re-check. Expected behaviour: clicking \"Add to cart\" shows \"Added to "
          "cart\" in the status line. Do not ask me questions. When done, list every bug you found in findings.md, "
          "one per line, saying what was wrong.")
# Planted defect → (what a report names it by, what Agylite's browser check reports while it is still there)
DEFECTS = {
    "console-error": (r"undefinedFunction|ReferenceError|is not defined|console error|javascript error|js error",
                      r"console error: .*undefinedFunction"),
    "missing-image": (r"missing-lamp|\b404\b|broken image|image (?:is )?missing|not found",
                      r"failed request: .*missing-lamp"),
    "overflow": (r"overflow|horizontal(?:ly)? scroll|wider than|640\s*px|\b390\b|mobile width|narrow screen",
                 r"horizontal overflow"),
    "dead-button": (r"add to cart|button (?:does nothing|did nothing|has no effect)|click handler|empty (?:click )?handler",
                    r"flow failed"),
    "missing-alt": (r"\balt\b", r"image without alt text"),
}


def cells(cfg):
    return [{"task": t} for t in cfg["tasks"]]


def _workspace(label: str) -> Path:
    """A copy of the fixture without its `// planted:` comments (they would hand every arm the answers)."""
    ws = harness.fresh_workspace(label)
    src = repo_root() / FIXTURE
    for f in src.iterdir():
        if f.is_file():
            text = f.read_text(encoding="utf-8") if f.suffix == ".html" else None
            if text is None:
                shutil.copy2(f, ws / f.name)
            else:
                (ws / f.name).write_text(re.sub(r"[ \t]*// planted:[^\n]*", "", text), encoding="utf-8")
    return ws


def _upstream_arm() -> harness.ArmSetup:
    """gstack the way its users run it: the generated `qa` skill from gstack's own install (its browse daemon and
    paths point back into that install), invoked as /qa."""
    return harness.ArmSetup("upstream", project_skills=(str(Path.home() / ".claude" / "skills" / "qa"),))


def remaining(ws: Path, home) -> list:
    """Planted defects Agylite's browser check still finds in the workspace, with the fixture's own flow (an agent
    cannot weaken the check by editing its copy)."""
    with tempfile.TemporaryDirectory() as out:
        r = browser.check(ws, home, flows=repo_root() / FIXTURE / ".agylite" / "flows.yaml", out=out)
    text = "\n".join(r.get("defects") or [])
    return [d for d, (_said, seen) in DEFECTS.items() if re.search(seen, text)]


def reported(text: str) -> list:
    return [d for d, (said, _seen) in DEFECTS.items() if re.search(said, text, re.I)]


def run_cell(cell, ctx):
    ws = _workspace(ctx["label"])
    if ctx["arm"] == "upstream":
        arm, prompt = _upstream_arm(), "/qa " + PROMPT
    elif ctx["arm"] == "baseline":
        arm, prompt = harness.ArmSetup("baseline"), PROMPT
    else:
        arm, prompt = harness.agylite_arm(ctx["run_dir"], ctx.get("python")), PROMPT
    rec = harness.run_session(prompt, ws, arm, model=ctx["model"], allowed_tools=TOOLS, timeout=1500,
                              out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    findings = (ws / "findings.md").read_text(encoding="utf-8", errors="replace") if (ws / "findings.md").is_file() else ""
    out = ctx["run_dir"] / "answers"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{ctx['label']}.md").write_text(findings + "\n---\n" + (rec.get("result") or ""), encoding="utf-8")
    left = remaining(ws, agylite_home())
    rec["metrics"] = {"defects_reported": len(reported(findings)), "defects_fixed": len(DEFECTS) - len(left)}
    rec["defects_left"] = left
    return rec
