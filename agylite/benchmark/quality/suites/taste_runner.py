"""design-taste: build each Taste eval in three arms, then measure with Taste's own instruments.

After a session the built page is copied, without dot folders, to a neutral folder (so no arm's dealt direction
grants itself allowances), inspected with inspect.mjs (FAIL findings at 1440/768/390) and linted with lint.mjs. When
all arms of an eval are done, one blind judge scores their screenshots, labelled A/B/C by a fixed shuffle, with
references/critique.md (overall = 0.4 design + 0.3 usability + 0.2 creativity + 0.1 content).
"""
import json
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

from .. import harness
from . import load_suite, upstreams_dir

METRICS = {"inspector_fail": True, "lint_fail": True, "judge_overall": False}
TOOLS = "Read,Glob,Grep,Edit,Write,Bash"
SKIP = {".claude", ".taste-skill", ".git", "node_modules"}


def _skill_dir() -> Path:
    return upstreams_dir() / "taste-skill" / "skills" / "taste-skill"


def _evals():
    return {e["id"]: e for e in json.loads((_skill_dir() / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]}


def cells(cfg):
    return [{"task": str(t), "eval": t} for t in cfg["tasks"]]


def find_page(ws: Path):
    pages = [p for p in ws.rglob("*.html") if not set(p.relative_to(ws).parts) & SKIP]
    pages.sort(key=lambda p: (p.name != "index.html", len(p.relative_to(ws).parts), str(p)))
    return pages[0] if pages else None


def _node(script, *args, cwd, tmp):
    env = {**os.environ, "TASTE_SKILL_TMP": str(tmp)}
    Path(tmp).mkdir(parents=True, exist_ok=True)
    return subprocess.run(["node", str(_skill_dir() / "scripts" / script), *args], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=600)


def measure(page: Path, out: Path, app: bool, tmp: Path) -> dict:
    """Clean copy → inspect.mjs + lint.mjs; FAIL counts and the screenshot folder."""
    clean = out / "page"
    shutil.rmtree(clean, ignore_errors=True)
    shutil.copytree(page.parent, clean, ignore=lambda d, names: [n for n in names if n.startswith(".") or n in SKIP])
    flags = ["--app"] if app else []
    shots = out / "inspect"
    p = _node("inspect.mjs", page.name, "--out", str(shots), "--json", *flags, cwd=clean, tmp=tmp)
    try:
        ins = json.loads(p.stdout)
        ins_fail = sum(1 for f in ins.get("findings") or [] if f.get("level") == "FAIL")
    except ValueError:
        ins, ins_fail = None, None
    q = _node("lint.mjs", ".", "--json", *flags, cwd=clean, tmp=tmp)
    try:
        lint_fail = sum(1 for f in json.loads(q.stdout).get("findings") or [] if f.get("level") == "FAIL")
    except ValueError:
        lint_fail = None
    (out / "inspect.stderr.txt").write_text(p.stderr[-4000:], encoding="utf-8")
    return {"inspector_fail": ins_fail, "lint_fail": lint_fail, "shots": str(shots),
            "inspector_findings": [f"{f.get('level')} {f.get('id')}" for f in (ins or {}).get("findings") or []][:40]}


def run_cell(cell, ctx):
    cfg = load_suite("design-taste")
    ev = _evals()[cell["eval"]]
    ws = harness.fresh_workspace(ctx["label"])
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = harness.ArmSetup("upstream", project_skills=(str(_skill_dir()),))
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    rec = harness.run_session(ev["prompt"], ws, arm, model=ctx["model"], allowed_tools=TOOLS,
                              timeout=cfg.get("timeout_s", 1500), out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    page = find_page(ws)
    out = ctx["run_dir"] / "pages" / ctx["label"]
    out.mkdir(parents=True, exist_ok=True)
    if page is None:
        rec["metrics"] = {"inspector_fail": None, "lint_fail": None, "judge_overall": None}
        rec["note"] = "no HTML page produced"
        return rec
    m = measure(page, out, cell["eval"] in cfg.get("app_evals", []), ctx["run_dir"] / "taste-tmp")
    rec["metrics"] = {"inspector_fail": m["inspector_fail"], "lint_fail": m["lint_fail"], "judge_overall": None}
    rec["shots"], rec["inspector_findings"] = m["shots"], m["inspector_findings"]
    return rec


JUDGE = """You are a design juror. Score each of the {n} pages below by the rubric that follows. You do not know who
made them or how; judge only what you see in the screenshots. Read every image listed for a page before scoring it.

The brief all pages answered:
{brief}

Pages (screenshots at 1440 / 768 / 390 px wide; "fold" is the first screen, "page-NN" the full page in parts):
{listing}

Rubric (Taste references/critique.md):
{rubric}

Return ONLY JSON: {{"pages": {{"A": {{"design": n, "usability": n, "creativity": n, "content": n, "overall": n, "notes": "…"}}, …}}}}
with overall = 0.4·design + 0.3·usability + 0.2·creativity + 0.1·content."""


def finalize(records, ctx):
    """One blind judge per eval over all arms that produced a page (fixed shuffle per eval id and run)."""
    rubric = (_skill_dir() / "references" / "critique.md").read_text(encoding="utf-8")
    evals = _evals()
    for key in sorted({(r["task"], r["run"]) for r in records}):
        group = [r for r in records if (r["task"], r["run"]) == key and r.get("shots") and Path(r["shots"]).is_dir()]
        if not group:
            continue
        random.Random(f"{key[0]}-{key[1]}").shuffle(group)
        jdir = ctx["run_dir"] / "judge" / f"eval-{key[0]}-run-{key[1]}"
        shutil.rmtree(jdir, ignore_errors=True)
        listing = []
        for letter, r in zip("ABCDEF", group):
            d = jdir / letter
            d.mkdir(parents=True)
            names = sorted(p.name for p in Path(r["shots"]).glob("*.jpg"))
            keep = [n for n in names if "fold" in n] + [n for n in names if "page-0" in n][:6]
            for n in keep:
                shutil.copy2(Path(r["shots"]) / n, d / n)
            listing.append(f"- Page {letter}: " + ", ".join(f"{letter}/{n}" for n in keep))
        prompt = JUDGE.format(n=len(group), brief=evals[int(key[0])]["prompt"], listing="\n".join(listing),
                              rubric=rubric)
        raw = subprocess.run(["claude", "-p", "--setting-sources", "project,local", "--strict-mcp-config",
                              "--model", ctx.get("judge_model") or harness.DEFAULT_MODEL, "--allowedTools", "Read"],
                             input=prompt, text=True, capture_output=True, cwd=jdir, timeout=900).stdout
        (jdir / "verdict.raw.txt").write_text(raw, encoding="utf-8")
        m = re.search(r"\{[\s\S]*\}", raw)
        try:
            scores = json.loads(m.group(0))["pages"] if m else {}
        except (ValueError, KeyError):
            scores = {}
        for letter, r in zip("ABCDEF", group):
            s = scores.get(letter) or {}
            r["judge"] = {"label": letter, **s}
            r["metrics"]["judge_overall"] = s.get("overall")
    return records
