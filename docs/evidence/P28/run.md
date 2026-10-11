# P28 evidence — upstream tracking (2026-10-11)

- `agylite update --check` against GitHub (outside the sandbox; DNS working again): up to date — appllama, beyondseo, karpathy, unlazy; update available — addy, agency, beacon, brag, ecc, graphify, gstack, opendesign, ponytail, taste, uiuxpromax.
- `agylite update taste --latest` (scratch home, bundle `07cd36edb5d9`): "fetched Leonxlnx/taste-skill @ 717446e (13 bundled paths)" → `taste activated ce26fc2 → 717446e · 8 commits` → current `392b5d77ffb9` known-good; mirror `~/.agylite/mirrors/Leonxlnx__taste-skill.git`; diff: 3 added, 5 removed, 1 changed upstream files, none bundled; 1 min 15 s.
- `tests/update/test_track.py` (5, real local git upstreams): check up-to-date → new commit found → latest activated (1 commit, bundled change listed) → second run "none" → another commit fetched incrementally into the same mirror and activated; removing a referenced file → failed with "dangling reference", current unchanged; due/manual/releases (annotated tag) policies; promote rewrites the pin and inventory; LaunchAgent written with `update --latest --due`, Mondays 09:00, removed cleanly; `config/upstreams.yaml` covers all 15 upstreams with their pinned branches.
- Full suite **251 OK, 3 skipped**; doctor and validate pass; workflow YAML parses.

## First real batch (2026-10-11): 11 upstreams, run locally and opened as a pull request
`agylite update --latest` against GitHub, then `--promote`, `bundle fetch`, matrix/notices/cards regenerated, bundle rebuilt from the repository evidence: **`2502140a790a` known-good, 2,648 files, closure 0 open, `debts {}`, `unresolved_placeholders {}`, self-tests pass**; Beacon rules 538/538; 252 tests; benchmark unchanged (≈ 900 vs ≈ 32,000 est. tokens per turn; 83 % less over 22 tasks; routing 22/22).

| Upstream | Commits | Bundled files changed/added | Result |
|---|---:|---:|---|
| taste | 8 | 0 | applied |
| addy | — | 4 | applied |
| agency | — | 22 | applied (after fix 1) |
| beacon | 211 | 77 | applied; one new rule needed the engine port (fix 5) |
| brag | 2 | 1 | applied |
| ecc | 672 | 14 | applied |
| graphify | 195 | 175 | first refused (closure gap: new tests import the excluded skill generator) → rule `tests/test_skill*.py` excluded → applied |
| gstack | 43 | 69 | first refused (rewrite drift; then 3 gaps to gstack docs/tooling) → rewrite accepts the new wording, 3 mentions accepted → applied |
| opendesign | 17 | 0 | applied |
| ponytail | 62 | 6 | applied |
| uiuxpromax | 5 | 5 | applied |

Up to date: appllama, beyondseo, karpathy, unlazy.

### Defects the live run exposed (all fixed, with tests)
1. Later updates in a batch built with earlier-updated upstreams' *old* trees → integrity check refused them. Activated updates now register their tree in `$AGYLITE_HOME/staging-current` (two-upstream test).
2. `git ls-tree -l` in a blobless clone downloaded every blob one by one (Beacon minutes, ECC/Open Design hours) → inventory without sizes; sizes from one GitHub tree API call.
3. Stale CARD.md counts failed an update → warning only (cards regenerated in the same change).
4. Karpathy's license (declared only in `.claude-plugin/plugin.json`) became UNKNOWN because the sparse fetch skipped that file → always fetched.
5. Beacon `2462839` changed `ToolResultText` (skip content-block metadata and base64 media; http(s) tool targets count as outside content) → ported; new gstack placeholders `DESIGN_OUTSIDE_VOICES`, `DESIGN_SHOTGUN_LOOP`, `TEST_VALUE_MESSAGE` → OS text (TRANSFORM_VERSION 5); two new Beacon rules treat MCP as detection data.
6. Bundled-file count tests hard-coded 2,582 → derived from the regenerated extraction summary, so automated updates do not need test edits.
