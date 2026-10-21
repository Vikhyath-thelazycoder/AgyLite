"""Progressive context levels (spec §16): L0 bootstrap · L1 routed capability cards · L2 capability files (sections) ·
L3 deep reference (explicit only). Every assembly respects config/budgets.yaml and goes through the ContextLoader."""
import fnmatch
import os

from .. import __version__
from ..registry import loader as registry
from ..routing.fallback_bm25 import BM25
from .budget import Budget
from .loader import ContextError, sections_from
from .sections import est_tokens, nbytes, pick_sections, render

L2_KINDS = ("skill", "doc")
L2_LISTING_RESERVE = 0.15
L3_KINDS = ("skill", "doc", "reference", "data")


def _cached_marker(path, sections):
    scope = f" §{', §'.join(sections)}" if sections and sections != ["all"] else ""
    return f"[cached] {path}{scope}: already in this session's context (unchanged); pass --no-cache to resend.\n"


def bootstrap(*, project, session_id, host, bundle_dir, budgets, root=None, stage="unknown", phase=None,
              state_lines=(), plan_pointer=None):
    """L0: identity, host, project/session, phase, compact state, plan pointer and the capability index."""
    from ..project.identity import current_branch
    limit = budgets["levels"]["L0"]["max_tokens"]
    branch = current_branch(project.root) if project else None
    head = [
        "# Agylite · L0 bootstrap",
        f"os: agylite v{__version__} · bundle {bundle_dir.name if bundle_dir else 'none (run scripts/install)'}"
        f" · host {host}",
        (f"project: {project.name} ({project.project_id}) · stage {stage}" + (f" · branch {branch}" if branch else ""))
        if project else "project: none",
        f"session: {session_id or 'none'}",
        *([f"cli: {os.environ['AGYLITE_CLI']} (use this when `agylite` is not on PATH)"]
          if os.environ.get("AGYLITE_CLI") else []),
        f"phase: {phase or '—'}",
        f"plan: {plan_pointer or '—'}",
    ]
    domains = registry.load_domains(root)
    index = ["capabilities (route: `agylite route \"<request>\"` · load: `agylite context <id>…`):"]
    index += [f"  {d}: " + ", ".join(c.split("/", 1)[1] for c in m["capabilities"]) for d, m in domains.items()]

    def assemble(state_part):
        return "\n".join(head + [f"state: {s}" for s in state_part] + index) + "\n"

    state = list(state_lines)
    text = assemble(state)
    while state and est_tokens(nbytes(text)) > limit:    # state lines are the only variable part
        state = state[:-1]
        text = assemble(state + ["(truncated to the L0 budget; run `agylite state`)"])
    return {"level": "L0", "text": text, "est_tokens": est_tokens(nbytes(text)), "limit": limit}


def domain_context(loader, cids, budgets, root=None):
    """L1: the routed capabilities' rendered cards, grouped by domain, within the per-domain budget."""
    limit = budgets["levels"]["L1"]["max_tokens_per_domain"]
    domains = registry.load_domains(root)
    by_domain = {}
    for cid in cids:
        by_domain.setdefault(cid.split("/", 1)[0], []).append(cid)
    parts = []
    for domain, members in by_domain.items():
        budget = Budget(limit)
        parts.append(f"## {domain}: {domains.get(domain, {}).get('purpose', '')}\n")
        skipped = []
        for cid in members:
            path = registry.capabilities_dir(root) / cid / "CARD.md"
            display = f"capabilities/{cid}/CARD.md"
            if not path.is_file():
                raise ContextError(f"unknown capability {cid}")
            stat = path.stat()
            if loader.cached(display, stat=stat, sections=["all"]):
                loader.note_hit(display, "L1")
                parts.append(_cached_marker(display, ["all"]))
                continue
            if not budget.fits(est_tokens(stat.st_size)):
                skipped.append(cid)
                continue
            text = loader.read(path, display=display, level="L1")
            budget.take(est_tokens(nbytes(text)))
            loader.record(display, level="L1", stat=stat, sections=["all"], sent_bytes=nbytes(text))
            parts.append(text + "\n")
        if skipped:
            parts.append(f"(L1 budget reached for {domain}; more cards: {', '.join(skipped)} → "
                         f"`agylite context {skipped[0]} --level 1`)\n")
    text = "".join(parts)
    return {"level": "L1", "text": text, "est_tokens": est_tokens(nbytes(text)), "limit_per_domain": limit}


