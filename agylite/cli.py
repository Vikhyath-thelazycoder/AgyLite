"""`agylite` command line: the single entry point every host adapter calls (D-009)."""
import argparse
import sys
from pathlib import Path

from . import __version__
from .paths import repo_root

# Subcommands planned in docs/plan/FILE_LEVEL_PLAN.md and the phase that delivers each.
PLANNED = {}


def _root(args) -> Path:
    return Path(args.root).resolve() if args.root else repo_root()


def _doctor(args):
    from .diagnostics.doctor import run
    return run(_root(args))


def _validate(args):
    from .diagnostics.validate import run
    return run(_root(args), online=args.online, unittests=not args.no_unittest)


def _quality(args):
    """MP2: `benchmark --quality --tier 0|1`."""
    import json

    from .benchmark.quality import harness, tier0, tier1
    if args.report:
        rep = json.loads((Path(args.report) / "report.json").read_text(encoding="utf-8"))
        print(tier1.render(rep), end="")
        return 0
    if args.tier == 0:
        base = json.loads(Path(args.compare_to).read_text(encoding="utf-8")) if args.compare_to else None
        rep = tier0.run(bundle=Path(args.bundle) if args.bundle else None, baseline=base)
        print(tier0.render(rep), end="")
        if args.baseline_save:
            tier0.save_baseline(rep, Path(args.baseline_save))
            print(f"baseline saved: {args.baseline_save}")
        return 0 if rep["ok"] else 1
    if not args.suite:
        from .benchmark.quality import suites
        print("agylite benchmark --quality --tier 1: name --suite (" + ", ".join(suites.names()) + ")", file=sys.stderr)
        return 2
    code = 0
    for suite in args.suite.split(","):
        try:
            rep = tier1.run(suite, arms=tuple(args.arms.split(",")), runs=args.runs,
                            tasks=args.tasks.split(",") if args.tasks else None, dry_run=args.dry_run,
                            yes_spend=args.yes_spend, max_sessions=args.max_sessions, model=args.model,
                            judge_model=args.judge_model, python=sys.executable,
                            resume=Path(args.resume).expanduser() if args.resume else None,
                            reuse_from=Path(args.reuse_from).expanduser() if args.reuse_from else None)
        except harness.SpendRefused as exc:
            print(f"agylite benchmark: {exc}", file=sys.stderr)
            return 3
        if rep.get("stopped"):   # a usage limit: the rest of the suites wait for the reset too
            print(tier1.render(rep), end="")
            rest = args.suite.split(",")[args.suite.split(",").index(suite) + 1:]
            if rest:
                print(f"not started: {', '.join(rest)}")
            return 4
        if not args.dry_run:
            print(tier1.render(rep), end="")
            print(f"report: {rep['run_dir']}/report.json")
            code |= 0 if rep["verdict"] == "same" else 1
    return code


def _benchmark(args):
    if args.quality:
        return _quality(args)
    from .diagnostics.benchmark import compare, render, run
    root = Path(args.plugins_root).expanduser() if args.plugins_root else None
    if not args.compare:
        return run(plugins_root=root)
    print(render(compare(root, Path(args.out) if args.out else None)), end="")
    return 0


