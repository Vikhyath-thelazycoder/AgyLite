"""research: four fetch tasks with checkable answers, three arms, success checked on the final answer."""
import os
import re
from pathlib import Path

from ....paths import agylite_home, current_bundle
from .. import harness
from . import upstreams_dir

METRICS = {"success": False}
TOOLS = "Read,Glob,Grep,Edit,Write,Bash,WebFetch,WebSearch"
SUFFIX = ("\n\nDo not ask me questions. Answer in a few lines and cite the URL of every source you used. Write the "
          "answer to answer.md in this folder as well.")
TASKS = {
    "page": ("Read https://docs.python.org/3/library/html.parser.html. What is the default value of the "
             "convert_charrefs argument of html.parser.HTMLParser, and what does it do?",
             lambda a: bool(re.search(r"\bTrue\b", a)) and "docs.python.org" in a and re.search(r"charref|character reference", a, re.I)),
    "rss": ("List the titles and links of the 3 newest items in the RSS feed https://hnrss.org/frontpage.",
            lambda a: len(set(re.findall(r"https?://[^\s)\]>]+", a)) - {"https://hnrss.org/frontpage"}) >= 3),
    # Phase 9: "Me at the zoo" was famous enough for plain Claude to answer from memory; this one (a small baking
    # channel, ~44k views) can only be answered from its transcript (110 °F / 43 °C at 1:07, Minnesota at 2:21).
    "youtube-transcript": ("In the YouTube video https://www.youtube.com/watch?v=EI4rvzpTDj8, what is the hottest water "
                           "the speaker says you may feed a sourdough starter with, and in which US state did the "
                           "speaker make a starter from scratch in winter? Quote the speaker with the timestamps.",
                           lambda a: re.search(r"\b110\b", a) and re.search(r"minnesota", a, re.I)
                           and re.search(r"\b0?0?:?\d{1,2}:\d{2}\b|\b\d+\s*s(ec(onds?)?)?\b", a)),
    "github": ("Find the GitHub repository of the Archify diagram tool by the user tt-a1i. What license is it "
               "under, and what is the repository's URL?",
               lambda a: "github.com/tt-a1i/archify" in a.lower() and re.search(r"\bMIT\b", a)),
}


def cells(cfg):
    return [{"task": t} for t in cfg["tasks"]]


def _upstream_arm() -> harness.ArmSetup:
    """Agent-Reach the way its users run it: its skill installed, its tools on PATH (yt-dlp from the research
    runtime's venv; gh and twitter/rdt are not installed here, as for any user without them)."""
    from ....runtimes import research
    skill = Path(harness.fresh_workspace("agentreach-skill")) / "agent-reach"
    skill.mkdir()
    src = upstreams_dir() / "Agent-Reach" / "agent_reach" / "skill"
    (skill / "SKILL.md").write_text((src / "SKILL_en.md").read_text(encoding="utf-8"), encoding="utf-8")
    venv_bin = research.tool(agylite_home(), current_bundle(), "yt-dlp").parent
    return harness.ArmSetup("upstream", project_skills=(str(skill),),
                            env={"PATH": f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}"})


def run_cell(cell, ctx):
    prompt, check = TASKS[cell["task"]]
    ws = harness.fresh_workspace(ctx["label"])
    if ctx["arm"] == "upstream":
        arm = _upstream_arm()
    elif ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    rec = harness.run_session(prompt + SUFFIX, ws, arm, model=ctx["model"], allowed_tools=TOOLS, timeout=600,
                              out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    answer = (ws / "answer.md").read_text(encoding="utf-8", errors="replace") if (ws / "answer.md").is_file() else ""
    answer = answer + "\n" + (rec.get("result") or "")
    out = ctx["run_dir"] / "answers"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{ctx['label']}.md").write_text(answer, encoding="utf-8")
    rec["metrics"] = {"success": int(bool(check(answer)))}
    return rec
