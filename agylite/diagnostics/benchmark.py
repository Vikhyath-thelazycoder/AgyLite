"""`agylite benchmark --baseline`: measure what installed host plugins load before any task.

Replaces the hard-coded tables of v1.0.1's scripts/benchmark (finding B-1) with measurements.
Method (docs/audit/13_TOKEN_CONTEXT_AUDIT.md): sum `name + description` frontmatter bytes of every
skill, agent and command each installed Claude Code plugin exposes. Tokens are ESTIMATES (bytes / 4).
"""
import json
import re
from pathlib import Path

FIELD = re.compile(r"^([A-Za-z_-]+):\s*(.*)$")


def frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    fields, key = {}, None
    for line in text[3:end if end > 0 else 0].splitlines():
        m = FIELD.match(line)
        if m:
            key = m.group(1)
            fields[key] = m.group(2)
        elif key and line[:1] in (" ", "\t"):
            fields[key] += " " + line.strip()
    return fields


def _skill_files(plugin_dir: Path):
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    listed = None
    if manifest.is_file():
        try:
            listed = json.loads(manifest.read_text(encoding="utf-8")).get("skills")
        except ValueError:
            listed = None
    if isinstance(listed, str):
        listed = [listed]
    if not isinstance(listed, list):
        listed = ["skills"]
    files = []
    for entry in listed:
        base = plugin_dir / entry
        # An entry is either one skill directory or a directory of skill directories (e.g. "./skills/").
        files += [base / "SKILL.md"] if (base / "SKILL.md").is_file() else sorted(base.glob("*/SKILL.md"))
    return files


def measure_plugin(plugin_dir: Path):
    """Return {kind: (count, bytes)} for skills, agents and commands of one installed plugin."""
    groups = {
        "skills": _skill_files(plugin_dir),
        "agents": sorted((plugin_dir / "agents").glob("*.md")),
        "commands": sorted((plugin_dir / "commands").glob("**/*.md")),
    }
    result = {}
    for kind, files in groups.items():
        total = 0
        for f in files:
            fm = frontmatter(f.read_text(encoding="utf-8", errors="ignore"))
            text = (fm.get("name", "") + " " + fm.get("description", "")).strip()
            if not text:
                text = f.parent.name if kind == "skills" else f.stem
            total += len(text.encode("utf-8"))
        result[kind] = (len(files), total)
    return result


def installed_plugins(plugins_root: Path):
    registry = plugins_root / "installed_plugins.json"
    if not registry.is_file():
        return []
    data = json.loads(registry.read_text(encoding="utf-8"))
    out = []
    for name, installs in sorted(data.get("plugins", {}).items()):
        for inst in installs:
            path = Path(inst.get("installPath", ""))
            if path.is_dir():
                out.append((name, inst.get("version", "?"), path))
    return out


def run(plugins_root: Path | None = None) -> int:
    plugins_root = plugins_root or Path.home() / ".claude" / "plugins"
    print("📊 Agylite — Benchmark (old-model baseline)")
    print("Token figures are ESTIMATES (bytes / 4); bytes are measured.\n")
    plugins = installed_plugins(plugins_root)
    if not plugins:
        print(f"No installed plugins found under {plugins_root}.")
        return 0
    print("| Plugin | Version | Skills | Agents | Commands | Bytes | Est. tokens |")
    print("|---|---|---:|---:|---:|---:|---:|")
    grand = 0
    for name, version, path in plugins:
        m = measure_plugin(path)
        total = sum(b for _, b in m.values())
        grand += total
        print(f"| {name} | {version} | {m['skills'][0]} | {m['agents'][0]} | {m['commands'][0]} | {total:,} | {total // 4:,} |")
    print(f"\nAlways-loaded descriptions across installed plugins: {grand:,} bytes ≈ {grand // 4:,} tokens (estimate).")
    print("Not included: MCP tool schemas and hook output, which add to this cost.")
    return 0