def _bundle(args):
    import json

    from .bundle import build as bundle_build
    from .paths import agylite_home
    home = agylite_home()
    if args.bundle_cmd == "fetch":
        from .bundle.fetch import fetch
        fetch(Path(args.staging) if args.staging else home / "staging" / "upstream")
        return 0
    if args.bundle_cmd == "build":
        try:
            info = bundle_build.build(home, Path(args.staging) if args.staging else None,
                                      activate_bundle=not args.no_activate, self_test=args.self_test)
        except bundle_build.BuildError as exc:
            print(f"bundle build failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({k: info[k] for k in ("bundle_id", "status", "counts", "error_count")}, indent=1))
        if info["status"] != "known-good":
            for err in info["errors"][:20]:
                print(f"  ✗ {err}", file=sys.stderr)
            return 1
        return 0
    if args.bundle_cmd == "verify":
        target = home / "bundles" / (args.bundle_id or "current")
        if not target.exists():
            print(f"no bundle at {target}", file=sys.stderr)
            return 1
        problems = bundle_build.verify(target.resolve())
        for p in problems[:50]:
            print(f"  ✗ {p}")
        print(f"bundle {target.resolve().name}: {'intact' if not problems else f'{len(problems)} problems'}")
        return 1 if problems else 0
    if args.bundle_cmd == "list":
        for b in bundle_build.list_bundles(home):
            print(f"{'*' if b['current'] else ' '} {b['bundle_id']}  {b['status']:10}  {b['created']}")
        return 0
    return 2


def _registry(args):
    import yaml

    from .paths import bundles_dir, current_bundle
    from .registry import generate, loader
    bundle = (bundles_dir() / args.bundle_id).resolve() if getattr(args, "bundle_id", None) else current_bundle()
    if args.registry_cmd == "check":
        problems = generate.check(bundle_dir=None if args.no_bundle else bundle)
        for p in problems[:50]:
            print(f"  ✗ {p}")
        where = f" + bundle {bundle.name}" if bundle and not args.no_bundle else ""
        print(f"registry ({len(loader.load_cards())} capabilities{where}): "
              f"{'valid' if not problems else f'{len(problems)} problems'}")
        return 1 if problems else 0
    if args.registry_cmd == "cards":
        changed = generate.write_card_docs()
        print(f"CARD.md rendered: {len(changed)} changed")
        return 0
    if args.registry_cmd == "build":
        if bundle is None or not (bundle / "provenance.json").is_file():
            print("no built bundle (run `agylite bundle build` first)", file=sys.stderr)
            return 1
        reg = generate.write_registry(bundle)
        print(f"registry.yaml written for bundle {bundle.name}: {len(reg['capabilities'])} capabilities")
        return 0
    reg = (generate.load_registry(bundle) if bundle else None) or generate.plan_registry()
    if args.registry_cmd == "list":
        for cid, e in reg["capabilities"].items():
            mode = e["activation_conditions"]["mode"]
            print(f"{cid:36} {mode:14} p{e['priority']:<3} {e['token_cost_estimate']['bundled_files']:>4} files"
                  f"{'' if e['enabled'] else '  DISABLED'}")
        print(f"source: {reg['source']}{' ' + reg['bundle_id'] if reg.get('bundle_id') else ''}")
        return 0
    if args.registry_cmd == "show":
        entry = reg["capabilities"].get(args.capability)
        if entry is None:
            print(f"unknown capability {args.capability}", file=sys.stderr)
            return 1
        if not args.paths:
            entry = dict(entry, source_paths={r: f"{len(p)} files" for r, p in entry["source_paths"].items()})
        print(yaml.safe_dump({args.capability: entry}, sort_keys=False, allow_unicode=True, width=120), end="")
        return 0
    return 2


def _project_ref(args):
    from .project.identity import detect
    return detect(Path(args.project) if getattr(args, "project", None) else None)


def _facts(project, stage=None, stack=None):
    """ProjectFacts from flags, else recorded state, else detection (spec §15 project identification + state load)."""
    from .project import lifecycle, plan_index, state as pstate
    from .routing import ProjectFacts
    st = pstate.load_state(project)
    index = plan_index.load_index(project, st) if st else None
    return ProjectFacts(stage=stage or lifecycle.detect_stage(project.root, st), project_id=project.project_id,
                        phase=(index or {}).get("current_phase"),
                        stack=tuple(stack if stack is not None else (st or {}).get("stack")
                                    or lifecycle.detect_stack(project.root)))


def _emit_route(project, result, session_id=None):
    """Spec §30: DOMAIN_SELECTED then CAPABILITIES_SELECTED for one routing decision."""
    from .events import emit
    caps = [c["id"] for c in result["capabilities"]]
    emit(project, "DOMAIN_SELECTED", session_id=session_id, duration_ms=result["duration_ms"],
         details={"domains": result["domains"], "change_type": result["change_type"], "method": result["method"],
                  "confidence": result["confidence"]})
    emit(project, "CAPABILITIES_SELECTED", session_id=session_id, capabilities=caps,
         details={"dependencies": [d["id"] for d in result["dependencies"]], "fallbacks": result["fallbacks"],
                  "browser": result["browser"], "suppressed": len(result["suppressed"]), "rules": result["rules"]})
    if result.get("unmatched"):
        emit(project, "ROUTE_UNMATCHED", session_id=session_id, details=_unmatched_details(result["request"]))


def _unmatched_details(request, keywords=True):
    """MP1 F4: what MP6 needs to group requests nobody routes — content words, a hash and the length, never the text."""
    import hashlib

    from .routing.fallback_bm25 import tokenize
    d = {"request_sha256": hashlib.sha256(request.encode()).hexdigest()[:16], "length": len(request)}
    if keywords:
        d["keywords"] = sorted(set(tokenize(request)))[:12]
    return d


def _route(args):
    import json

    from .routing import Router, RoutingError
    stage = "new" if args.new else "existing" if args.existing else None
    project = _project_ref(args)
    try:
        result = Router().route(" ".join(args.request), paths=args.paths or (), requested=args.capability or (),
                                project=_facts(project, stage, args.stack))
    except RoutingError as exc:
        print(f"agylite route: {exc}", file=sys.stderr)
        return 2
    _emit_route(project, result, _session_id(args))
    if args.brief and result.get("unmatched"):
        print(f"{result['change_type']} · UNMATCHED · no capability fits; using principles only")
    elif args.brief:
        caps = ", ".join(c["id"] for c in result["capabilities"]) or "—"
        deps = ", ".join(d["id"] for d in result["dependencies"])
        print(f"{result['change_type']} · {result['confidence']} ({result['method']}) · {caps}"
              + (f" + deps: {deps}" if deps else ""))
    else:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


def _event_summary(d):
    """A few words saying what an event was about (`events list`), from its details."""
    if d.get("change") == "task_added":
        return f"task {d.get('task')} added to {d.get('phase')}"
    if d.get("change") == "question_answered":
        return f"answered {d.get('question')}"
    if d.get("change") == "decision_recorded":
        return f"decision {d.get('decision')}"
    if d.get("change") == "project_initialised":
        return "project initialised"
    if d.get("item") and d.get("to"):
        return f"{d['item']} {d.get('from') or '?'} → {d['to']}" + (f" ({d['reason']})" if d.get("reason") else "")
    if d.get("change"):
        return str(d["change"])
    return ""


def _session_id(args, create=False):
    import os
    import secrets
    from datetime import datetime, timezone
    sid = getattr(args, "session", None) or os.environ.get("AGYLITE_SESSION_ID")
    if not sid and create:
        sid = f"s-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(3)}"
    return sid


def _hook(args):
    """MP1 F15: print the context to inject for the prompt on stdin; never fail, never block (exit 0 always)."""
    from .context import prompt_hook
    try:
        out = prompt_hook.run(sys.stdin.read(), args.host)
    except BaseException:   # noqa: BLE001 — a hook may never break the host's prompt
        out = ""
    if out:
        sys.stdout.write(out)
    return 0


def _skill(args):
    """Plan B (IMPLEMENTATION_PLAN §2.1): print one whole skill with its folder and file list, or list skill ids."""
    from .context import levels
    from .context.loader import ContextError, ContextLoader
    from .paths import current_bundle
    project = _project_ref(args)
    loader = ContextLoader(project, _session_id(args), current_bundle(), use_cache=not args.no_cache)
    try:
        if args.skill_cmd == "list":
            for cid, entries in sorted(loader.index["capabilities"].items()):
                if args.capability and cid != args.capability:
                    continue
                for e in entries:
                    if e["kind"] == "skill":
                        print(f"{levels.skill_id(e):48} {cid:34} ~{e['tokens']} tokens")
            return 0
        entry = levels.find_skill(loader, args.skill_id or "")
        if entry is None:
            print(f"agylite skill: no bundled skill {args.skill_id!r}; list them with `agylite skill list`, or find one "
                  f"in every upstream with `agylite skills search \"<words>\"`", file=sys.stderr)
            return 2
        text, _ = levels.whole_skill(loader, entry, level="L2")
    except ContextError as exc:
        print(f"agylite skill: {exc}", file=sys.stderr)
        return 1
    loader.finish(active_capabilities=[next((c for c, es in loader.index["capabilities"].items()
                                              if any(x["path"] == entry["path"] for x in es)), "")])
    sys.stdout.write(text)
    return 0


def _skills(args):
    """Plan B breadth: `skills search` ranks the catalog of every pinned upstream; `skills get` fetches one folder."""
    import json

    from . import catalog
    from .paths import agylite_home, current_bundle
    bundle = current_bundle()
    try:
        cat = catalog.load(bundle) if bundle else None
    except FileNotFoundError as exc:
        print(f"agylite skills: {exc}", file=sys.stderr)
        return 1
    if cat is None:
        print("agylite skills: no bundle installed (scripts/install)", file=sys.stderr)
        return 1
    if args.skills_cmd == "search":
        res = catalog.search(cat, " ".join(args.words), args.n)
        print(json.dumps(res, indent=1) if args.json else catalog.render(res), end="" if not args.json else "\n")
        return 0
    from .paths import repo_root
    licenses = json.loads((repo_root() / "third_party" / "licenses.json").read_text(encoding="utf-8"))
    try:
        dest = catalog.get(agylite_home(), cat, args.words[0], licenses)
    except (KeyError, PermissionError) as exc:
        print(f"agylite skills: {exc.args[0]}", file=sys.stderr)
        return 2
    print(f"fetched {args.words[0]} → {dest}\nRead {dest / 'SKILL.md'} and follow it like any skill; its files are in that folder.")
    return 0


def _bootstrap(args):
    import json

    from .context.budget import load_budgets
    from .context.levels import bootstrap
    from .paths import current_bundle
    from .project import lifecycle, plan_index, state as pstate
    from .events import emit
    project = _project_ref(args)
    sid = _session_id(args, create=True)
    record = lifecycle.start_session(project, sid, args.host)
    from .adapters import record_runtime
    record_runtime(args.host, project.project_id)   # host really ran the OS (P19–P22 RUNTIME_VERIFIED evidence)
    if record.get("new"):
        emit(project, "SESSION_STARTED", session_id=sid, host=args.host, details={"root": str(project.root)})
    emit(project, "PROJECT_DETECTED", session_id=sid, host=args.host,
         details={"name": project.name, "origin": project.origin})
    st = pstate.load_state(project)
    index = plan_index.load_index(project, st) if st else None
    phase = next((f"{p['phase_id']} {p['phase_name']} ({p['status']})" for p in (index or {}).get("phases", [])
                  if p["phase_id"] == (index or {}).get("current_phase")), None)
    lines = pstate.summary_lines(st, index) if st else ["no project state yet (`agylite project init`)"]
    pointer = (f"{index['plan_path']}#{index['current_phase']} · index .agylite/plan-index.yaml" if index else None)
    result = bootstrap(project=project, session_id=sid, host=args.host, bundle_dir=current_bundle(),
                       budgets=load_budgets(), stage=lifecycle.detect_stage(project.root, st), phase=phase,
                       state_lines=lines, plan_pointer=pointer)
    print(json.dumps(result, indent=1) if args.json else result["text"], end="" if not args.json else "\n")
    return 0


def _context(args):
    import json

    from .context import levels
    from .context.budget import load_budgets
    from .context.loader import ContextError, ContextLoader
    from .paths import current_bundle
    from .project.identity import detect
    from .registry.loader import load_cards
    budgets = load_budgets()
    caps, query = list(args.capability), args.request
    if args.route:
        from .routing import Router, context_order
        route = Router().route(args.route, project=_facts(_project_ref(args)))
        _emit_route(_project_ref(args), route, _session_id(args))
        caps = caps or context_order(route)   # the whole-skill capabilities first (Plan B)
        query = query or args.route
        args.whole = args.whole or max(len(route.get("whole_skills") or []), 1)
    if not query and not args.file:
        print("note: no --request given; files ranked by sources_priority only", file=sys.stderr)
    cards = load_cards()
    unknown = [c for c in caps if c not in cards]
    if unknown:
        print(f"agylite context: unknown capability {unknown[0]}", file=sys.stderr)
        return 2
    level = 3 if args.file else args.level
    if level == 3 and not args.file:
        print("agylite context: level 3 is explicit only; pass --file <bundle path> (spec §16)", file=sys.stderr)
        return 2
    if not caps and not args.file:
        print("agylite context: name capabilities, --route \"<request>\", or --file", file=sys.stderr)
        return 2
    project = detect(Path(args.project) if args.project else None)
    loader = ContextLoader(project, _session_id(args), current_bundle(), use_cache=not args.no_cache)
    out = []
    try:
        if args.file:
            out.append(levels.deep_reference(loader, args.file, budgets, sections=args.section, query=query))
        else:
            out.append(levels.domain_context(loader, caps, budgets))
            from .project import decisions
            relevant = decisions.relevant(project, caps)
            if relevant:   # spec §50–52: recorded decisions, only the kinds these capabilities need
                text = "## Project decisions (relevant)\n" + "".join(
                    f"- {d['decision_id']} [{d['kind']}] {d['topic']}: {d['decision']}\n" for d in relevant)
                out.append({"level": "L1", "text": text, "est_tokens": -(-len(text.encode()) // 4)})
            if level >= 2:
                out.append(levels.capability_context(loader, caps, budgets, query=query, whole=args.whole or 1))
    except ContextError as exc:
        print(f"agylite context: {exc}", file=sys.stderr)
        return 1
    loader.finish(active_capabilities=caps or None)
    if args.json:
        print(json.dumps({"levels": out, "load_log": loader.log, "session_id": loader.session_id,
                          "project_id": project.project_id}, indent=1))
    else:
        print("\n".join(o["text"] for o in out), end="")
        total = sum(o["est_tokens"] for o in out)
        hits = sum(1 for e in loader.log if e["cache"] == "hit")
        print(f"\n— context: ≈{total} est. tokens · {len(loader.log)} files ({hits} cached) · "
              f"levels {', '.join(o['level'] for o in out)}")
    return 0


def _print(data, as_json):
    import json

    import yaml
    if as_json:
        print(json.dumps(data, indent=1, ensure_ascii=False, default=str))
    else:
        print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120), end="")


def _project_cmd(args):
    import shutil

    from .project import lifecycle, plan_index, questions, reconcile, state as pstate
    from .project.state import read_yaml, write_yaml
    project = _project_ref(args)
    cmd = args.project_cmd
    if cmd == "init":
        if pstate.load_state(project) and not args.force:
            print(f"project already initialised ({pstate.state_path(project)}); --force to reset state", file=sys.stderr)
            return 1
        stage = "new" if args.new else "existing" if args.existing else lifecycle.detect_stage(project.root)
        stack = args.stack if args.stack is not None else lifecycle.detect_stack(project.root)
        st = pstate.new_state(project, stage, stack)
        written = []
        if args.docs:
            from datetime import date
            docs = project.root / "docs"
            docs.mkdir(exist_ok=True)
            for tpl in sorted((repo_root() / "templates" / "project-docs").glob("*.md")):
                dest = docs / tpl.name
                if dest.exists():
                    continue
                dest.write_text(tpl.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", project.name)
                                .replace("{{DATE}}", date.today().isoformat()), encoding="utf-8")
                written.append(f"docs/{tpl.name}")
        pstate.save_state(project, st)
        reconcile.register(project)
        index = plan_index.load_index(project, st)
        if index:
            pstate.update_state(project, lambda s: s["plan"].__setitem__("current_phase", index.get("current_phase")))
        from .events import emit
        emit(project, "PROJECT_DETECTED", details={"name": project.name, "origin": project.origin, "stage": stage})
        emit(project, "STATE_UPDATED", details={"change": "project_initialised", "stack": stack, "docs": written})
        print(f"initialised {project.name} ({project.project_id}) as {stage} project; stack: {', '.join(stack) or '—'}")
        for w in written:
            print(f"  + {w}")
        return 0
    if cmd == "status":
        st = pstate.require_state(project)
        index = plan_index.load_index(project, st)
        _print({"project": st["project"], "root": str(project.root), "stack": st.get("stack"),
                "summary": pstate.summary_lines(st, index)}, args.json)
        return 0
    if cmd == "questions":
        st = pstate.load_state(project) or {}
        stage = (st.get("project") or {}).get("stage") or lifecycle.detect_stage(project.root)
        qs, skipped = questions.next_questions(questions.load_bank(), " ".join(args.request), stage=stage,
                                               answers=st.get("answers"), stack=st.get("stack") or
                                               lifecycle.detect_stack(project.root))
        blocking = [q["id"] for q in qs if q["priority"] == "BLOCKING"]
        if st and blocking:   # recorded: `plan set-status <task> IN_PROGRESS` refuses until they are answered
            pstate.update_state(project, lambda s: s.__setitem__(
                "pending_questions", sorted(set(s.get("pending_questions") or []) | set(blocking))))
        _print({"ask": qs, "not_asked": skipped,
                **({"answer_with": "agylite project answer <id> \"<answer>\""} if qs else {})}, args.json)
        return 0
    if cmd == "answer":
        bank = {q["id"] for q in questions.load_bank().get("questions") or []}
        if args.question not in bank:
            print(f"unknown question {args.question}", file=sys.stderr)
            return 2
        def record(s):
            s["answers"][args.question] = " ".join(args.answer)
            s["pending_questions"] = [q for q in s.get("pending_questions") or [] if q != args.question]
        pstate.update_state(project, record)
        from .events import emit
        emit(project, "STATE_UPDATED", details={"change": "question_answered", "question": args.question})
        print(f"recorded {args.question}")
        return 0
    if cmd == "relink":
        old_dir = project.home / "projects" / args.old_id
        if not old_dir.is_dir():
            print(f"no machine-local data for project {args.old_id}", file=sys.stderr)
            return 1
        if old_dir == project.data_dir:
            print("project id unchanged; nothing to relink")
            return 0
        if project.data_dir.exists() and any(project.data_dir.iterdir()):
            print(f"{project.data_dir} already has data; refusing to merge two projects", file=sys.stderr)
            return 1
        if project.data_dir.exists():
            project.data_dir.rmdir()
        shutil.move(str(old_dir), str(project.data_dir))
        rec = read_yaml(project.data_dir / "project.yaml") or {}
        rec.update({"project_id": project.project_id, "root": str(project.root), "origin": project.origin})
        rec["aliases"] = sorted(set(rec.get("aliases") or []) | {args.old_id})
        write_yaml(project.data_dir / "project.yaml", rec)
        if pstate.load_state(project):
            pstate.update_state(project, lambda s: s["project"].__setitem__("project_id", project.project_id))
        print(f"relinked {args.old_id} → {project.project_id}")
        return 0
    return 2


def _state_cmd(args):
    from .project import plan_index, state as pstate
    project = _project_ref(args)
    st = pstate.require_state(project)
    index = plan_index.load_index(project, st)
    cur = next((p for p in (index or {}).get("phases", []) if p["phase_id"] == (index or {}).get("current_phase")), None)
    _print({"project": st["project"], "stack": st.get("stack"), "plan": st.get("plan"),
            "current_phase": {k: cur[k] for k in ("phase_id", "phase_name", "status", "active_tasks")} if cur else None,
            "answers": st.get("answers"), "pending_questions": st.get("pending_questions") or [],
            "verification": st.get("verification"),
            "summary": pstate.summary_lines(st, index)}, args.json)
    return 0


def _plan_cmd(args):
    from .project import plan_index, reconcile, state as pstate
    project = _project_ref(args)
    st = pstate.require_state(project)
    index = plan_index.load_index(project, st, rebuild=args.plan_cmd == "index" and args.rebuild)
    if index is None:
        print(f"no plan at {plan_index.plan_file(project, st)} (`agylite project init --docs` creates one)",
              file=sys.stderr)
        return 1
    cmd = args.plan_cmd
    if cmd == "index":
        if args.json:
            _print(index, True)
        else:
            for p in index["phases"]:
                mark = "*" if p["phase_id"] == index["current_phase"] else " "
                flags = ",".join(f for f in ("security", "design", "testing") if p[f"{f}_flags"]) or "—"
                print(f"{mark} {p['phase_id']:5} {p['status']:22} {p['phase_name']}  tasks {len(p['tasks'])}"
                      f"  active {', '.join(p['active_tasks']) or '—'}  flags {flags}")
        return 0
    if cmd == "show":
        print(plan_index.phase_section(project, st, index, args.phase), end="")
        return 0
    if cmd == "locate":
        best, ranking = reconcile.locate_phase(index, " ".join(args.request), args.paths or ())
        _print({"phase": best and {"phase_id": best["phase_id"], "phase_name": best["phase_name"]},
                "ranking": ranking[:5]}, args.json)
        return 0
    if cmd == "add-task":
        task, reopened = reconcile.add_task(project, st, index, args.phase, " ".join(args.title),
                                            capabilities=args.capability or (), depends=", ".join(args.depends or []) or None,
                                            acceptance=args.acceptance)
        plan_index.load_index(project, st, rebuild=True)
        print(f"{task['id']} added to {args.phase}" + (" (phase reopened)" if reopened else ""))
        return 0
    if cmd == "set-status":
        pending = [q for q in st.get("pending_questions") or [] if q not in (st.get("answers") or {})]
        if pending and args.status.upper() == "IN_PROGRESS" and not args.item.upper().startswith("P"):
            print(f"agylite plan: blocking requirements questions are unanswered: {', '.join(pending)}\n"
                  f"  answer each first: agylite project answer <id> \"<answer>\" "
                  f"(the questions: agylite project questions \"<request>\")", file=sys.stderr)
            return 3
        old = reconcile.set_status(project, st, index, args.item, args.status.upper(), args.evidence)
        plan_index.load_index(project, st, rebuild=True)
        print(f"{args.item}: already {old} (unchanged)" if old == args.status.upper()
              else f"{args.item}: {old} → {args.status.upper()}")
        return 0
    if cmd == "reconcile":
        from .routing import Router
        report = reconcile.reconcile(project, st, Router(), " ".join(args.request), args.paths or (), args.new_phase)
        report.pop("route", None) if report["status"] == "planned" else None
        _print(report, args.json)
        return 0 if report["status"] == "planned" else 3
    return 2


def _decide_cmd(args):
    from .project import decisions
    project = _project_ref(args)
    if args.decide_cmd == "add":
        entry = decisions.add(project, kind=args.kind, topic=args.topic, decision=args.decision, reason=args.reason,
                              alternatives=args.alternative or (), impact=args.impact or "",
                              supersedes=args.supersedes, tags=args.tag or ())
        print(f"{entry['decision_id']} recorded ({entry['kind']}: {entry['topic']})")
        return 0
    if args.decide_cmd == "list":
        rows = decisions.find(project, kind=args.kind, topic=args.topic, status=None if args.all else "ACTIVE")
        for d in rows:
            print(f"{d['decision_id']}  {d['status']:10} {d['kind']:14} {d['topic']}: {d['decision']}")
        return 0
    if args.decide_cmd == "show":
        match = [d for d in decisions.load(project)["decisions"] if d["decision_id"] == args.id]
        if not match:
            print(f"no decision {args.id}", file=sys.stderr)
            return 1
        _print(match[0], args.json)
        return 0
    return 2


def _events_cmd(args):
    import json

    from .events import emit, read
    from .events import rules_cel
    from .events.redact import redact
    from .paths import current_bundle
    project = _project_ref(args)
    if args.events_cmd == "list":
        rows = read(project, event=args.type, session_id=args.session, limit=args.tail)
        if args.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        else:
            for r in rows:
                caps = f" [{', '.join(r['capabilities'][:3])}{'…' if len(r['capabilities']) > 3 else ''}]" if r["capabilities"] else ""
                what = _event_summary(r.get("details") or {})
                print(f"{r['ts']}  {r['event']:28} {r['severity']:8} {r.get('session_id') or '-':22}{caps}"
                      + (f"  {what}" if what else ""))
        return 0
    rules_dir = rules_cel.rules_dir_for(current_bundle())
    if rules_dir is None:
        print("no bundled detection rules (install the bundle: scripts/install)", file=sys.stderr)
        return 1
    rules = rules_cel.load_rules(rules_dir)
    if args.events_cmd == "rules":
        failed, total = [], 0
        for rule in rules:
            for name, verdict, ok in rules_cel.run_embedded_tests(rule) if args.test else []:
                total += 1
                if not ok:
                    failed.append(f"{rule['id']}::{name} (expected {verdict})")
        print(f"{len(rules)} rules from {rules_dir}")
        if args.test:
            print(f"embedded tests: {total - len(failed)}/{total} pass")
            for f in failed:
                print(f"  ✗ {f}")
        return 1 if failed else 0
    # observe: Beacon-shaped tool events from a host adapter (stdin JSON object or JSON lines)
    raw = sys.stdin.read().strip()
    incoming = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines() if line.strip()]
    findings = []
    for event in incoming:
        sid = (event.get("session") or {}).get("id") or _session_id(args) or "unknown"
        event.setdefault("session", {})["id"] = sid
        buf = project.data_dir / "events" / "observed" / f"{sid}.jsonl"
        from .isolation import atomic, guard_for
        guard_for(project).check(buf, "write")
        history = [json.loads(line) for line in buf.read_text(encoding="utf-8").splitlines()] if buf.is_file() else []
        reported = {r["details"].get("rule") for r in read(project, event="RISK_DETECTED", session_id=sid)}
        for hit in rules_cel.detect(rules, history + [event]):
            if hit["id"] in reported:
                continue
            severity = hit["severity"] if hit["severity"] in ("low", "medium", "high", "critical") else "medium"
            emit(project, "RISK_DETECTED", session_id=sid, severity=severity,
                 details={"rule": hit["id"], "title": hit["title"], "reason": hit["reason"],
                          "action": (event.get("event") or {}).get("action")})
            findings.append(hit)
            reported.add(hit["id"])
        history = (history + [redact(event)])[-200:]
        atomic.write_text(buf, "".join(json.dumps(h, sort_keys=True) + "\n" for h in history))
    print(json.dumps({"findings": findings}, indent=1))
    return 0


def _runtime_cmd(args):
    from .paths import current_bundle, agylite_home
    from .runtimes import graphify
    home, bundle = agylite_home(), current_bundle()
    from .runtimes import unlazy
    if args.runtime_cmd == "status":
        from .runtimes import uiux
        from .runtimes import brag, seo
        from .runtimes import taste
        _print({"runtimes": [graphify.health(home, bundle), unlazy.health(home), uiux.health(bundle),
                             taste.health(bundle, home), seo.health(home, bundle), brag.health(home, bundle)]}, args.json)
        return 0
    if args.runtime_cmd == "unlazy-hook":
        before = unlazy.stop_hook_commands()
        try:
            p = unlazy.stop_hook(home, enable=args.enable)
        except unlazy.UnlazyError as exc:
            print(f"agylite runtime unlazy-hook: {exc}", file=sys.stderr)
            return 1
        print((p.stdout or p.stderr).strip())
        after = unlazy.stop_hook_commands()   # MP3 §3.2: say exactly what changed in the user's settings
        added, removed = [c for c in after if c not in before], [c for c in before if c not in after]
        print("~/.claude/settings.json: " + ("; ".join([f"added Stop hook `{c}`" for c in added] +
                                                       [f"removed Stop hook `{c}`" for c in removed]) or "unchanged"))
        return p.returncode
    if args.name == "brag":
        from .runtimes import brag
        try:
            _print(brag.install_music(home, bundle), args.json)
        except (brag.BragError, OSError) as exc:
            print(f"agylite runtime install: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.name == "seo":
        from .runtimes import seo
        extras = [e for e in ("browser", "reports") if getattr(args, e, False)]
        try:
            _print(seo.install(home, bundle, extras), args.json)
        except (seo.SEOError, OSError) as exc:
            print(f"agylite runtime install: {exc}", file=sys.stderr)
            return 1
        return 0
    src = graphify.source_dir(bundle)
    if src is None:
        print("agylite runtime: no active bundle with files/graphify (run `agylite bundle build`)", file=sys.stderr)
        return 1
    try:
        info = graphify.install(home, src)
    except (graphify.GraphifyError, OSError) as exc:
        print(f"agylite runtime install: {exc}", file=sys.stderr)
        return 1
    _print(info, args.json)
    return 0


def _codebase_cmd(args):
    from .codebase import affected
    from .paths import current_bundle
    from .runtimes.graphify import Graphify, GraphifyBlocked, GraphifyError
    project = _project_ref(args)
    if args.codebase_cmd == "affected":
        result = affected(project, args.paths, bundle_dir=current_bundle(), depth=args.depth,
                          use_graph=not args.structural, force_update=args.update)
        if args.json:
            _print(result, True)
            return 0
        if result["notice"]:
            print(f"! {result['notice']}")
        print(f"changed ({result['source']}): {', '.join(result['changed']) or '—'}")
        print(f"files ({result['method']}, ≤{result['limit']}):")
        for f in result["files"]:
            print(f"  {f['file']}  [{f['reason']}]")
        print("tests:")
        for t in result["tests"]:
            print(f"  {t['file']}  [{t['reason']}]")
        if any(result["omitted"].values()):
            print(f"omitted by the code-surface limit: {result['omitted']['files']} files, {result['omitted']['tests']} tests")
        for u in result["unknown"]:
            print(f"  ? {u['path']}: {u['reason']}")
        return 0
    try:
        g = Graphify(project, project.home, current_bundle())
        if args.codebase_cmd == "update":
            from .codebase import structural
            files, _ = structural.scan(project.root.resolve())
            _print(g.ensure_graph(structural.fingerprint(project.root.resolve(), files), force=args.force), args.json)
            return 0
        if not g.graph_json.is_file():
            print("agylite codebase: no graph yet; run `agylite codebase update`", file=sys.stderr)
            return 1
        p = g.passthrough(args.codebase_cmd, args.terms + (["--budget", str(args.budget)] if args.budget else []))
    except GraphifyBlocked as exc:
        print(f"agylite codebase: {exc}", file=sys.stderr)
        return 2
    except GraphifyError as exc:
        print(f"agylite codebase: {exc}", file=sys.stderr)
        return 1
    print(p.stdout, end="")
    if p.returncode:
        print(p.stderr, end="", file=sys.stderr)
    return p.returncode


def _gates_cmd(args):
    from .paths import agylite_home
    from .runtimes import unlazy
    project = _project_ref(args)
    extra = [*(["--jobs", str(args.jobs)] if args.jobs else []), *(["--timeout", str(args.timeout)] if args.timeout else [])]
    try:
        p = unlazy.gates(agylite_home(), args.mode, args.files, project.root, extra)
    except unlazy.UnlazyError as exc:
        print(f"agylite gates: {exc}", file=sys.stderr)
        return 2
    print(p.stdout, end="")
    print(p.stderr, end="", file=sys.stderr)
    return p.returncode


def _design_cmd(args):
    from .design import tokens
    from .paths import current_bundle
    from .runtimes import uiux
    project = _project_ref(args)
    if args.design_cmd == "taste":   # MP4 §1.3: Taste v2.1 scripts from the bundle, run in the project
        from .paths import agylite_home
        from .runtimes import taste
        if args.script == "status":
            _print(taste.health(current_bundle(), agylite_home()), args.json)
            return 0
        try:
            return taste.run(current_bundle(), agylite_home(), args.script, args.args, cwd=project.root).returncode
        except taste.TasteError as exc:
            print(f"agylite design taste: {exc}", file=sys.stderr)
            return 1
    if args.design_cmd == "check":
        result = tokens.check(project.root.resolve())
        if args.json:
            _print(result, True)
        else:
            for c in result["checks"]:
                print(f"{c['status']:4}  {c['check']:15} {c['count']:>3} (limit {c['limit']})  {', '.join(map(str, c['values']))}")
            print(f"design check: {result['status']}" + ("" if result["design_md"] else " · no DESIGN.md"))
        return 1 if result["status"] == "FAIL" else 0
    try:
        if args.design_cmd == "search":
            p = uiux.search(current_bundle(), " ".join(args.query), domain=args.domain, stack=args.stack,
                            max_results=args.max_results, as_json=args.json, cwd=project.root)
        else:
            p = uiux.design_system(current_bundle(), project, " ".join(args.query), project_name=args.project_name,
                                   persist=args.persist, page=args.page, force=args.force,
                                   dials={"variance": args.variance, "motion": args.motion, "density": args.density})
    except uiux.UIUXError as exc:
        print(f"agylite design: {exc}", file=sys.stderr)
        return 1
    print(p.stdout, end="")
    print(p.stderr, end="", file=sys.stderr)
    return p.returncode


def _verify_cmd(args):
    from .paths import current_bundle
    from .project import state as pstate
    from .verify import engine, evidence
    project = _project_ref(args)
    if getattr(args, "action", None) == "exception":   # records only; runs nothing (D-035)
        if not args.reason:
            print("agylite verify exception: --reason is required (why local verification is insufficient)",
                  file=sys.stderr)
            return 2
        try:
            entry = pstate.record_browser_exception(project, args.reason)
        except pstate.StateError as exc:
            print(f"agylite verify exception: {exc}", file=sys.stderr)
            return 1
        _print({"browser_exception": entry, "note": "recorded only; the user operates any browser, no screenshots "
                "enter model context"}, args.json)
        return 0
    kinds = ["test"] if args.command == "test" else (args.kind or None)
    if args.plan:
        impact, selected = engine.plan_for(project, args.paths, full=args.all, kinds=kinds,
                                           include_e2e=args.include_e2e, bundle_dir=current_bundle())
        _print(engine.describe(selected, impact), args.json)
        return 0
    try:
        record, rel, results = engine.verify(project, args.paths, full=args.all, kinds=kinds,
                                             include_e2e=args.include_e2e, task=args.task,
                                             bundle_dir=current_bundle(), timeout=args.timeout,
                                             session_id=_session_id(args))
    except evidence.EvidenceError as exc:
        print(f"agylite verify: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print({**record, "evidence": rel}, True)
    else:
        for r in results:
            n = " ".join(f"{k}={r[k]}" for k in ("passed", "failed", "skipped") if k in r)
            print(f"{r['result']:8} {r['kind']:9} {r['name']:12} exit {r['exit_code']:<3} {n}"
                  + (" (flaky)" if r.get("flaky") else ""))
            for d in r.get("diagnosis", [])[:6]:
                print(f"           {d}")
        print(f"verification: {record['result']} · evidence {rel}")
    return 0 if record["result"] == "PASSED" else 1


def _seo_cmd(args):
    from .paths import current_bundle, agylite_home
    from .runtimes import seo
    from .seo import authorization
    project = _project_ref(args)
    if args.seo_cmd == "authorize":
        try:
            entry = authorization.grant(project, site=args.site, task=args.task, reason=args.reason, hours=args.hours)
        except authorization.AuthorizationError as exc:
            print(f"agylite seo authorize: {exc}", file=sys.stderr)
            return 2
        _print(entry, args.json)
        return 0
    if args.seo_cmd == "evidence":
        try:
            rows = seo.capture_report(agylite_home(), current_bundle(), Path(args.run_dir))
        except seo.SEOError as exc:
            print(f"agylite seo evidence: {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print(rows, True)
        else:
            for r in rows:
                print(f"{r['url']}\n  presence claims: [{r['presence']['label']}] {r['presence']['why']}"
                      f"\n  absence claims:  [{r['absence']['label']}] {r['absence']['why']}")
        return 0
    rest = [a for a in args.args if a != "--"]
    try:
        cmd, action = seo.check_command(rest)
        if (cmd, action) in seo.LIVE_WRITE:
            site = rest[rest.index("--site") + 1] if "--site" in rest[:-1] else None
            authorization.require(project, args.authorization, action=action, site=site)
        print(f"[agylite] running beyondseo {cmd}… (network; results print when it finishes, Ctrl+C to stop)",
              file=sys.stderr, flush=True)
        p, out = seo.run(project, agylite_home(), current_bundle(), rest)
    except (seo.SEOError, authorization.AuthorizationError) as exc:
        print(f"agylite seo: {exc}", file=sys.stderr)
        return 2
    print(p.stdout, end="")
    print(p.stderr, end="", file=sys.stderr)
    if out:
        print(f"[agylite] output: {out}")
    return p.returncode


def _media_cmd(args):
    from .paths import current_bundle, agylite_home
    from .runtimes import brag
    project = _project_ref(args)
    try:
        if args.media_cmd == "plan":
            _print(brag.plan(project, current_bundle(), full=args.full), args.json)
            return 0
        p = brag.music_cues(agylite_home(), current_bundle(), Path(args.audio),
                            Path(args.out) if args.out else project.root / "brag-output" / "audio")
    except brag.BragError as exc:
        print(f"agylite media: {exc}", file=sys.stderr)
        return 1
    print(p.stdout, end="")
    print(p.stderr, end="", file=sys.stderr)
    return p.returncode


def _adapters_cmd(args):
    from .adapters import all_adapters, get
    adapters = [get(args.host)] if getattr(args, "host", None) else all_adapters()
    if args.adapters_cmd == "status":
        _print({"hosts": [a.status() for a in adapters]}, args.json)
        return 0
    if args.adapters_cmd == "render":
        if args.check:
            stale = {a.host: a.stale() for a in adapters if a.stale()}
            for host, files in stale.items():
                print(f"  ✗ {host}: {', '.join(files)} out of date (run `agylite adapters render`)")
            print("adapter files: " + ("current" if not stale else f"{sum(map(len, stale.values()))} stale"))
            return 1 if stale else 0
        for a in adapters:
            for rel in a.write_repo_files():
                print(f"{a.host}: wrote {rel}")
        return 0
    try:
        done = adapters[0].install() if args.adapters_cmd == "install" else adapters[0].uninstall()
    except (NotImplementedError, FileExistsError) as exc:
        print(f"agylite adapters {args.adapters_cmd}: {exc}", file=sys.stderr)
        return 1
    for d in done:
        print(f"{args.adapters_cmd}ed {d}")
    return 0


def _dashboard_cmd(args):
    from .dashboard.server import Dashboard
    project = _project_ref(args)
    try:
        d = Dashboard(project, port=args.port, demo=args.demo,
                      sleep_after=args.idle_minutes * 60 if args.idle_minutes is not None else None)
    except OSError as exc:
        print(f"agylite dashboard: cannot listen on 127.0.0.1:{args.port} ({exc})", file=sys.stderr)
        return 1
    print(f"Agent Office for {project.name}: {d.url}" + ("  (demo replay)" if args.demo else ""), flush=True)
    print("Read-only · 127.0.0.1 only · stops after it has been idle, or with Ctrl+C.", flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(d.url)   # the user's own browser shows the page; the OS never drives it
    reason = d.serve()
    print(f"dashboard stopped ({reason})")
    return 0


def _update_cmd(args):
    from .events import emit
    from .paths import agylite_home
    from .update import UpdateError, gc, rollback, update
    home = agylite_home()
    try:
        if args.command == "update" and (args.check or args.latest or args.promote or args.schedule):
            from .update import track
            if args.schedule:
                path = track.schedule(home, enable=args.schedule == "install")
                print(f"weekly update job {'installed' if args.schedule == 'install' else 'removed'}: {path}")
                return 0
            if args.promote:
                changed = track.promote(home)
                print("pins promoted into docs/audit/evidence: " + (", ".join(changed) or "none changed"))
                return 0
            repos = [args.repo] if args.repo else None
            if args.check:
                rows = track.check(home, repos=repos)
                if args.json:
                    _print(rows, True)
                else:
                    for x in rows:
                        print(f"{x['repo']:11} {x['track']:8} {x['pinned'][:7]} → {(x['latest'] or '???????')[:7]}  "
                              f"{x['status']}{'' if x['due'] else ' (not due)'}{'  ' + x['error'] if x.get('error') else ''}")
                return 0
            rows = track.latest(home, only_due=args.due, repos=repos, tracks=args.track or None)
            if args.json:
                _print(rows, True)
            else:
                for x in rows:
                    extra = f" · {x['commits']} commits" if x.get("commits") is not None else ""
                    print(f"{x['repo']:11} {x['action']:10} {x['pinned'][:7]} → {(x.get('latest') or '')[:7]}{extra}"
                          + (f"  ✗ {x['errors'][0]}" if x.get("errors") else ""))
            ok = [x for x in rows if x["action"] == "activated"]
            for x in ok:
                emit(_project_ref(args), "UPSTREAM_UPDATED", severity="medium",
                     details={"repo": x["repo"], "from": x["pinned"], "to": x["latest"], "bundle_id": x["bundle_id"]})
            return 1 if any(x["action"] == "failed" for x in rows) else 0
        if args.command == "update":
            if not (args.repo and args.sha):
                print("agylite update: give <repo> <sha>, or use --check / --latest", file=sys.stderr)
                return 2
            r = update(home, args.repo, args.sha, source=Path(args.source) if args.source else None,
                       self_test=args.self_test)
            if r["status"] == "activated":
                emit(_project_ref(args), "UPSTREAM_UPDATED", severity="medium",
                     details={k: r[k] for k in ("repo", "from", "to", "bundle_id", "previous_bundle")})
        elif args.command == "rollback":
            r = rollback(home, args.to)
            emit(_project_ref(args), "UPSTREAM_ROLLBACK", severity="medium", details=r)
        else:
            r = gc(home, dry_run=args.dry_run)
    except (UpdateError, OSError) as exc:
        print(f"agylite {args.command}: {exc}", file=sys.stderr)
        return 1
    _print(r, args.json)
    return 0 if r.get("status", "ok") in ("activated", "ok") or args.command != "update" else 1


def _guarded(func):
    """Expected user-facing errors print one line and exit 1 instead of a traceback."""
    def run(args):
        from .project.decisions import DecisionError
        from .project.lifecycle import TransitionError
        from .project.plan_index import PlanError
        from .project.reconcile import ReconcileError
        from .project.state import StateError
        try:
            return func(args)
        except (StateError, PlanError, ReconcileError, TransitionError, DecisionError) as exc:
            print(f"agylite {args.command}: {exc}", file=sys.stderr)
            return 1
    return run


def build_parser():
    parser = argparse.ArgumentParser(prog="agylite", description="Agylite")
    parser.add_argument("-v", "--version", action="version", version=f"agylite v{__version__}")
    sub = parser.add_subparsers(dest="command")

    for name, func, helptext in (("doctor", _doctor, "Check plugin structure, manifests, environment and no-MCP"),
                                 ("validate", _validate, "Run the validation suite")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--root", help="Repository root to check (default: this package's repo)")
        p.set_defaults(func=func)
        if name == "validate":
            p.add_argument("--online", action="store_true", help="Verify pinned SHAs against GitHub")
            p.add_argument("--no-unittest", action="store_true", help="Skip running the unit test suite")

    p = sub.add_parser("benchmark", help="Measure the always-loaded context of installed host plugins")
    p.add_argument("--baseline", action="store_true", help="Old-model baseline only (default)")
    p.add_argument("--compare", action="store_true", help="OLD vs NEW per spec scenario: tokens, routing accuracy, speed")
    p.add_argument("--out", help="With --compare: also write the Markdown report here")
    p.add_argument("--plugins-root", help="Claude Code plugins dir (default: ~/.claude/plugins)")
    q = p.add_argument_group("quality (MP2: is Agylite as good as the upstream skill?)")
    q.add_argument("--quality", action="store_true", help="Quality benchmark instead of the token comparison")
    q.add_argument("--tier", type=int, choices=(0, 1), default=0, help="0: deterministic, free · 1: paid A/B sessions")
    q.add_argument("--suite", help="Tier 1 suite(s), comma-separated")
    q.add_argument("--arms", default="baseline,upstream,agylite")
    q.add_argument("--runs", type=int, default=1)
    q.add_argument("--tasks", help="Only these task ids (comma-separated)")
    q.add_argument("--dry-run", action="store_true", help="Print the session matrix; start nothing")
    q.add_argument("--yes-spend", action="store_true", help="Required to start paid sessions")
    q.add_argument("--max-sessions", type=int, help="Hard cap on paid sessions")
    q.add_argument("--model", help="Actor model id (default claude-opus-5-5)")
    q.add_argument("--judge-model", help="Grader/judge model id (default: the actor's)")
    q.add_argument("--bundle", help="Tier 0 against this bundle directory (default: current)")
    q.add_argument("--baseline-save", help="Tier 0: save this run as the baseline file")
    q.add_argument("--compare-to", help="Tier 0: regression check against a saved baseline")
    q.add_argument("--report", help="Re-render a Tier 1 run directory's report")
    q.add_argument("--resume", help="Tier 1: continue a stopped run directory (keeps its valid cells, runs the rest)")
    q.add_argument("--reuse-from", help="Tier 1: new run reusing an earlier run's cells for the arms not in --arms "
                                        "(e.g. --arms agylite after an AgyLite change)")
    p.set_defaults(func=_benchmark)

    p = sub.add_parser("bundle", help="Fetch pinned upstreams, build/verify/list the local capability bundle")
    bsub = p.add_subparsers(dest="bundle_cmd", required=True)
    b = bsub.add_parser("fetch", help="Clone the 14 pinned upstreams (network; explicit, D-023)")
    b.add_argument("--staging", help="Destination (default: $AGYLITE_HOME/staging/upstream)")
    b = bsub.add_parser("build", help="Build the bundle from staged upstreams")
    b.add_argument("--staging", help="Staged upstream snapshots (default: repo .staging/ or $AGYLITE_HOME/staging)")
    b.add_argument("--no-activate", action="store_true", help="Build without switching `current`")
    b.add_argument("--self-test", action="store_true", help="Run bundled runtime self-tests (Unlazy, UI/UX Pro Max)")
    b = bsub.add_parser("verify", help="Re-hash a bundle against its provenance")
    b.add_argument("bundle_id", nargs="?", help="Bundle id (default: current)")
    bsub.add_parser("list", help="List built bundles")
    p.set_defaults(func=_bundle)

    p = sub.add_parser("registry", help="Check, generate and inspect the capability registry")
    rsub = p.add_subparsers(dest="registry_cmd", required=True)
    r = rsub.add_parser("check", help="Validate cards, CARD.md and the generated registry (and the current bundle's)")
    r.add_argument("--no-bundle", action="store_true", help="Check the repository only, ignore any built bundle")
    rsub.add_parser("cards", help="Render every CARD.md from its card.yaml")
    r = rsub.add_parser("build", help="(Re)generate registry.yaml for a built bundle")
    r.add_argument("bundle_id", nargs="?", help="Bundle id (default: current)")
    rsub.add_parser("list", help="List capabilities (current bundle's registry, else the extraction plan)")
    r = rsub.add_parser("show", help="Show one capability's registry entry")
    r.add_argument("capability", help="Capability id, e.g. engineering/security")
    r.add_argument("--paths", action="store_true", help="List every source path instead of counts")
    p.set_defaults(func=_registry)

    p = sub.add_parser("route", help="Route a request to capabilities (deterministic; JSON output)")
    p.add_argument("request", nargs="+", help="The user request text")
    p.add_argument("--paths", nargs="*", help="Files the request touches (path rules, spec §15)")
    p.add_argument("--capability", action="append", help="Force-include a capability the user named explicitly")
    stage = p.add_mutually_exclusive_group()
    stage.add_argument("--new", action="store_true", help="Treat the project as new (requirements first)")
    stage.add_argument("--existing", action="store_true", help="Treat the project as existing (codebase first)")
    p.add_argument("--stack", nargs="*", help="Detected stack, e.g. python django (selects stack packs)")
    p.add_argument("--brief", action="store_true", help="One-line summary instead of JSON")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.set_defaults(func=_route)

    p = sub.add_parser("bootstrap", help="Print the Level-0 bootstrap context for this project and session")
    p.add_argument("--host", default="cli", help="Host name (claude-code, codex, cursor, antigravity, cli)")
    p.add_argument("--session", help="Session id (default: $AGYLITE_SESSION_ID, else a new id)")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.set_defaults(func=_bootstrap)

    p = sub.add_parser("hook", help="Host hook entry points (Claude Code UserPromptSubmit: `hook prompt`)")
    p.add_argument("hook_cmd", choices=("prompt",))
    p.add_argument("--host", default="claude-code")
    p.set_defaults(func=_hook)

    p = sub.add_parser("skill", help="Load one whole skill by id (Plan B): `agylite skill load <upstream>/<name>`")
    p.add_argument("skill_cmd", choices=("load", "list"))
    p.add_argument("skill_id", nargs="?", help="e.g. ponytail/ponytail-review, taste/design-taste-frontend")
    p.add_argument("--capability", help="With list: only this capability's skills")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.add_argument("--session", help="Session id (default: $AGYLITE_SESSION_ID)")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=_skill)

    p = sub.add_parser("skills", help="Search every upstream's skills (de-duplicated catalog) and fetch one at its pin")
    p.add_argument("skills_cmd", choices=("search", "get"))
    p.add_argument("words", nargs="+", help="search: words · get: one skill id from search")
    p.add_argument("-n", type=int, default=5, help="search: results (default 5)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_skills)

    p = sub.add_parser("context", help="Load L1/L2 context for capabilities, or one L3 file (explicit)")
    p.add_argument("capability", nargs="*", help="Capability ids (from `agylite route`)")
    p.add_argument("--level", type=int, choices=(1, 2, 3), default=2,
                   help="1 = cards only; 2 = cards + capability files; 3 = one --file (explicit only)")
    p.add_argument("--route", metavar="REQUEST", help="Route REQUEST and load the selected capabilities")
    p.add_argument("--whole", type=int, choices=(1, 2), help="Whole primary skills to load (default: what the route says, else 1)")
    p.add_argument("--request", help="Request text used to rank files and sections")
    p.add_argument("--file", help="Level 3: one bundle file (path as listed by L2), explicit only")
    p.add_argument("--section", action="append", help="With --file: only these section ids")
    p.add_argument("--session", help="Session id (default: $AGYLITE_SESSION_ID); enables the session cache")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.add_argument("--no-cache", action="store_true", help="Resend content even if already loaded this session")
    p.add_argument("--json", action="store_true", help="JSON output with the load log")
    p.set_defaults(func=_context)

    def project_arg(parser):
        parser.add_argument("--project", help="Project directory (default: current directory)")
        parser.add_argument("--json", action="store_true", help="JSON output")

    p = sub.add_parser("project", help="Initialise and inspect this project's compact state")
    psub = p.add_subparsers(dest="project_cmd", required=True)
    q = psub.add_parser("init", help="Create .agylite/state.yaml (and docs/ templates with --docs)")
    stage = q.add_mutually_exclusive_group()
    stage.add_argument("--new", action="store_true", help="New project: requirements first")
    stage.add_argument("--existing", action="store_true", help="Existing project: codebase first")
    q.add_argument("--stack", nargs="*", help="Override the detected stack tags")
    q.add_argument("--docs", action="store_true", help="Add the spec §20 document templates under docs/ (never overwrites)")
    q.add_argument("--force", action="store_true", help="Reset existing state")
    project_arg(q)
    project_arg(psub.add_parser("status", help="Project identity and compact summary"))
    q = psub.add_parser("questions", help="Requirements questions worth asking now (spec §53)")
    q.add_argument("request", nargs="*", help="The request being planned")
    project_arg(q)
    q = psub.add_parser("answer", help="Record the answer to a requirements question")
    q.add_argument("question", help="Question id")
    q.add_argument("answer", nargs="+", help="Answer text")
    project_arg(q)
    q = psub.add_parser("relink", help="Move machine-local data after the project was moved or re-cloned")
    q.add_argument("--from", dest="old_id", required=True, help="Previous project id")
    project_arg(q)
    p.set_defaults(func=_guarded(_project_cmd))

    p = sub.add_parser("state", help="Compact project state (cheap read)")
    project_arg(p)
    p.set_defaults(func=_guarded(_state_cmd))

    p = sub.add_parser("plan", help="Implementation plan index, sections, reconciliation and statuses")
    psub = p.add_subparsers(dest="plan_cmd", required=True)
    q = psub.add_parser("index", help="List phases from the compact index")
    q.add_argument("--rebuild", action="store_true", help="Re-read the plan even if unchanged")
    project_arg(q)
    q = psub.add_parser("show", help="Print one phase section of the plan")
    q.add_argument("phase", help="Phase id, e.g. P4")
    project_arg(q)
    q = psub.add_parser("locate", help="Which phase a request belongs to")
    q.add_argument("request", nargs="+")
    q.add_argument("--paths", nargs="*")
    project_arg(q)
    q = psub.add_parser("add-task", help="Add a PLANNED task to a phase")
    q.add_argument("phase")
    q.add_argument("title", nargs="+")
    q.add_argument("--capability", action="append")
    q.add_argument("--depends", action="append", help="A blocking task id (repeat for several)")
    q.add_argument("--acceptance")
    project_arg(q)
    q = psub.add_parser("set-status", help="Set a task (T-…) or phase (P…) status (spec §25 states)")
    q.add_argument("item")
    q.add_argument("status")
    q.add_argument("--evidence", help="Required for VERIFIED/COMPLETED")
    project_arg(q)
    q = psub.add_parser("reconcile", help="Route a change, locate its phase, add it to the plan (spec §56)")
    q.add_argument("request", nargs="+")
    q.add_argument("--paths", nargs="*")
    q.add_argument("--new-phase", help="Name of a new phase when no existing phase fits")
    project_arg(q)
    p.set_defaults(func=_guarded(_plan_cmd))

    p = sub.add_parser("decide", help="Structured decision memory (spec §50–52)")
    dsub = p.add_subparsers(dest="decide_cmd", required=True)
    q = dsub.add_parser("add", help="Record a decision")
    q.add_argument("--kind", required=True)
    q.add_argument("--topic", required=True)
    q.add_argument("--decision", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--alternative", action="append")
    q.add_argument("--impact")
    q.add_argument("--supersedes")
    q.add_argument("--tag", action="append")
    project_arg(q)
    q = dsub.add_parser("list", help="List decisions (ACTIVE by default)")
    q.add_argument("--kind")
    q.add_argument("--topic")
    q.add_argument("--all", action="store_true")
    project_arg(q)
    q = dsub.add_parser("show", help="Show one decision")
    q.add_argument("id")
    project_arg(q)
    p.set_defaults(func=_guarded(_decide_cmd))

    p = sub.add_parser("used", help="What this session used: capabilities, upstream projects, engines, core steps")
    p.add_argument("--session", help="Session id (default: the host's current session, else the newest)")
    project_arg(p)
    p.set_defaults(func=_guarded(_used))
    p = sub.add_parser("events", help="Project event log and risk detection (spec §30)")
    esub = p.add_subparsers(dest="events_cmd", required=True)
    q = esub.add_parser("list", help="Show recent events (redacted)")
    q.add_argument("--tail", type=int, default=50)
    q.add_argument("--type", help="Only this event type, e.g. CONTEXT_LOADED")
    q.add_argument("--session")
    project_arg(q)
    q = esub.add_parser("observe", help="Evaluate host tool events (Beacon shape, JSON on stdin) against the rules")
    q.add_argument("--session")
    project_arg(q)
    q = esub.add_parser("rules", help="List the bundled detection rules")
    q.add_argument("--test", action="store_true", help="Run every rule's embedded tests")
    project_arg(q)
    p.set_defaults(func=_events_cmd)

    p = sub.add_parser("runtime", help="Isolated upstream runtimes: status and explicit install (D-016)")
    rsub = p.add_subparsers(dest="runtime_cmd", required=True)
    q = rsub.add_parser("status", help="Health of each runtime (ready / not-installed / broken / no-bundle)")
    q.add_argument("--json", action="store_true", help="JSON output")
    q = rsub.add_parser("unlazy-hook", help="Register/remove Unlazy's Stop hook in ~/.claude/settings.json (never per project)")
    onoff = q.add_mutually_exclusive_group(required=True)
    onoff.add_argument("--enable", action="store_true")
    onoff.add_argument("--disable", action="store_true")
    q = rsub.add_parser("install", help="Install a runtime from the active bundle (network: pip dependencies)")
    q.add_argument("name", choices=("graphify", "seo", "brag"))
    q.add_argument("--browser", action="store_true", help="seo: add the browser extra (Playwright + Chromium, large)")
    q.add_argument("--reports", action="store_true", help="seo: add the PDF reports extra")
    q.add_argument("--json", action="store_true", help="JSON output")
    p.set_defaults(func=_runtime_cmd)

    p = sub.add_parser("gates", help="Acceptance-gate ledgers (Unlazy): status, check, approve, reverify, lint")
    p.add_argument("mode", choices=("status", "check", "approve", "reverify", "lint"))
    p.add_argument("files", nargs="+", help="Ledger files, e.g. GATES.md")
    p.add_argument("--jobs", type=int, help="Parallel independent checks (1..64)")
    p.add_argument("--timeout", type=int, help="Per-check timeout in seconds")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.set_defaults(func=_gates_cmd)

    for name, helptext in (("verify", "Local test-first verification: impacted tests + static checks, with evidence"),
                           ("test", "Run only the impacted tests (same as verify --kind test)")):
        p = sub.add_parser(name, help=helptext)
        if name == "verify":
            p.add_argument("action", nargs="?", choices=("exception",),
                           help="exception: record a browser-exception request (runs nothing)")
            p.add_argument("--reason", help="With exception: why local verification is insufficient")
            p.add_argument("--kind", action="append", choices=("test", "security", "typecheck", "lint", "build", "e2e"))
        p.add_argument("--paths", nargs="*", help="Changed files (default: git working-tree changes)")
        p.add_argument("--plan", action="store_true", help="Show the selected checks without running them")
        p.add_argument("--all", action="store_true", help="Full suites instead of impacted tests")
        p.add_argument("--include-e2e", action="store_true", help="Also run the project's own headless E2E script")
        p.add_argument("--task", help="Plan task this verifies (recorded with the evidence)")
        p.add_argument("--timeout", type=int, default=900, help="Per-check timeout in seconds")
        p.add_argument("--session")
        project_arg(p)
        p.set_defaults(func=_verify_cmd)

    p = sub.add_parser("seo", help="BeyondSEO runtime: audits, research, evidence; live-site edits need authorization")
    ssub = p.add_subparsers(dest="seo_cmd", required=True)
    q = ssub.add_parser("run", help="Run a BeyondSEO command, e.g. `agylite seo run crawl https://example.com`")
    q.add_argument("--authorization", help="Authorization id for `edit apply|rollback` (live website writes)")
    project_arg(q)
    q.add_argument("args", nargs=argparse.REMAINDER, help="BeyondSEO command and its arguments")
    q = ssub.add_parser("evidence", help="Label what a crawl run can support: FACT/OBSERVATION/UNKNOWN per page")
    q.add_argument("run_dir")
    project_arg(q)
    q = ssub.add_parser("authorize", help="Authorize live-website edits for one task (expires)")
    q.add_argument("--site", required=True)
    q.add_argument("--task", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--hours", type=int, default=2)
    project_arg(q)
    p.set_defaults(func=_seo_cmd)

    p = sub.add_parser("media", help="Launch videos (Brag): mode/tool plan, music-cue analysis")
    msub = p.add_subparsers(dest="media_cmd", required=True)
    q = msub.add_parser("plan", help="Which Brag workflow runs here (brag-slim default) and which tools are available")
    q.add_argument("--full", action="store_true", help="Ask for full /brag (only if Hyperframes is installed locally)")
    project_arg(q)
    q = msub.add_parser("music-cues", help="Beat/cue analysis of a soundtrack (needs `agylite runtime install brag`)")
    q.add_argument("audio")
    q.add_argument("--out", help="Output directory (default brag-output/audio in the project)")
    project_arg(q)
    p.set_defaults(func=_media_cmd)

    p = sub.add_parser("update", help="Pin one upstream to a new commit: build, check, switch only if everything passes")
    p.add_argument("repo", nargs="?", help="Upstream name, e.g. graphify")
    p.add_argument("sha", nargs="?", help="Full 40-character commit SHA")
    p.add_argument("--check", action="store_true", help="Show which upstreams have new commits (no download)")
    p.add_argument("--latest", action="store_true", help="Apply new upstream commits (all, or the named repo)")
    p.add_argument("--due", action="store_true", help="With --latest: only upstreams whose interval has passed")
    p.add_argument("--promote", action="store_true", help="Write the active bundle's pins into docs/audit/evidence (CI)")
    p.add_argument("--track", action="append", choices=("weekly", "monthly", "releases"),
                   help="With --latest: only upstreams with this policy (repeatable)")
    p.add_argument("--schedule", choices=("install", "remove"), help="Weekly job on this Mac (LaunchAgent)")
    p.add_argument("--source", help="Local tree of that commit (offline mirror); default: fetch it (network)")
    p.add_argument("--self-test", action="store_true", help="Also run the runtime self-tests before switching")
    p.add_argument("--json", action="store_true")
    p.add_argument("--project", help=argparse.SUPPRESS)
    p.set_defaults(func=_update_cmd)
    p = sub.add_parser("rollback", help="Switch back to the previous (or a named) known-good bundle")
    p.add_argument("--to", help="Bundle id (default: previous)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--project", help=argparse.SUPPRESS)
    p.set_defaults(func=_update_cmd)
    p = sub.add_parser("gc", help="Remove old bundles and unused runtimes (keeps current, previous, 2 newest failed)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_update_cmd)

    p = sub.add_parser("dashboard", help="Agent Office: live, read-only view of this project's agents (127.0.0.1)")
    p.add_argument("--port", type=int, default=0, help="Port (default: a free one)")
    p.add_argument("--demo", action="store_true", help="Replay sample events instead of the project's event log")
    p.add_argument("--open", action="store_true", help="Open the page in your default browser")
    p.add_argument("--idle-minutes", type=float, help="Stop after this many minutes without a page poll (default 10)")
    p.add_argument("--project", help="Project directory (default: current directory)")
    p.set_defaults(func=_dashboard_cmd)

    p = sub.add_parser("adapters", help="Host packaging and status: Claude Code, Codex, Cursor, Antigravity")
    asub = p.add_subparsers(dest="adapters_cmd", required=True)
    q = asub.add_parser("status", help="FILES_PRESENT / INSTALLED / RUNTIME_VERIFIED per host (spec §34)")
    q.add_argument("--host", choices=("claude-code", "codex", "cursor", "antigravity"))
    q.add_argument("--json", action="store_true")
    q = asub.add_parser("render", help="(Re)generate the host files in this repository from the entry skills")
    q.add_argument("--host", choices=("claude-code", "codex", "cursor", "antigravity"))
    q.add_argument("--check", action="store_true", help="Only report out-of-date files (CI/validate)")
    for name in ("install", "uninstall"):
        q = asub.add_parser(name, help=f"{name.capitalize()} user-level skills (cursor: ~/.cursor/skills, "
                                       "antigravity: ~/.gemini/config/skills)")
        q.add_argument("--host", required=True, choices=("cursor", "antigravity"))
    p.set_defaults(func=_adapters_cmd)

    p = sub.add_parser("design", help="Design engine (UI/UX Pro Max) search/system and local design-token checks")
    dsub2 = p.add_subparsers(dest="design_cmd", required=True)
    q = dsub2.add_parser("search", help="Search styles, colors, typography, UX rules, stack guidance")
    q.add_argument("query", nargs="+")
    q.add_argument("--domain", choices=("style", "color", "chart", "landing", "product", "ux", "typography", "icons",
                                        "gsap", "react", "web", "google-fonts"))
    q.add_argument("--stack")
    q.add_argument("-n", "--max-results", type=int, default=3)
    project_arg(q)
    q = dsub2.add_parser("system", help="Generate a design system; --persist writes design-system/ in this project only")
    q.add_argument("query", nargs="+")
    q.add_argument("--project-name")
    q.add_argument("--persist", action="store_true")
    q.add_argument("--page")
    q.add_argument("--force", action="store_true", help="Overwrite an existing MASTER.md")
    for dial in ("variance", "motion", "density"):
        q.add_argument(f"--{dial}", type=int, choices=range(1, 11), metavar="1-10")
    project_arg(q)
    q = dsub2.add_parser("check", help="Design-token checks: accents, greys, radii, fonts (config/design.yaml)")
    project_arg(q)
    q = dsub2.add_parser("taste", help="Taste v2.1 scripts: draw | inspect | lint | scenes | assets | status (MP4)")
    project_arg(q)
    q.add_argument("script", choices=("draw", "inspect", "lint", "scenes", "assets", "status"))
    q.add_argument("args", nargs=argparse.REMAINDER, help="Passed to the script (e.g. --sector, --options 3)")
    p.set_defaults(func=_design_cmd)

    p = sub.add_parser("codebase", help="Code graph (Graphify): affected files + related tests, scoped queries")
    csub = p.add_subparsers(dest="codebase_cmd", required=True)
    q = csub.add_parser("affected", help="Files and tests impacted by a change (default: git working-tree changes)")
    q.add_argument("--paths", nargs="*", help="Changed files or directories (default: `git status`)")
    q.add_argument("--depth", type=int, default=2, help="Reverse traversal depth (default 2)")
    q.add_argument("--structural", action="store_true", help="Skip the graph; limited structural analysis only")
    q.add_argument("--update", action="store_true", help="Force a graph rebuild first")
    project_arg(q)
    q = csub.add_parser("update", help="Build or refresh the project graph (only when code changed)")
    q.add_argument("--force", action="store_true", help="Rebuild even if unchanged")
    project_arg(q)
    for name, helptext in (("query", "Scoped subgraph for a question"), ("path", "Shortest path between two nodes"),
                           ("explain", "Explain one node and its neighbours")):
        q = csub.add_parser(name, help=helptext)
        q.add_argument("terms", nargs="+")
        q.add_argument("--budget", type=int, help="Token cap for the output (Graphify default 2000)")
        project_arg(q)
    p.set_defaults(func=_codebase_cmd)

    for name, phase in PLANNED.items():
        p = sub.add_parser(name, help=f"(available in {phase})")
        p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        p.set_defaults(func=lambda args, n=name, ph=phase: _not_yet(n, ph))
    return parser


def _not_yet(name, phase):
    print(f"agylite {name}: not implemented yet (planned for {phase}).", file=sys.stderr)
    return 2


def _note_engine(args, code):
    """RUNTIME_USED for commands that run an upstream engine (`agylite used` reports them). Never raises."""
    from .events.used import ENGINES
    engine = ENGINES.get(getattr(args, "command", None))
    if not engine:
        return
    try:
        sub = next((getattr(args, a) for a in vars(args) if a.endswith("_cmd") and getattr(args, a)), None)
        details = {"engine": engine, "command": " ".join(x for x in (args.command, sub) if x), "exit_code": code}
        if engine == "graphify":
            from .paths import agylite_home, current_bundle
            from .runtimes import graphify
            ready = graphify.health(agylite_home(), current_bundle()).get("status") == "ready"
            if not ready:   # structural fallback: Graphify itself did not run
                return
        from .events import emit
        emit(_project_ref(args), "RUNTIME_USED", details=details)
    except Exception:   # noqa: BLE001 — reporting must never change a command's outcome
        pass


def _used(args):
    import json

    from .events.log import current_session, read
    from .events.used import render, session_events, summarize
    project = _project_ref(args)
    sid, events = session_events(read(project), args.session or current_session(project))
    summary = summarize(events)
    print(json.dumps({"session_id": sid, **summary}, indent=1) if args.json else render(summary, sid))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    from .events import install_hooks
    install_hooks()   # isolation violations → ISOLATION_VIOLATION_BLOCKED events
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        code = args.func(args)
        _note_engine(args, code)
        return code
    except KeyboardInterrupt:
        print(f"\nagylite {args.command}: stopped (Ctrl+C)", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
