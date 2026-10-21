"""Registry schema (spec §13, §23A.13).

Cards (`capabilities/<domain>/<sub>/card.yaml`) author the judgement fields; the generator derives identity and
every provenance fact (sources, commit, license, size) so no fact is stored twice (§13 "one source of truth").
"""
import re

# Spec §13 metadata, in spec order. Every generated registry entry carries all of them.
SPEC_FIELDS = (
    "capability_id", "name", "domain", "subdomain", "description", "intent_tags", "source_repositories",
    "source_paths", "version", "commit_sha", "license", "integration_type", "runtime_type", "host_compatibility",
    "dependencies", "requires_network", "requires_browser", "requires_codebase_analysis", "context_level", "priority",
    "security_class", "token_cost_estimate", "cache_strategy", "activation_conditions", "verification_requirements",
    "related_capabilities", "conflicts", "fallback_capability", "enabled",
)
# Filled by agylite/registry/generate.py from the card path and bundle provenance; never written in a card.
GENERATED_FIELDS = ("capability_id", "domain", "subdomain", "source_repositories", "source_paths", "version",
                    "commit_sha", "license", "integration_type", "token_cost_estimate")
# sources_priority (MP1 F5): bundle-path globs, the capability's primary source first; validated against the bundle.
EXTRA_FIELDS = ("origin", "web_qa_class", "web_qa_modes", "runtime_status", "sources_priority")
AUTHORED_FIELDS = tuple(f for f in SPEC_FIELDS if f not in GENERATED_FIELDS) + EXTRA_FIELDS

ORIGINS = {"bundled", "os-native", "mixed"}
RUNTIMES = {"none", "node", "python-stdlib", "python-isolated", "python-uv", "playwright-optional", "os-native"}
NETWORK = (False, True, "local-only", "optional")
BROWSER = {"none", "fallback", "required-for-output"}
CONTEXT_LEVELS = {"L1", "L2", "L3"}
SECURITY_CLASSES = {"read-only", "local-exec", "network", "privileged"}
CACHE_STRATEGIES = {"static", "project", "run", "none"}
ACTIVATION_MODES = {"on-demand", "explicit", "stack-detected", "internal", "fallback"}
# D-035 local test-first: browser/visual verification has no FALLBACK class any more; it is DISABLED_BY_POLICY.
WEB_QA_CLASSES = {"CORE", "OPTIONAL", "DISABLED_BY_POLICY"}
RUNTIME_STATUSES = {"ACTIVE", "DISABLED_BY_POLICY"}
# Only these domains may declare a browser need, and only for their own output (SEO capture, media rendering) —
# never as verification (D-035). Every other domain is requires_browser: none.
BROWSER_SCOPED_DOMAINS = {"seo", "media", "design"}   # design: MP4 + IMPLEMENTATION_PLAN §2.2 (designlang reads sites; Taste inspect)
HOST_STATUSES = {"NOT_VERIFIED", "FILES_PRESENT", "RUNTIME_VERIFIED", "UNSUPPORTED"}
ID = re.compile(r"^[a-z][a-z0-9-]*/[a-z][a-z0-9-]*$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _str_list(value, non_empty=False):
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value) and (value or not non_empty)


def _network_ok(value):
    return any(value is v if isinstance(v, bool) else value == v for v in NETWORK)


