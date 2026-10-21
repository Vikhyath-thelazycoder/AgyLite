"""MP2 Tier 0: deterministic, offline suites that gate every change and every upstream update.

T0.1 routing out of distribution (OOD set + Addy's trigger prompts) · T0.2 context selection (is the right upstream
file loaded first?) · T0.3 fidelity (how much of the primary source the agent sees; reported, not gated) · T0.4 token
no-regression against a saved baseline · T0.5 engine and tool self-tests.
"""
import contextlib
import io
import json
import re
from pathlib import Path

import yaml

from ...paths import repo_root

TOKEN_SCENARIO_LIMIT = 0.15   # MP2 T0.4: no scenario more than +15 % over baseline
TOKEN_TOTAL_LIMIT = 0.05      # … and the total no more than +5 %
FIDELITY_WARN = 0.50          # warn when the primary source is under half loaded
HEADER = re.compile(r"^### (files/\S+) — .*?(?:\(sections (\d+)/(\d+), ≈(\d+) of (\d+) est\. tokens\))?$", re.M)


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _hit(ids, entry):
    return [i for i in ids if (i.startswith(entry) if entry.endswith("/") else i == entry)]


def routing(root: Path, router=None) -> dict:
    """T0.1: share of scenarios whose `expect` is present and `forbid` absent, per file and per domain."""
    from ...routing import ProjectFacts, Router, capability_ids
    router = router or Router()
    out = {"sets": {}, "failed": [], "by_domain": {}}
    for name in ("ood_scenarios.yaml", "addy_trigger_scenarios.yaml"):
        path = root / "tests" / "routing" / name
        if not path.is_file():
            continue
        passed = total = 0
        for sc in _yaml(path).get("scenarios") or []:
            ids = capability_ids(router.route(sc["request"], project=ProjectFacts(stage=sc.get("stage", "unknown"))))
            expect = sc.get("expect") or []
            missing = [] if sc.get("pending") else [e for e in expect if e not in ids]
            bad = [] if sc.get("pending_forbid") else [i for f in sc.get("forbid") or [] for i in _hit(ids, f)
                                                         if i not in expect]
            ok = not missing and not bad
            passed += ok
            total += 1
            dom = (expect[0] if expect else (sc.get("forbid") or ["unknown/"])[0]).split("/")[0]
            d = out["by_domain"].setdefault(dom, [0, 0])
            d[0] += ok
            d[1] += 1
            if not ok:
                out["failed"].append({"id": sc["id"], "set": name, "missing": missing, "forbidden": bad})
        out["sets"][name] = [passed, total]
    return out


def _first_files(cid, query, bundle):
    from ...context import levels
    from ...context.budget import load_budgets
    from ...context.loader import ContextLoader
    loader = ContextLoader(None, None, bundle, use_cache=False)
    text = levels.capability_context(loader, [cid], load_budgets(), query=query)["text"]
    return HEADER.findall(text)


def agency_in_first_two(entries, priority) -> list:
    """MP3 §4: Agency files among a capability's first two ranked sources that rank ahead of a non-Agency source
    (Agency may follow every non-Agency source; [] when Agency is all it has)."""
    from ...context import levels
    ranked = [e["path"] for e in levels._rank_files(entries, None, priority)]
    others = [i for i, p in enumerate(ranked) if not p.startswith("files/agency/")]
    last = others[-1] if others else -1
    return [p for i, p in enumerate(ranked[:2]) if p.startswith("files/agency/") and i < last]


def context_selection(root: Path, bundle: Path) -> dict:
    """T0.2: the expected first file loads first, with and without a request; and no Agency file ranks in the first
    two sources of an engineering/testing capability (MP3 §4)."""
    expected = _yaml(root / "tests" / "context" / "expected_sources.yaml")
    requests = _yaml(root / "tests" / "context" / "fidelity_requests.yaml")
    rows = []
    for cid, path in expected.items():
        got = {}
        for label, query in (("no request", None), ("request", requests.get(cid) or cid)):
            heads = _first_files(cid, query, bundle)
            got[label] = heads[0][0] if heads else None
        rows.append({"capability": cid, "expected": path, **got,
                     "ok": all(v == path for v in got.values())})
    from ...context import levels
    from ...context.loader import ContextLoader
    from ...registry import loader as registry
    loader, agency = ContextLoader(None, None, bundle, use_cache=False), {}
    for cid, card in registry.load_cards().items():
        if cid.split("/", 1)[0] in ("engineering", "testing"):
            bad = agency_in_first_two(loader.files_of(cid), card.get("sources_priority") or [])
            if bad:
                agency[cid] = bad
    return {"rows": rows, "agency_first_two": agency, "ok": all(r["ok"] for r in rows) and not agency}


def fidelity(root: Path, bundle: Path) -> dict:
    """T0.3: for each capability's primary file, sections and tokens loaded ÷ total for a representative request."""
    from ...registry import loader as registry
    requests = _yaml(root / "tests" / "context" / "fidelity_requests.yaml")
    rows = []
    for cid, card in registry.load_cards().items():
        prio = card.get("sources_priority")
        if not prio:
            continue
        heads = _first_files(cid, requests.get(cid) or card["description"], bundle)
        primary = next((h for h in heads if re.fullmatch(prio[0].replace("*", ".*"), h[0])), None)
        if primary is None:
            rows.append({"capability": cid, "primary": prio[0], "loaded": False})
            continue
        path, s_in, s_all, t_in, t_all = primary
        if s_all:
            share_s, share_t = int(s_in) / int(s_all), int(t_in) / int(t_all)
            detail = f"sections {s_in}/{s_all}, ≈{t_in} of {t_all} est. tokens"
        else:
            share_s = share_t = 1.0
            detail = "whole file"
        rows.append({"capability": cid, "primary": path, "loaded": True, "sections": round(share_s, 3),
                     "tokens": round(share_t, 3), "detail": detail, "warn": share_t < FIDELITY_WARN})
    return {"rows": rows}