# ── OLD vs NEW (P25, spec §92–93): measured per routing scenario ─────────────────────────────────────────────────
NAME = "agylite"


def _pct(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else 0.0


def compare(plugins_root: Path | None = None, out: Path | None = None, repeats=20) -> dict:
    """OLD = what installed host plugins load (all descriptions every turn + the full skill files a task triggers);
    NEW = this OS (its own descriptions + L0 bootstrap every turn + routed L1 cards + budgeted L2 sections).
    Bytes are measured; tokens are bytes/4 estimates."""
    import time

    import yaml

    from ..context import levels
    from ..context.budget import load_budgets
    from ..context.loader import ContextLoader
    from ..paths import current_bundle, repo_root
    from ..project.identity import detect
    from ..routing import ProjectFacts, Router, capability_ids, context_order
    root = repo_root()
    plugins_root = plugins_root or Path.home() / ".claude" / "plugins"
    seen, others = set(), []
    for n, v, p in installed_plugins(plugins_root):   # one install per plugin (a second scope is not counted twice)
        if not n.startswith(NAME + "@") and n not in seen:
            seen.add(n)
            others.append((n, v, p))
    old_always = sum(sum(b for _, b in measure_plugin(p).values()) for _n, _v, p in others)
    own = measure_plugin(root)
    budgets, bundle, project = load_budgets(), current_bundle(), detect(root)
    t0 = time.perf_counter()
    l0 = levels.bootstrap(project=project, session_id="bench", host="cli", bundle_dir=bundle, budgets=budgets)
    l0_ms = (time.perf_counter() - t0) * 1000
    new_always = sum(b for _, b in own.values()) + len(l0["text"].encode())
    doc = yaml.safe_load((root / "tests" / "routing" / "scenarios.yaml").read_text(encoding="utf-8"))
    alias = doc.get("aliases", {})
    router = Router()
    from ..context import prompt_hook
    rows, route_ms, ctx_ms, hook_bytes = [], [], [], []
    for sc in doc["scenarios"]:
        facts = ProjectFacts(stage=sc.get("stage", "unknown"))
        for _ in range(repeats):
            r = router.route(sc["request"], project=facts, requested=sc.get("capabilities", ()))
            route_ms.append(r["duration_ms"])
        ids = set(capability_ids(r))
        expect = [alias.get(e, e) for e in sc.get("expect", [])]
        forbid = sc.get("forbid", [])
        ok = all(e in ids for e in expect) and not any(
            (c.startswith(f) if f.endswith("/") else c == f) and c not in expect for c in ids for f in forbid)
        caps = context_order(r)
        hook = prompt_hook.compose(sc["request"], project, budgets)   # what each message adds (MP1 F15)
        if hook is not None:
            hook_bytes.append(len(hook["text"].encode()))
        old_task = new_task = 0
        if bundle is not None and caps:
            t0 = time.perf_counter()
            loader = ContextLoader(project, None, bundle, use_cache=False)
            l1 = levels.domain_context(loader, caps, budgets)
            l2 = levels.capability_context(loader, caps, budgets, query=sc["request"])
            ctx_ms.append((time.perf_counter() - t0) * 1000)
            new_task = len(l1["text"].encode()) + len(l2["text"].encode())
            old_task = sum(e["bytes"] for e in loader.log if e["level"] == "L2")
        rows.append({"id": sc["id"], "request": sc["request"], "capabilities": caps, "routing_ok": ok,
                     "old_bytes": old_always + old_task, "new_bytes": new_always + new_task,
                     "old_task": old_task, "new_task": new_task})
    result = {"old_always": old_always, "new_always": new_always, "own": own, "l0_bytes": len(l0["text"].encode()),
              "plugins": [(n, v) for n, v, _p in others], "rows": rows,
              "routing_accuracy": (sum(r["routing_ok"] for r in rows), len(rows)),
              "route_p50": _pct(route_ms, .5), "route_p95": _pct(route_ms, .95), "l0_ms": l0_ms,
              "context_p50": _pct(ctx_ms, .5), "context_p95": _pct(ctx_ms, .95), "bundle": bundle.name if bundle else None,
              "hook_p50": _pct(hook_bytes, .5), "hook_max": max(hook_bytes, default=0)}
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(result), encoding="utf-8")
    return result


