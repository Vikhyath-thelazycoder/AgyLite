"""design-extract: designlang's extraction benchmark, the original CLI against `agylite design extract`.

Both arms produce designlang's per-site `<host>-DESIGN.md`; its front matter (`tokens.colors.primary`,
`tokens.typography.sans`) is scored against bench/sites.json with bench/score.js's own colorHit and fontHit. The AgyLite
arm reads the per-site file, not the project DESIGN.md, whose primary is hue-shifted on purpose (systems, never
identity); the section count is taken from the project DESIGN.md. No skill means no extractor and no DESIGN.md, so the
baseline arm scores 0 without running anything.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ....design import extract
from ....paths import agylite_home
from ....runtimes import designlang
from . import load_suite, upstreams_dir

METRICS = {"color_hit": False, "font_hit": False, "design_md_sections": False}
PKG_ROOT = Path(__file__).resolve().parents[4]


def _bench() -> Path:
    return upstreams_dir() / "design-extract" / "bench"


def _truths() -> dict:
    return {s["site"]: s for s in json.loads((_bench() / "sites.json").read_text(encoding="utf-8"))["sites"]}


def cells(cfg):
    return [{"task": site, "site": site} for site in cfg["tasks"]]


def sections(md: str) -> int:
    heads = {line[2:].strip() for line in md.splitlines() if line.startswith("# ")}
    return sum(1 for s in extract.DESIGN_MD_SECTIONS if s in heads)


def hits(primary, font, truth) -> dict:
    """bench/score.js colorHit/fontHit through node; a dimension without ground truth scores None, as upstream."""
    code = ("const [s, p, f, t] = process.argv.slice(1); const m = await import(s); const truth = JSON.parse(t);"
            "console.log(JSON.stringify({color: truth.primary?.length ? m.colorHit(p || null, truth.primary) : null,"
            " font: truth.font?.length ? m.fontHit(f || null, truth.font) : null}));")
    p = subprocess.run(["node", "--input-type=module", "-e", code, (_bench() / "score.js").as_uri(), primary or "",
                        font or "", json.dumps(truth)], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(p.stdout)


def _site_md(out: Path, site: str) -> Path:
    return next((out / extract.host_of(f"https://{site}")).glob("*-DESIGN.md"))


def run_cell(cell, ctx):
    site, arm = cell["site"], ctx["arm"]
    rec = {"label": ctx["label"], "arm": arm}
    if arm == "baseline":
        return {**rec, "metrics": {"color_hit": 0, "font_hit": 0, "design_md_sections": 0},
                "note": "no extractor, no DESIGN.md"}
    timeout = load_suite("design-extract").get("timeout_s", 300)
    rt = designlang.runtime(agylite_home())
    work = Path(ctx["run_dir"]) / ctx["label"]
    work.mkdir(parents=True, exist_ok=True)
    env = extract.child_env(dict(os.environ), rt.env())
    started = time.monotonic()
    with tempfile.TemporaryDirectory(dir=work) as tmp:   # designlang writes its own files; keep only what is scored
        if arm == "upstream":
            out = Path(tmp)
            argv = [rt.bin, f"https://{site}", "--out", str(out / extract.host_of(f"https://{site}"))]
            design_md = None
        else:
            proj = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
            out = proj / extract.DEFAULT_OUT
            argv = [sys.executable, "-m", "agylite.cli", "design", "extract", f"https://{site}"]
            env["PYTHONPATH"] = str(PKG_ROOT)
            design_md = proj / "DESIGN.md"
        p = subprocess.run(argv, cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout)
        rec["duration_ms"] = int((time.monotonic() - started) * 1000)
        if p.returncode != 0:
            return {**rec, "error": f"exit {p.returncode}: {(p.stderr or p.stdout).strip()[-300:]}", "metrics": {}}
        site_md = _site_md(out, site)
        fm, _ = extract._split(site_md.read_text(encoding="utf-8"))
        tokens = fm.get("tokens") or {}
        primary = (tokens.get("colors") or {}).get("primary")
        font = (tokens.get("typography") or {}).get("sans")
        final = (design_md or site_md).read_text(encoding="utf-8")
        (work / f"{arm}-DESIGN.md").write_text(final, encoding="utf-8")
    h = hits(primary, font, _truths()[site])
    rec.update(predicted={"primary": primary, "font": font},
               metrics={"color_hit": None if h["color"] is None else int(h["color"]),
                        "font_hit": None if h["font"] is None else int(h["font"]),
                        "design_md_sections": sections(final)})
    return rec
