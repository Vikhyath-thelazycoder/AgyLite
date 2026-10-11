"""Impact of a change (P12, spec §23, §74; A-1 duty for P15): affected files + the tests that cover them, within the
code-surface budget (config/budgets.yaml code_files_per_task).

Graph first (Graphify reverse traversal); when the runtime or graph is unavailable the limited structural analysis
in `structural.py` is used and the result says so. Nothing is ever truncated silently: `omitted` counts what the
limit dropped, `unknown` lists what could not be resolved.
"""
import subprocess
import time
from pathlib import Path

from ..context.budget import load_budgets
from ..isolation.guard import guard_for
from . import structural

FALLBACK_NOTICE = "graph-based analysis unavailable; limited structural analysis used"
DEFAULT_DEPTH = 2


def changed_files(root) -> list:
    """Working-tree changes against HEAD (staged, unstaged, untracked), repo-relative; [] outside git.
    The OS's own project state (`.agylite/`) is never a code change."""
    try:
        p = subprocess.run(["git", "status", "--porcelain", "-uall", "--no-renames"], cwd=root, capture_output=True,
                           text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if p.returncode:
        return []
    paths = {line[3:].strip().strip('"') for line in p.stdout.splitlines() if len(line) > 3}
    return sorted(x for x in paths if not x.startswith(".agylite/"))


def code_limit(budgets=None) -> int:
    return int(((budgets or load_budgets()).get("code_files_per_task") or {}).get("value", 12))


def _normalize(project, paths):
    guard = guard_for(project)
    root = project.root.resolve()
    out, unknown = [], []
    for raw in paths:
        p = Path(raw) if Path(raw).is_absolute() else root / raw
        try:
            p = guard.check(p)
        except PermissionError:
            unknown.append({"path": str(raw), "reason": "outside the project (isolation guard)"})
            continue
        relp = structural.rel(p, root)
        if p.is_file() or p.is_dir():
            out.append(relp)
        else:
            out.append(relp)   # deleted files still have importers worth checking
            unknown.append({"path": relp, "reason": "not present in the working tree (deleted or misspelled)"})
    return sorted(set(out)), unknown


def affected(project, paths=None, *, home=None, bundle_dir=None, depth=DEFAULT_DEPTH, limit=None, use_graph=True,
             force_update=False):
    start = time.perf_counter()
    root = project.root.resolve()
    source = "paths" if paths else "git-status"
    paths = list(paths) if paths else changed_files(root)
    changed, unknown = _normalize(project, paths)
    files, truncated_scan = structural.scan(root)
    if truncated_scan:
        unknown.append({"path": ".", "reason": f"scan stopped at {structural.MAX_FILES} files"})
    tests_all = [f for f in files if structural.is_runnable_test(f)]
    limit = limit or code_limit()

    # Directories expand to the code files inside them.
    seeds = []
    for c in changed:
        inside = [f for f in files if f.startswith(c.rstrip("/") + "/")]
        seeds += inside or [c]
    seeds = sorted(set(seeds))

    method, notice, graph_info, reach = "graph", None, None, {}
    if use_graph:
        try:
            from ..runtimes.graphify import Graphify, GraphifyError
            try:
                g = Graphify(project, home or project.home, bundle_dir)
                graph_info = g.ensure_graph(structural.fingerprint(root, files), force=force_update)
                got = g.affected(seeds, depth=depth)
                graph_info = {**graph_info, "nodes": got["nodes"], "edges": got["edges"]}
                reach = {f: (h["depth"], h["via"], h["relation"], h["location"]) for f, h in got["affected"].items()}
                unknown += [{"path": u, "reason": "UNKNOWN: no graph node for this path"} for u in got["unresolved"]
                            if u in files]
            except GraphifyError as exc:
                method, notice = "structural", f"{FALLBACK_NOTICE} ({exc})"
        except ImportError as exc:   # pragma: no cover - packaging error
            method, notice = "structural", f"{FALLBACK_NOTICE} ({exc})"
    else:
        method, notice = "structural", FALLBACK_NOTICE
    if method == "structural":
        edges = structural.import_graph(root, files)
        reach = {f: (d, via, "imports", f) for f, (d, via) in structural.reverse_reach(edges, seeds, depth).items()}
        langs = sorted({f.rsplit(".", 1)[-1] for f in seeds if "." in f
                        and "." + f.rsplit(".", 1)[-1].lower() not in structural.EDGE_LANGS})
        if langs:
            unknown.append({"path": ", ".join(f".{x}" for x in langs),
                            "reason": "UNKNOWN: imports of these languages are not analysed without the graph"})

    ranked = sorted(reach.items(), key=lambda kv: (kv[1][0], kv[0]))
    code = [{"file": c, "reason": "changed", "depth": 0} for c in seeds if not structural.is_test(c)]
    code += [{"file": f, "reason": f"{rel} {via}", "depth": d, "location": loc}
             for f, (d, via, rel, loc) in ranked if not structural.is_test(f)]
    tests = [{"file": c, "reason": "changed test", "depth": 0} for c in seeds if structural.is_runnable_test(c)]
    tests += [{"file": f, "reason": f"{rel} {via}", "depth": d} for f, (d, via, rel, _loc) in ranked
              if structural.is_runnable_test(f)]
    have = {t["file"] for t in tests}
    named = structural.tests_named_after([c["file"] for c in code], tests_all)
    tests += [{"file": t, "reason": f"named after {f}", "depth": None} for t, f in sorted(named.items())
              if t not in have]

    return {
        "method": method,
        "notice": notice,
        "source": source,
        "changed": changed,
        "files": code[:limit],
        "tests": tests[:limit],
        "omitted": {"files": max(0, len(code) - limit), "tests": max(0, len(tests) - limit)},
        "limit": limit,
        "depth": depth,
        "unknown": unknown,
        "graph": graph_info,
        "scanned_files": len(files),
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
    }