def priority_rank(path, priority):
    """Index of the first `sources_priority` glob matching `path`; unmatched files rank after every glob (MP1 F5)."""
    return next((i for i, g in enumerate(priority) if fnmatch.fnmatchcase(path, g)), len(priority))


def _rank_files(entries, query, priority=()):
    """L2 candidates: skills and docs; a capability without any (e.g. BeyondSEO playbook-only SEO subdomains) uses its
    own markdown references, which are then its primary instructions. Order: the card's `sources_priority` first,
    then BM25 against the request, then the old tie-breakers — never the folder name alone (MP1 F5)."""
    cands = [e for e in entries if e["kind"] in L2_KINDS] or [e for e in entries if e["kind"] == "reference"]
    if query and cands:
        scores = dict(BM25({e["path"]: " ".join([e.get("name", ""), e.get("description", ""),
                                                  e["path"].replace("/", " ").replace("-", " ")])
                            for e in cands}).score(query))
        return sorted(cands, key=lambda e: (priority_rank(e["path"], priority), -scores.get(e["path"], 0.0),
                                            e["kind"] != "skill", e["tokens"], e["path"]))
    return sorted(cands, key=lambda e: (priority_rank(e["path"], priority), e["kind"] != "skill", e["path"]))


def source_priorities(root=None):
    """{capability id: its card's sources_priority globs}."""
    return {cid: card.get("sources_priority") or [] for cid, card in registry.load_cards(root).items()}