def _t(b):
    return f"{b:,} B ≈ {b // 4:,}"


def render(r) -> str:
    ok, total = r["routing_accuracy"]
    lines = [
        "# Benchmarks — OLD (installed plugins) vs NEW (Agylite)", "",
        "Generated by `agylite benchmark --compare`. Bytes are **measured**; tokens are **estimates** (bytes ÷ 4, "
        "no model tokenizer). OLD = every installed plugin's skill/agent/command descriptions on every turn + the "
        "full skill files a task triggers. NEW = this OS's own descriptions + the L0 bootstrap on every turn + routed "
        "L1 cards + the whole primary skill (IMPLEMENTATION_PLAN §2.1, Plan B) for the same task. MCP tool schemas and hook output (OLD only) are not "
        "counted, so OLD is a lower bound.", "",
        f"Bundle: `{r['bundle']}` · OLD plugins measured: " + (", ".join(f"{n} {v}" for n, v in r["plugins"]) or "none"),
        "", "## Every turn (before any task)", "",
        "| | Bytes ≈ est. tokens |", "|---|---:|",
        f"| OLD: installed plugin descriptions | {_t(r['old_always'])} |",
        f"| NEW: own descriptions ({sum(c for c, _ in r['own'].values())} items) + L0 bootstrap ({r['l0_bytes']:,} B) | {_t(r['new_always'])} |",
        "", f"Per message: L0 bootstrap ≈ {r['l0_bytes'] // 4:,} tokens (once per session) · prompt hook p50 ≈ "
        f"{int(r['hook_p50']) // 4:,} · max ≈ {r['hook_max'] // 4:,} tokens (route line, `agylite skill load` line, L1 cards; "
        "budget 800). Per task: the whole primary skill of the top capability (NEW L1+L2 below).",
        "", "## Per task (spec scenarios)", "",
        "| Scenario | Routed capabilities | Routing | OLD task files | NEW L1+L2 | OLD total | NEW total |",
        "|---|---|:---:|---:|---:|---:|---:|"]
    for row in r["rows"]:
        lines.append(f"| {row['id']} | {', '.join(row['capabilities']) or '—'} | {'✔' if row['routing_ok'] else '✗'} | "
                     f"{row['old_task']:,} | {row['new_task']:,} | {row['old_bytes'] // 4:,} | {row['new_bytes'] // 4:,} |")
    tot_old = sum(x["old_bytes"] for x in r["rows"])
    tot_new = sum(x["new_bytes"] for x in r["rows"])
    change = (1 - tot_new / tot_old) * 100 if tot_old else 0
    lines += ["", f"Totals over {total} scenarios: OLD ≈ {tot_old // 4:,} tokens · NEW ≈ {tot_new // 4:,} tokens "
                  f"({abs(change):.0f}% {'less' if change >= 0 else 'more'})" if tot_old else "", "",
              "## Routing accuracy and speed", "",
              f"- Routing accuracy on the spec scenarios: **{ok}/{total}** (expected capabilities present, forbidden absent).",
              f"- Route latency: p50 {r['route_p50']:.2f} ms · p95 {r['route_p95']:.2f} ms (deterministic, no model call).",
              f"- L0 bootstrap: {r['l0_ms']:.0f} ms. L1+L2 context assembly: p50 {r['context_p50']:.0f} ms · p95 {r['context_p95']:.0f} ms (no session cache).",
              "", "OLD has no routing step: the host model chooses among all descriptions itself, so its accuracy and "
              "latency depend on the model and are not measured here."]
    return "\n".join(lines) + "\n"
