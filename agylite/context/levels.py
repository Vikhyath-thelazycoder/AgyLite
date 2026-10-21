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
    index = ["capabilities (route: `agylite route \"<request>\"` · load: `agylite skill load <upstream>/<skill>` or "
             "`agylite context <id>…` · rare needs: `agylite skills search \"<words>\"`):"]
    index += [f"  {d}: " + ", ".join(c.split("/", 1)[1] for c in m["capabilities"]) for d, m in domains.items()]

    discipline = discipline_lines(bundle_dir)

    def assemble(state_part):
        return "\n".join(head + [f"state: {s}" for s in state_part] + index + discipline) + "\n"

    state = list(state_lines)
    text = assemble(state)
    while state and est_tokens(nbytes(text)) > limit:    # state lines are the only variable part
        state = state[:-1]
        text = assemble(state + ["(truncated to the L0 budget; run `agylite state`)"])
    return {"level": "L0", "text": text, "est_tokens": est_tokens(nbytes(text)), "limit": limit}


RULESET = "files/ponytail/RULESET-lite.md"


def load_discipline(root=None):
    from .prompt_hook import load_discipline as load
    return load(root)


def discipline_lines(bundle_dir, root=None) -> list:
    """MP3 §2.2: the Ponytail lite ruleset, whole, plus a pointer to the full principles (never truncated; L0 drops
    state lines first). `ponytail_ruleset: off` in config/discipline.yaml removes it."""
    if str(load_discipline(root).get("ponytail_ruleset", "lite")).lower() in ("off", "false"):
        return []
    path = bundle_dir / RULESET if bundle_dir else None
    if path is None or not path.is_file():
        return ["discipline: the Ponytail lite ruleset is not in this bundle (rebuild: `agylite bundle build`)"]
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("<!--"):                      # the provenance comment stays in the file
        text = text.split("-->", 1)[1].strip()
    return ["discipline (always on):", text,
            "Full principles (Karpathy): `agylite context engineering/principles`."]


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


def skill_id(entry) -> str:
    """`<upstream>/<skill name>` (e.g. `ponytail/ponytail-review`, `taste/design-taste-frontend`)."""
    parts = entry["path"].split("/")
    folder = parts[-2] if parts[-1].startswith("SKILL.md") and len(parts) > 3 else parts[-1]
    return f"{parts[1]}/{entry.get('name') or folder}"


def primary_skill(entries, query=None, priority=()):
    """The capability's primary skill: the first `sources_priority` match, else its best-ranked SKILL.md."""
    ranked = _rank_files(entries, query, priority)
    return next((e for e in ranked if e["kind"] == "skill"), ranked[0] if ranked else None)


def skill_unit(loader, entry) -> dict:
    """The skill's folder (relative links resolve there) and its other bundled files, read on demand."""
    folder = entry["path"].rsplit("/", 1)[0]
    files = sorted({e["path"]: e for es in loader.index["capabilities"].values() for e in es
                    if e["path"].startswith(folder + "/") and e["path"] != entry["path"]}.values(),
                   key=lambda e: e["path"])
    return {"folder": folder, "files": files}


def whole_skill(loader, entry, level="L2") -> tuple:
    """(text, sent tokens): one skill's SKILL.md in full — no section picking, no truncation (Plan B) — followed by
    its folder and file list. A file already sent in this session becomes a `[cached]` marker."""
    unit = skill_unit(loader, entry)
    bundle = loader.require_bundle()
    head = f"### {entry['path']} — {entry.get('name', '')} (skill {skill_id(entry)}, whole)\n"
    if loader.cached(entry["path"], sha256=entry["sha256"], sections=["all"]):
        loader.note_hit(entry["path"], level, ["all"])
        body = _cached_marker(entry["path"], ["all"])
    else:
        body = loader.read(bundle / entry["path"], display=entry["path"], level=level).rstrip() + "\n"
        loader.record(entry["path"], level=level, sha256=entry["sha256"], sections=["all"], sent_bytes=nbytes(body))
    tail = f"Skill folder: {bundle / unit['folder']} (this skill's relative paths resolve here)\n"
    if unit["files"]:
        tail += ("Files of this skill (read when the skill says so, e.g. `agylite context --file <path>`): "
                 + ", ".join(f"{e['path']} (~{e['tokens']})" for e in unit["files"][:40])
                 + (" …" if len(unit["files"]) > 40 else "") + "\n")
    text = head + body + tail
    return text, est_tokens(nbytes(body))


def capability_context(loader, cids, budgets, query=None, priorities=None, whole=1):
    """L2 (IMPLEMENTATION_PLAN §2.1, Plan B): the primary skill of the highest-ranked capability loads whole, a second
    one too when `whole=2` (strong signals in two domains) and it fits `max_tokens_per_task`; every other routed
    capability is index only, naming its primary skill for `agylite skill load`. Secondary sources stay L3."""
    cfg = budgets["levels"]["L2"]
    priorities = source_priorities() if priorities is None else priorities
    n_whole = min(max(int(whole), 1), cfg["max_whole_skills_per_task"])
    budget = Budget(cfg["max_tokens_per_task"])
    parts, full, index_only = [], [], []
    for i, cid in enumerate(cids):
        entries = loader.files_of(cid)
        prim = primary_skill(entries, query, priorities.get(cid, ()))
        if prim is not None and len(full) < n_whole and i < n_whole and (not full or budget.fits(prim["tokens"])):
            text, sent = whole_skill(loader, prim)
            budget.take(sent)
            full.append(cid)
            parts.append(f"## {cid} · L2\n{text}")
            rest = [e for e in _rank_files(entries, query, priorities.get(cid, ()))
                    if e["path"] != prim["path"] and not e["path"].startswith(prim["path"].rsplit("/", 1)[0] + "/")]
            if rest:
                parts.append(f"Secondary sources of {cid} (L3, explicit only): "
                             + ", ".join(f"{e['path']} (~{e['tokens']})" for e in rest[:8])
                             + (" …" if len(rest) > 8 else "") + "\n")
            continue
        index_only.append(cid)
        parts.append(f"## {cid} · index only: " + (f"primary skill {skill_id(prim)} → `agylite skill load {skill_id(prim)}`"
                                                    if prim else "OS-native (no bundled skill)") + "\n")
    text = "".join(parts)
    return {"level": "L2", "text": text, "est_tokens": est_tokens(nbytes(text)), "limit": cfg["max_tokens_per_task"],
            "capabilities_full": full, "capabilities_index_only": index_only}


def find_skill(loader, sid: str):
    """The bundled SKILL.md entry whose skill id is `sid`, else None."""
    for entries in loader.index["capabilities"].values():
        for e in entries:
            if e["kind"] == "skill" and skill_id(e) == sid:
                return e
    return None


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