def validate_card(cid, card, ids):
    """Problems with one merged card (defaults applied); `ids` is the set of all capability ids."""
    p = []
    domain = cid.split("/", 1)[0]
    authored = [f for f in GENERATED_FIELDS if f in card]
    if authored:
        p.append(f"{cid}: {authored} are generated and must not be authored")
    unknown = sorted(set(card) - set(AUTHORED_FIELDS) - set(GENERATED_FIELDS))
    if unknown:
        p.append(f"{cid}: unknown fields {unknown}")
    missing = [f for f in AUTHORED_FIELDS if f not in EXTRA_FIELDS[1:] and f not in card]
    if missing:
        return p + [f"{cid}: missing fields {missing}"]
    checks = (
        ("name", isinstance(card["name"], str) and card["name"]),
        ("description", isinstance(card["description"], str) and card["description"]),
        ("intent_tags", _str_list(card["intent_tags"])),
        ("origin", card["origin"] in ORIGINS),
        ("runtime_type", card["runtime_type"] in RUNTIMES),
        ("requires_network", _network_ok(card["requires_network"])),
        ("requires_browser", card["requires_browser"] in BROWSER),
        ("requires_codebase_analysis", isinstance(card["requires_codebase_analysis"], bool)),
        ("context_level", card["context_level"] in CONTEXT_LEVELS),
        ("priority", type(card["priority"]) is int and 1 <= card["priority"] <= 100),
        ("security_class", card["security_class"] in SECURITY_CLASSES),
        ("cache_strategy", card["cache_strategy"] in CACHE_STRATEGIES),
        ("verification_requirements", _str_list(card["verification_requirements"], non_empty=True)),
        ("enabled", isinstance(card["enabled"], bool)),
    )
    p += [f"{cid}: invalid {field}: {card.get(field)!r}" for field, ok in checks if not ok]

    prio = card.get("sources_priority")
    if prio is not None and not (_str_list(prio, non_empty=True) and all(g.startswith("files/") for g in prio)):
        p.append(f"{cid}: sources_priority must be a non-empty list of bundle path globs (files/…)")

    act = card["activation_conditions"]
    if not isinstance(act, dict) or act.get("mode") not in ACTIVATION_MODES or not _str_list(act.get("when"), True):
        p.append(f"{cid}: activation_conditions needs mode in {sorted(ACTIVATION_MODES)} and a non-empty `when` list")

    for field in ("dependencies", "related_capabilities", "conflicts"):
        refs = card[field]
        if not isinstance(refs, list):
            p.append(f"{cid}: {field} must be a list")
            continue
        for ref in refs:
            if ref == cid:
                p.append(f"{cid}: {field} references itself")
            elif ref not in ids:
                p.append(f"{cid}: {field} references unknown capability {ref}")
    fb = card["fallback_capability"]
    if fb is not None and (fb not in ids or fb == cid):
        p.append(f"{cid}: fallback_capability must be another known capability or null, got {fb!r}")

    hosts = card["host_compatibility"]
    if not isinstance(hosts, dict) or not hosts or any(
            not isinstance(h, dict) or h.get("status") not in HOST_STATUSES for h in hosts.values()):
        p.append(f"{cid}: host_compatibility must map each host to a status in {sorted(HOST_STATUSES)}")

    # §23A.13: every testing capability records its web-QA class; other domains do not.
    if domain == "testing":
        if card.get("web_qa_class") not in WEB_QA_CLASSES:
            p.append(f"{cid}: testing capability needs web_qa_class in {sorted(WEB_QA_CLASSES)}")
    elif "web_qa_class" in card or "web_qa_modes" in card:
        p.append(f"{cid}: web QA classes are only recorded for testing capabilities")
    modes = card.get("web_qa_modes")
    if modes is not None and (not isinstance(modes, dict) or any(v not in WEB_QA_CLASSES for v in modes.values())):
        p.append(f"{cid}: web_qa_modes values must be in {sorted(WEB_QA_CLASSES)}")

    # D-035: browser use is scoped to SEO/media output; a disabled-by-policy capability can never be enabled.
    status = card.get("runtime_status", "ACTIVE")
    if status not in RUNTIME_STATUSES:
        p.append(f"{cid}: runtime_status must be in {sorted(RUNTIME_STATUSES)}")
    if status == "DISABLED_BY_POLICY" and card["enabled"]:
        p.append(f"{cid}: runtime_status DISABLED_BY_POLICY requires enabled: false")
    if card["requires_browser"] != "none" and domain not in BROWSER_SCOPED_DOMAINS:
        p.append(f"{cid}: requires_browser must be none outside {sorted(BROWSER_SCOPED_DOMAINS)} (local test-first, D-035)")

    # Declared needs must agree with the security class.
    if card["requires_network"] is True and card["security_class"] in ("read-only", "local-exec"):
        p.append(f"{cid}: requires_network=true needs security_class network or privileged")
    if card["runtime_type"] != "none" and card["security_class"] == "read-only":
        p.append(f"{cid}: runtime {card['runtime_type']} executes code; security_class cannot be read-only")
    return p


def validate_cards(cards):
    ids = set(cards)
    problems = []
    for cid, card in cards.items():
        if not ID.match(cid):
            problems.append(f"{cid}: capability id must be <domain>/<subdomain> in lower-kebab-case")
        problems += validate_card(cid, card, ids)
    for cid, card in cards.items():
        for other in card.get("conflicts") or []:
            if other in cards and cid not in (cards[other].get("conflicts") or []):
                problems.append(f"{cid}: conflict with {other} is not declared on both cards")
    return problems


def validate_registry(registry, upstream_names=()):
    """Problems with a generated registry: complete §13 fields, provenance-consistent origins, domain-first ids."""
    p = []
    caps = registry.get("capabilities") or {}
    if not caps:
        return ["registry has no capabilities"]
    upstream = {n.lower() for n in upstream_names} | {n.split("/")[-1].lower() for n in upstream_names}
    for cid, entry in caps.items():
        missing = [f for f in SPEC_FIELDS if f not in entry]
        if missing:
            p.append(f"{cid}: missing §13 fields {missing}")
            continue
        if entry["capability_id"] != cid or cid != f"{entry['domain']}/{entry['subdomain']}":
            p.append(f"{cid}: inconsistent capability_id/domain/subdomain")
        if upstream & set(cid.split("/")):
            p.append(f"{cid}: capability ids are domain-first; upstream repository names belong to provenance only")
        own = entry["token_cost_estimate"]["bundled_files"]
        shared = sum(caps[d]["token_cost_estimate"]["bundled_files"] for d in entry["dependencies"] if d in caps)
        if entry["origin"] == "os-native" and own:
            p.append(f"{cid}: os-native capability must not own bundled files ({own} found)")
        if entry["origin"] != "os-native" and own == 0 and shared == 0:
            p.append(f"{cid}: {entry['origin']} capability has no bundled source (own or via dependencies)")
        if own and not (entry["source_repositories"] and entry["commit_sha"] and entry["license"]):
            p.append(f"{cid}: bundled capability without source/commit/license provenance")
        for repo, sha in entry["commit_sha"].items():
            if not SHA1.match(str(sha)):
                p.append(f"{cid}: commit for {repo} is not a 40-hex SHA")
    return p