def tokens(root: Path, baseline: dict | None) -> dict:
    """T0.4: per-scenario NEW totals (`--compare`), checked against a saved baseline when one is given."""
    from ...diagnostics.benchmark import compare
    with contextlib.redirect_stdout(io.StringIO()):
        result = compare(repeats=1)
    now = {r["id"]: r["new_bytes"] // 4 for r in result["rows"]}
    out = {"scenarios": now, "total": sum(now.values()), "regressions": [], "ok": True}
    if baseline and baseline.get("tokens"):
        base = baseline["tokens"]["scenarios"]
        for sid, n in now.items():
            if sid in base and base[sid] and n > base[sid] * (1 + TOKEN_SCENARIO_LIMIT):
                out["regressions"].append({"id": sid, "baseline": base[sid], "now": n})
        btotal = baseline["tokens"]["total"]
        out["total_change"] = round(out["total"] / btotal - 1, 4) if btotal else None
        out["ok"] = not out["regressions"] and (out["total_change"] or 0) <= TOKEN_TOTAL_LIMIT
    return out


def self_tests(bundle: Path) -> dict:
    """T0.5: the bundle's engine self-tests (Unlazy, UI/UX Pro Max; MP4/MP5 add Taste, YouTube, Archify)."""
    from ...bundle.build import _self_tests
    results = _self_tests(bundle, log=lambda *_: None)
    return {"results": results, "ok": all(r["exit"] == 0 for r in results.values())}


def run(root: Path | None = None, bundle: Path | None = None, baseline: dict | None = None) -> dict:
    from ...paths import current_bundle
    root = root or repo_root()
    bundle = bundle or current_bundle()
    report = {"tier": 0, "bundle": bundle.name if bundle else None, "routing": routing(root)}
    if baseline and baseline.get("routing"):
        before = {f["id"] for f in baseline["routing"]["failed"]}
        report["routing"]["new_failures"] = [f for f in report["routing"]["failed"] if f["id"] not in before]
    else:
        report["routing"]["new_failures"] = []
    if bundle is not None:
        report["context_selection"] = context_selection(root, bundle)
        report["fidelity"] = fidelity(root, bundle)
        report["self_tests"] = self_tests(bundle)
    report["tokens"] = tokens(root, baseline)
    report["ok"] = (not report["routing"]["new_failures"] and report["tokens"]["ok"]
                    and report.get("context_selection", {}).get("ok", True)
                    and report.get("self_tests", {}).get("ok", True))
    return report


def render(r: dict) -> str:
    lines = [f"# Tier 0 (bundle {r['bundle']}): {'PASS' if r['ok'] else 'FAIL'}", "", "## T0.1 Routing (out of distribution)", ""]
    for name, (p, t) in r["routing"]["sets"].items():
        lines.append(f"- {name}: {p}/{t} ({p / t:.0%})" if t else f"- {name}: empty")
    lines.append("- per domain: " + ", ".join(f"{d} {p}/{t}" for d, (p, t) in sorted(r["routing"]["by_domain"].items())))
    if r["routing"]["new_failures"]:
        lines.append("- **new failures vs baseline:** " + ", ".join(f["id"] for f in r["routing"]["new_failures"]))
    if "context_selection" in r:
        lines += ["", "## T0.2 Context selection", "", "| capability | expected first | no request | request | ok |",
                  "|---|---|---|---|:---:|"]
        lines += [f"| {x['capability']} | {x['expected']} | {x['no request']} | {x['request']} | {'✔' if x['ok'] else '✗'} |"
                  for x in r["context_selection"]["rows"]]
        agency = r["context_selection"].get("agency_first_two") or {}
        lines += ["", "Agency in the first two sources (MP3 §4): " + ("; ".join(f"{c}: {', '.join(p)}"
                                                                        for c, p in agency.items()) or "none")]
        lines += ["", "## T0.3 Fidelity (primary source; reported, not gated)", "",
                  "| capability | primary | loaded | tokens |", "|---|---|---|---:|"]
        for x in r["fidelity"]["rows"]:
            lines.append(f"| {x['capability']} | {x['primary']} | {x.get('detail', 'NOT LOADED')} | "
                         f"{x.get('tokens', 0):.0%}{' ⚠' if x.get('warn') or not x['loaded'] else ''} |")
        lines += ["", "## T0.5 Engine self-tests", ""]
        lines += [f"- {k}: exit {v['exit']}" for k, v in r["self_tests"]["results"].items()]
    t = r["tokens"]
    lines += ["", "## T0.4 Tokens", "", f"- total NEW ≈ {t['total']:,} est. tokens over {len(t['scenarios'])} scenarios"
              + (f" ({t['total_change']:+.1%} vs baseline)" if t.get("total_change") is not None else "")]
    lines += [f"- **regression** {x['id']}: {x['baseline']:,} → {x['now']:,}" for x in t["regressions"]]
    return "\n".join(lines) + "\n"


def save_baseline(report: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {k: report[k] for k in ("tier", "bundle", "routing", "tokens") if k in report}
    if "fidelity" in report:
        keep["fidelity"] = report["fidelity"]
    path.write_text(json.dumps(keep, indent=1, sort_keys=True) + "\n", encoding="utf-8")
