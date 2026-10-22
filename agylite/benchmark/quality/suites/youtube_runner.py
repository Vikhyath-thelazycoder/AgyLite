"""youtube: yt-script tasks in three arms; the HOOK line is scored with the upstream's own hookscore.py."""
import json
import re
import subprocess
from pathlib import Path

from .. import harness
from . import upstreams_dir

METRICS = {"hook_verdict": False, "on_screen_beats": False}
TOOLS = "Read,Glob,Grep,Edit,Write,Bash"
VOICE = ("I make YouTube videos about home-office setups for remote workers (about 8,000 subscribers). I talk "
         "casually and plainly, to one remote worker who is tired of back pain and bad calls. I never say "
         "\"game-changer\", \"unlock\" or \"let's dive in\", and I never claim numbers I have not measured.")
IDEAS = {
    "desk-lamps": "I tested five cheap desk lamps for a month to fix the glare on my video calls.",
    "cable-management": "How I hid every cable under my desk for under 30 dollars, and the one mistake that cost me a weekend.",
    "standing-desk": "One year with a standing desk: what changed, what did not, and whether I would buy it again.",
}
PROMPT = """{voice}

Write the script for my next video: {idea}

Do not ask me questions; make reasonable assumptions and say what you assumed. Save the finished script as script.md
in this folder. In script.md, put the single opening line I should record first on its own line, formatted exactly as
`HOOK: <the line>`."""
HOOK = re.compile(r"^\W*HOOK\W*:\W*(.+?)\W*$", re.M | re.I)


def _skill() -> Path:
    return upstreams_dir() / "youtube-agent-skill" / "skills" / "yt-script"


def cells(cfg):
    return [{"task": t} for t in cfg["tasks"]]


def hook_score(line: str):
    p = subprocess.run(["python3", "-I", str(_skill() / "hookscore.py"), "--hook", line, "--json"],
                       capture_output=True, text=True, timeout=60)
    try:
        return json.loads(p.stdout)[0]
    except (ValueError, IndexError):
        return None


def score_script(text: str) -> dict:
    m = HOOK.search(text or "")
    scored = hook_score(m.group(1).strip().strip('"“”')) if m else None
    return {"hook": m.group(1).strip() if m else None, "hookscore": scored,
            "metrics": {"hook_verdict": scored["verdict"] if scored else 0,
                        "on_screen_beats": int(len(re.findall(r"ON[ -]SCREEN", text or "", re.I)) >= 3)}}


def run_cell(cell, ctx):
    ws = harness.fresh_workspace(ctx["label"])
    if ctx["arm"] == "upstream":
        arm = harness.ArmSetup("upstream", project_skills=(str(_skill()),))
    elif ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    rec = harness.run_session(PROMPT.format(voice=VOICE, idea=IDEAS[cell["task"]]), ws, arm, model=ctx["model"],
                              allowed_tools=TOOLS, timeout=900, out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    script = ws / "script.md"
    text = script.read_text(encoding="utf-8", errors="replace") if script.is_file() else ""
    out = ctx["run_dir"] / "scripts"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{ctx['label']}.md").write_text(text, encoding="utf-8")
    scored = score_script(text)
    rec.update(hook=scored["hook"], hookscore=scored["hookscore"], metrics=scored["metrics"])
    return rec