def capability_context(loader, cids, budgets, query=None, priorities=None):
    """L2: the most relevant entry files of up to `max_capabilities_full` capabilities, section by section within
    `max_tokens_per_task`; remaining files and capabilities are listed for explicit L3 / later loading."""
    cfg = budgets["levels"]["L2"]
    priorities = source_priorities() if priorities is None else priorities
    # Content gets the budget minus a reserve for headers and the file/section listings, so the whole L2 text fits.
    total = Budget(int(cfg["max_tokens_per_task"] * (1 - L2_LISTING_RESERVE)))
    bundle = loader.require_bundle()
    full, index_only = list(cids[:cfg["max_capabilities_full"]]), list(cids[cfg["max_capabilities_full"]:])
    plan = []
    for cid in full:
        plan += [(cid, e) for e in _rank_files(loader.files_of(cid), query, priorities.get(cid, ()))
                 [:cfg["max_files_per_capability"]]]
    # Pass 1 — choose sections from metadata only, so the choice (and therefore the cache key) does not depend on
    # what this session already holds. Unused share rolls over to the next file.
    planned, left = [], total.limit
    for i, (cid, e) in enumerate(plan):
        share = max(left // (len(plan) - i), 1)
        secs = sections_from(e)
        chosen, skipped, truncated = pick_sections(secs, share, query)
        cost = sum(s.tokens for s in chosen) if chosen and not truncated else min(e["tokens"], share)
        left -= min(cost, share)
        planned.append((cid, e, share, secs, chosen, skipped, truncated))
    # Pass 2 — send what is not already in this session's context.
    parts, current = [], None
    for cid, e, share, secs, chosen, skipped, truncated in planned:
        if cid != current:
            current = cid
            parts.append(f"## {cid} · L2\n")
        ids = [s.id for s in chosen] or ["all"]
        if loader.cached(e["path"], sha256=e["sha256"], sections=ids):
            loader.note_hit(e["path"], "L2", ids)
            parts.append(_cached_marker(e["path"], ids))
            continue
        text = loader.read(bundle / e["path"], display=e["path"], level="L2")
        out = render(text, chosen, truncated, share) if chosen else text[:share * 4]
        total.take(est_tokens(nbytes(out)))
        loader.record(e["path"], level="L2", sha256=e["sha256"], sections=ids, sent_bytes=nbytes(out))
        header = f"### {e['path']} — {e.get('name', '')}"
        if skipped:
            header += f" (sections {len(chosen)}/{len(secs)}, ≈{est_tokens(nbytes(out))} of {e['tokens']} est. tokens)"
        parts.append(header + "\n" + out.rstrip() + "\n")
        if skipped:
            more = ", ".join(f"{s.id} (~{s.tokens})" for s in skipped[:10])
            parts.append(f"More sections: {more}{' …' if len(skipped) > 10 else ''} → "
                         f"`agylite context --file {e['path']} --section <id>`\n")
    for cid in full:
        loaded = {e["path"] for c, e in plan if c == cid}
        rest = [e for e in loader.files_of(cid) if e["kind"] in L3_KINDS and e["path"] not in loaded]
        rest.sort(key=lambda e: (e["kind"] not in ("skill", "doc", "reference"), e["path"]))
        if rest:
            shown = ", ".join(f"{e['path']} (~{e['tokens']})" for e in rest[:5])
            parts.append(f"{cid}: {len(rest)} more files at L3 (explicit `--file`): {shown}{' …' if len(rest) > 5 else ''}\n")
    for cid in index_only:
        ranked = _rank_files(loader.files_of(cid), query, priorities.get(cid, ()))
        names = ", ".join(e.get("name", e["path"]) for e in ranked[:5]) or "OS-native"
        parts.append(f"## {cid} · index only (L2 capability limit reached): {names} → `agylite context {cid}`\n")
    text = "".join(parts)
    return {"level": "L2", "text": text, "est_tokens": est_tokens(nbytes(text)), "limit": cfg["max_tokens_per_task"],
            "capabilities_full": full, "capabilities_index_only": index_only}


def deep_reference(loader, path: str, budgets, sections=None, query=None):
    """L3: one explicitly requested bundle file (or some of its sections), capped per fetch."""
    limit = budgets["levels"]["L3"]["max_tokens_per_fetch"]
    entry = loader.bundle_entry(path)
    if entry is None:
        raise ContextError(f"{path} is not a file of the installed bundle")
    if entry["kind"] in ("license", "binary"):
        raise ContextError(f"{path} is a {entry['kind']} file, not loadable context")
    secs = sections_from(entry)
    chosen, skipped, truncated = pick_sections(secs, limit, query, wanted=sections) if secs else ([], [], False)
    if sections and not chosen:
        raise ContextError(f"no section {sections} in {path} (sections: {', '.join(s.id for s in secs)})")
    ids = [s.id for s in chosen] or ["all"]
    if loader.cached(path, sha256=entry["sha256"], sections=ids):
        loader.note_hit(path, "L3", ids)
        text = _cached_marker(path, ids)
    else:
        raw = loader.read(loader.require_bundle() / path, display=path, level="L3")
        if chosen:
            text = render(raw, chosen, truncated, limit)
        else:
            text = raw.encode("utf-8")[:limit * 4].decode("utf-8", "ignore")
            if nbytes(raw) > limit * 4:
                text += "\n[… truncated to the L3 budget]\n"
        loader.record(path, level="L3", sha256=entry["sha256"], sections=ids, sent_bytes=nbytes(text))
        if skipped:
            text += f"\nMore sections: {', '.join(f'{s.id} (~{s.tokens})' for s in skipped[:20])}\n"
    return {"level": "L3", "text": f"## {path} · L3\n{text}", "est_tokens": est_tokens(nbytes(text)), "limit": limit}
