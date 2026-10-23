"""The deterministic router (spec §15, D-012): request → change type → domains → capabilities, as JSON-ready data.

Pipeline: normalize → rule/path match → intent-tag match → suppression and project stage → selection limit →
conflicts → dependency/impact closure → fallbacks → (only if not confident) BM25 over CARD.md.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..codebase.impact import code_limit
from ..context.budget import load_budgets
from ..project.lifecycle import load_lifecycle, steps_for
from ..registry import loader
from ..verify import policy
from .classify import classify_change, extract_urls, normalize
from .fallback_bm25 import BM25
from .rules import load_hierarchy, load_routing, match_paths, match_rules, role_of
from .select import ROUTABLE_MODES, Candidate, dependency_closure, domain_of, select_capabilities

# 2: browser, verification_mode (D-035; 6: D-049 browser = required | not-needed). 3: impact (P12). 4: lifecycle (P13).
# 5: urls (MP1 F1) — URLs/domains found in the request; matching sees the placeholder `urlref` in their place;
#    unmatched + fallback_guidance (MP1 F4) — nothing fits, so the agent uses principles only;
#    whole_skills (Plan B) — the capabilities whose primary skill loads whole (one, or two across domains).
ROUTE_SCHEMA_VERSION = 6


@dataclass
class ProjectFacts:
    """What the router knows about the project (filled from project state in P10; flags in the CLI)."""
    stage: str = "unknown"          # new | existing | unknown (spec §19.2)
    project_id: str | None = None
    phase: str | None = None
    stack: tuple = field(default_factory=tuple)


LIFECYCLE_DOMAINS = {"engineering", "codebase", "testing"}
UNMATCHED_GUIDANCE = ("engineering/principles",)   # MP1 F4: always safe when no capability fits


class RoutingError(ValueError):
    pass


class Router:
    def __init__(self, root: Path | None = None, cards=None, cfg=None):
        self.root = root
        self.cards = cards if cards is not None else loader.load_cards(root)
        self.cfg = cfg if cfg is not None else load_routing(root)
        self.hierarchy = load_hierarchy(root)
        self.verification_mode = policy.load_policy(root)["mode"]
        self.code_limit = code_limit(load_budgets(root))
        self.lifecycle = load_lifecycle(root)
        self._bm25 = None

    @property
    def bm25(self) -> BM25:
        """Built on first use only: deterministic routes never read CARD.md."""
        if self._bm25 is None:
            docs = {}
            for cid, card in self.cards.items():
                if card["activation_conditions"]["mode"] not in ROUTABLE_MODES or not card["enabled"]:
                    continue
                path = loader.capabilities_dir(self.root) / cid / "CARD.md"
                body = path.read_text(encoding="utf-8") if path.is_file() else ""
                docs[cid] = " ".join([card["name"], card["description"], " ".join(card["intent_tags"]), body])
            self._bm25 = BM25(docs, stopwords=(self.cfg.get("limits") or {}).get("bm25_stopwords") or ())
        return self._bm25

    def route(self, request: str, paths=(), project: ProjectFacts | None = None, requested=()):
        start = time.perf_counter()
        project = project or ProjectFacts()
        unknown = [c for c in requested if c not in self.cards]
        if unknown:
            raise RoutingError(f"unknown capability {unknown[0]} (see `agylite registry list`)")
        masked, urls = extract_urls(request)
        text = normalize(masked)  # rules, tags, BM25 and the change type see `urlref`, never a domain name (F1)
        limits = self.cfg.get("limits") or {}
        confident = limits.get("confident_score", 2)
        hits = match_rules(text, self.cfg, project.stage, has_urls=bool(urls), urls=urls) + match_paths(paths, self.cfg)
        selected, suppressed, extra = select_capabilities(text, self.cards, self.cfg, self.hierarchy, hits,
                                                          project.stage, requested, project.stack)

        method = "rules" if any(c.strong for c in selected) else ("tags" if selected else "none")
        best = max((c.score for c in selected), default=0)
        if best < confident:
            have = {c.cid for c in selected} | {s["id"] for s in suppressed}
            # F3 domain agreement: BM25 may only add capabilities from the domains already selected, or, when
            # nothing was selected, from the one domain of its own top hit.
            agreed = {domain_of(c.cid) for c in selected}
            keep = ((lambda cid, _top: domain_of(cid) in agreed) if agreed else
                    (lambda cid, top: domain_of(cid) == domain_of(top)))
            for cid, score in self.bm25.top(text, limits.get("bm25_top_k", 3), limits.get("bm25_min_score", 4.0),
                                            limits.get("bm25_min_ratio", 0.75), keep, limits.get("bm25_min_terms", 1)):
                if cid not in have:
                    selected.append(Candidate(cid, 0, False, [f"bm25 fallback (score {score})"]))
                    method = ("bm25" if method in ("none", "bm25") else
                              method if method.endswith("+bm25") else f"{method}+bm25")

        if not urls:   # MP4 §2.5: url_only capabilities need a URL to work on
            only = set(self.cfg.get("url_only") or [])
            selected = [c for c in selected if c.cid not in only]
        domain_score = {}
        for c in selected:
            domain_score[domain_of(c.cid)] = domain_score.get(domain_of(c.cid), 0) + max(c.score, 1)
        domains = sorted(domain_score, key=lambda d: (-domain_score[d], d))
        change_type, decided_by = classify_change(text, self.cfg.get("change_types") or {}, domains[0] if domains else None)

        # Impact check (spec §15, §19.4): existing-project change work starts from codebase understanding.
        ids = [c.cid for c in selected]
        if (project.stage == "existing" and change_type in extra["existing_change_types"]
                and any(self.cards[c]["requires_codebase_analysis"] for c in ids)):
            for cid in extra["existing_adds"]:
                if cid not in ids:
                    selected.append(Candidate(cid, 0, True, [f"existing project + {change_type}: impact analysis first"]))
                    ids.append(cid)
                    if domain_of(cid) not in domains:
                        domains.append(domain_of(cid))

        deps = dependency_closure(ids, self.cards, project.stack)
        adds = self.cfg.get("change_type_adds") or {}
        if ids and change_type in (adds.get("types") or []):   # MP3 §3.1: completion gate on multi-step changes
            have = set(ids) | {d["id"] for d in deps}
            deps += [{"id": cid, "required_by": f"change type {change_type} (completion gate, MP3 §3.1)"}
                     for cid in adds.get("add") or [] if cid not in have]
        all_ids = set(ids) | {d["id"] for d in deps}
        fallbacks = {c: self.cards[c]["fallback_capability"] for c in ids
                     if self.cards[c]["fallback_capability"] and self.cards[c]["fallback_capability"] not in all_ids}
        # P12: impact analysis runs as a command (graph or §74 fallback) and bounds the code surface.
        impact = None
        if "codebase/impact-analysis" in all_ids and project.stage != "new":
            impact = {"command": "agylite codebase affected" + (" --paths " + " ".join(paths) if paths else ""),
                      "code_files_limit": self.code_limit, "returns": ["files", "tests", "unknown"]}
        # P13: engineering work follows one lifecycle (config/lifecycle.yaml), ordered per change type.
        lifecycle = (steps_for(self.lifecycle, change_type, project.stage, capabilities=ids)
                     if set(domains) & LIFECYCLE_DOMAINS or "design/inspiration-extract" in ids else None)
        pipeline = next((h.pipeline for h in hits if h.pipeline), None) or domains
        # D-049: UI work (design, browser verification or QA routed) is done only after the browser check passes.
        native = any(h.rule == "mobile-native" for h in hits)   # a native app has no web page to check
        browser = ("required" if any(c in all_ids for c in ("testing/browser-verification", "testing/browser-qa"))
                   or (any(domain_of(c) == "design" for c in all_ids) and not native) else "not-needed")
        confidence = ("high" if any(c.strong for c in selected) and best >= confident else
                      "medium" if selected and best >= confident else
                      "low" if selected else "none")
        roles = self.cfg.get("roles") or []
        # F4: an empty selection is said out loud, and the agent falls back to the always-safe principles.
        unmatched = not selected
        # Plan B (IMPLEMENTATION_PLAN §2.1): the first capability's primary skill loads whole; a second one only when
        # the task clearly spans two jobs (strong rule signals in two domains). The rest are index only.
        # "Highest-ranked" is the score; the lifecycle order only breaks ties (security is listed first, not ranked first).
        ranked = sorted(selected, key=lambda c: -c.score)
        whole = [ranked[0].cid] if ranked else []
        if ranked and ranked[0].strong:
            second = next((c.cid for c in ranked[1:] if c.strong and domain_of(c.cid) != domain_of(ranked[0].cid)), None)
            whole += [second] if second else []
        return {
            "schema_version": ROUTE_SCHEMA_VERSION,
            "request": request,
            "urls": urls,
            "change_type": change_type,
            "change_type_keyword": decided_by,
            "project": {"stage": project.stage, "project_id": project.project_id, "phase": project.phase,
                        "stack": list(project.stack)},
            "domains": domains,
            "capabilities": [{"id": c.cid, "score": c.score, "role": role_of(c.cid, roles),
                              "level": self.hierarchy.get(role_of(c.cid, roles)),
                              "context_level": self.cards[c.cid]["context_level"], "reasons": c.reasons}
                             for c in selected],
            "dependencies": deps,
            "fallbacks": fallbacks,
            "impact": impact,
            "lifecycle": lifecycle,
            "browser": browser,
            "verification_mode": self.verification_mode,
            "pipeline": pipeline,
            "suppressed": suppressed,
            "rules": [h.rule for h in hits],
            "method": method,
            "confidence": confidence,
            "unmatched": unmatched,
            "whole_skills": whole,
            "fallback_guidance": list(UNMATCHED_GUIDANCE) if unmatched else [],
            "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        }


def context_order(result):
    """The routed capability ids with the whole-skill ones first (Plan B loads the first `whole` of them whole)."""
    ids = [c["id"] for c in result["capabilities"]]
    whole = [c for c in result.get("whole_skills") or [] if c in ids]
    return whole + [c for c in ids if c not in whole]


def capability_ids(result, include_dependencies=True):
    ids = [c["id"] for c in result["capabilities"]]
    return ids + [d["id"] for d in result["dependencies"]] if include_dependencies else ids
