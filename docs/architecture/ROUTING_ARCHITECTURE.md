# Routing

`agylite route "<request>" [--paths …] [--new|--existing] [--capability id]` returns, as JSON (`--brief` for one line):
change type, domains, capabilities in guidance order, dependencies, fallbacks, the impact step, the lifecycle,
browser policy, verification mode, method and confidence.

## Pipeline (`agylite/routing/router.py`, config `config/routing.yaml`)

1. Mask URLs and bare domains (`stripe.com`, `https://…`) as the placeholder `urlref` and normalize the request;
   the URLs found are returned as `urls` (schema 5, MP1 F1), so a brand-named site never fires a keyword rule.
2. Rules (keywords, `unless` exclusions, project stage) and path rules (`--paths`) → strong candidates.
3. Card intent tags → weak candidates.
4. Suppression ("forbidden pairings"), project stage (new: no codebase; existing: impact analysis first), limits.
5. Declared conflicts resolved by the hierarchy in `config/priorities.yaml`.
6. Dependency closure and fallbacks.
7. BM25 over CARD.md only when nothing scored confidently; such routes report `confidence: low`.

Output fields added later: `impact` (P12) — the `agylite codebase affected` command and the 12-file code surface;
`lifecycle` (P13) — the ordered steps for the change type; `browser: required | not-needed` and
`verification_mode: tests-and-browser` (D-049; was `disabled | exception-requested` under D-035).

## Guarantees

- No model call; p50 0.23 ms, p95 0.34 ms measured over the 22 spec scenarios.
- 22/22 spec scenarios route with every expected capability and no forbidden one (`tests/routing/scenarios.yaml`).
- A routing rule cannot select a disabled capability (validated).
- Every route emits DOMAIN_SELECTED and CAPABILITIES_SELECTED events (the dashboard's input).
