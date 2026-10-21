"""Parity ledger (IMPLEMENTATION_PLAN §6): one row per Tier 1 run in docs/plan/parity-ledger.json, rendered to
docs/plan/PARITY_LEDGER.md (generated; never hand-edited). Every new session resumes from it."""
import json
import subprocess
from pathlib import Path

from ...paths import repo_root

JSON_PATH = Path("docs/plan/parity-ledger.json")
MD_PATH = Path("docs/plan/PARITY_LEDGER.md")
UPSTREAM_DIRS = {"eng-addy": ["agent-skills"], "eng-pocock": ["skills", "agent-skills"], "eng-ponytail": ["ponytail"],
                 "design-taste": ["taste-skill"], "diagram-archify": ["archify"], "design-extract": ["design-extract"],
                 "youtube": ["youtube-agent-skill"], "browser-qa": ["gstack"], "research": ["Agent-Reach"]}


def _sha(path: Path):
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True)
    return p.stdout.strip() or None


def load(root: Path | None = None) -> dict:
    path = (root or repo_root()) / JSON_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"version": 1, "rows": [], "notes": []}


def append(report: dict, *, fix: str = "", next_step: str = "", root: Path | None = None) -> dict:
    from .suites import upstreams_dir
    root = root or repo_root()
    data = load(root)
    shas = {d: _sha(upstreams_dir() / d) for d in UPSTREAM_DIRS.get(report["suite"], []) if (upstreams_dir() / d).is_dir()}
    row = {"date": report.get("date"), "suite": report["suite"], "n": report.get("runs"), "bundle": report.get("bundle"),
           "agylite_commit": _sha(root), "upstream_shas": shas, "model": report.get("model"),
           "metrics": {m: {k: v.get(k) for k in ("baseline", "upstream", "agylite", "retained", "verdict")}
                       for m, v in report["metrics"].items()},
           "verdict": report["verdict"], "cost_usd": report.get("cost_usd"), "agent_seconds": report.get("agent_seconds"),
           "agylite_usage": report.get("agylite_usage"), "errors": report.get("errors"), "run_dir": report.get("run_dir"),
           "fix_applied": fix, "next_step": next_step}
    data["rows"].append(row)
    (root / JSON_PATH).write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    (root / MD_PATH).write_text(render(data), encoding="utf-8")
    return row


def note(text: str, root: Path | None = None):
    """A ledger note (e.g. a suite whose baseline waits for its instrument), kept with the rows."""
    root = root or repo_root()
    data = load(root)
    data["notes"].append(text)
    (root / JSON_PATH).write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    (root / MD_PATH).write_text(render(data), encoding="utf-8")


def _fmt(v):
    return "—" if v is None else (f"{v:.3g}" if isinstance(v, float) else str(v))


def render(data: dict) -> str:
    lines = ["# Parity ledger", "",
             "Generated from `docs/plan/parity-ledger.json` by `agylite/benchmark/quality/ledger.py`; do not edit by hand.",
             "Retained gain = (AgyLite − no skill) ÷ (original − no skill), sign flipped when lower is better. Same ≥ 0.90 ·",
             "near 0.70–0.90 · regressed < 0.70 or worse than no skill · inconclusive within run-to-run noise.", "",
             "| date | suite | n | bundle | AgyLite commit | model | metric: no skill / original / AgyLite (retained, verdict) | "
             "verdict | cost no skill / original / AgyLite | fix applied | next step |",
             "|---|---|---:|---|---|---|---|---|---|---|---|"]
    for r in data["rows"]:
        ms = "<br>".join(f"{m}: {_fmt(v['baseline'])} / {_fmt(v['upstream'])} / {_fmt(v['agylite'])} "
                         f"({_fmt(v['retained'])}, {v['verdict']})" for m, v in r["metrics"].items())
        c = r.get("cost_usd") or {}
        cost = " / ".join(f"${c.get(a, 0):.2f}" for a in ("baseline", "upstream", "agylite"))
        lines.append(f"| {r['date']} | {r['suite']} | {r['n']} | {r['bundle']} | {(r['agylite_commit'] or '')[:8]} | "
                     f"{r['model']} | {ms} | **{r['verdict']}** | {cost} | {r['fix_applied'] or '—'} | {r['next_step'] or '—'} |")
    if data.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {n}" for n in data["notes"]]
    return "\n".join(lines) + "\n"
