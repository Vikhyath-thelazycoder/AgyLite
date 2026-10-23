# AgyLite upgrade: implementation log

Driver: `IMPLEMENTATION_PLAN.md` of 2026-10-21 (copies in `/Users/vikhyathmgowda007/Developer/os/` and this
checkout's untracked `new/`; the two are byte-identical). The plan wins over the master prompts where they differ.

## Step 1: what was read (2026-10-21)

1. `IMPLEMENTATION_PLAN.md` (driver; §2 overrides: Plan B whole-skill routing, browser verification ON via CLI, gstack
   full, autonomous spending)
2. `README.md` (owner decisions; never re-opened)
3. `AUDIT_REPORT.md` (bugs §3, pilot §9, Plan A vs B §10)
4. `REPO_COMPARISON.md`
5. `MASTER_PROMPT_1_CRITICAL_FIXES.md` … `MASTER_PROMPT_6_UPSTREAM_UPDATES.md`, in order
6. In this checkout: `CLAUDE.md`, `AGENTS.md`, every file in `docs/architecture/`, `docs/audit/21_AUDIT_DECISIONS.md`

Working checkout: `/Users/vikhyathmgowda007/Developer/vikhyath-ai-engineering-os` (origin
`Vikhyath-thelazycoder/AgyLite`, same commit as `/Users/vikhyathmgowda007/Developer/os/AgyLite`). Upstream clones are
used from `/Users/vikhyathmgowda007/Developer/os/<name>`.

## Step 2: what was already done

| Check | Result |
|---|---|
| `git log --oneline -1` | `6e55166` (v2.1.6), the plan's ground-truth commit |
| `UserPromptSubmit` in `hooks/hooks.json` | absent |
| `sources_priority` in `capabilities/**/card.yaml` | absent |
| `agylite/benchmark/quality/` | absent |
| `docs/plan/PARITY_LEDGER.md` | absent |

No master prompt has been implemented. **Start at Phase 0.**

## Phase 0: setup

| Tool | Version / state |
|---|---|
| git | 2.54.0 |
| python3 / engine python (`~/.agylite/core/bin/python`) | 3.14.7 / 3.14.7 |
| node / npm | v22.14.0 / 10.9.2 (Taste needs ≥ 22: OK) |
| bun | **missing**; installed in Phase 7 after reading gstack's README and setup script |
| claude | 2.1.302 (Claude Code) |
| Chrome | Google Chrome 156.0.8078.47 (`/Applications/Google Chrome.app`) |
| gh | **missing** (research/code reports it; other channels unaffected) |
| actionlint | not on PATH; `actionlint-py` 1.7.12.25 in a scratch venv for F14 |
| yt-dlp | missing; installed by the research runtime (MP5) |
| uv, brew | present |

**`claude -p` probe** (`claude -p "Reply with just: ok" --setting-sources project,local --output-format json
--max-turns 1`, fresh dir outside git): `terminal_reason: completed`, model `claude-opus-5-5`, $0.061, 3.2 s.
Tier 1 runs on this Mac.

**Upstream clones** (all at the plan's §3 commits, verified with `git rev-parse HEAD`):

| Folder | Commit |
|---|---|
| ECC | 90606c8315ee09cafc303515c5f33024db6b9882 |
| agent-skills | aeac41d4d005999432bb7312f7ff06383a91d59d |
| agency-agents | 4e3ac3ca6604c75113f52c695dbddcc7af928b46 |
| andrej-karpathy-skills | 2c606141936f1eeef17fa3043a72095b4765b9c2 |
| gstack | b616d6c53dd8fc0d8db210444b44a131b553b83e |
| unlazy | 16671491f6679ad9378f52604d3bc2415b4120c7 |
| ponytail | 09c434ab73ca43761c5d8b0c5d341926c2fba710 |
| graphify (v8) | b90b9df7949bd04a15b40a1624af85d0a9cfdf04 |
| open-design | 3b0df90f305c8279e748c292accf336d02b924ef |
| taste-skill | 6010f91a9935f1c167dfc500fb1a475681892e6b |
| ui-ux-pro-max-skill | 56ea9cf174ed86786187daa9de0e6247cb0747e4 |
| brag | 069432cac935ed1895859df201c31436c07fb74e |
| skills (Pocock) | 5beb35b040e3de97e54fa9e386d7e42d15c295c2 |
| design-extract | 86bdbb53379d4c1f37ce407f706678c95181ea42 |
| archify | 25cf37080fc8b1dbe758a4efc3935b55f3327083 |
| youtube-agent-skill | a2feb2104981a375ffd4f87ee04f4f5344ac43c6 |
| Agent-Reach | 94f06c1969dfc1834001269d79d3ad0972d9dee6 |

### Phase 0 gate (baseline, before any change)

```
PYTHONPATH=. python -m unittest discover -s tests   → Ran 262 tests in 22.2s — OK (skipped=3)
bin/agylite doctor                                  → 52 passed, 0 failed, 1 warning
bin/agylite validate                                → 23 passed, 0 failed
bin/agylite benchmark --compare                     → 26/26 routing; OLD ≈ 373,016 · NEW ≈ 210,841 (43% less);
                                                      route p50 0.23 ms · p95 0.45 ms
actionlint .github/workflows/*.yml                  → upstream-updates.yml:25:25 context "runner" is not allowed here
```

Phase 0 is green (the known gaps are recorded above). Next: Phase 1 (MP1 F1–F15) on `impl/p1-critical-fixes`.

## Phase 1: critical fixes (MP1) — DONE on `impl/p1-critical-fixes` (2026-10-21)

Gate commands run this checkout's code (`PYTHONPATH=. python -m agylite.cli …`): `bin/agylite` execs the installed
engine in `~/.agylite/core`. Risky engine work ran in a temporary engine home first; the green result was then
installed into `~/.agylite` with `scripts/install` (bundle `5cb3ec9b15bc`, Graphify 0.9.93 ready).

### MP1 report

| Item | Commit | Test that proves it | Notes |
|---|---|---|---|
| F13 OOD routing set (54 requests) | 925d70a | `tests/routing/test_ood.py` | red first (21 failures). Strict markers: `ood-addy-interview` pending MP3, `ood-research` pending_forbid MP5 |
| F1 URLs/domains masked, `urls` in route (schema 5) | eb3d9d0 | `tests/routing/test_urls.py` | `stripe.com` no longer selects security/backend; "Add Stripe checkout" still does |
| F2 over-broad single words → phrases | 5eadb6b | OOD set | audit script output in the commit message |
| F3 BM25 domain agreement, stop-words, floor 4.0 / 0.75, ≥ 2 shared terms | 913340b | `test_routing.py::test_bm25_needs_domain_signal` | the ≥ 2-terms floor goes beyond MP1 (every remaining false hit shared one word) |
| F4 unmatched routes | 298685b | `tests/routing/test_unmatched.py` | `ROUTE_UNMATCHED` event: keywords + hash, never the text |
| F5 `sources_priority` + `--request` everywhere | 2459b3e | `test_sources_priority.py`, `test_entry_skills.py` | completion → Unlazy first; visual-quality → Taste first |
| F6 removed/moved Taste skills → SUPERSEDED | f0d60f7 | `tests/bundle/test_rules.py` | every affected capability keeps a source |
| F7 Taste tracking manual | 88e907a | config | MP4 switches back |
| F8 Graphify 0.9.93 + Brag secrets rule | a1efa57 | `TestInventoryFromDir` | found and fixed a symlink bug in `update --source` inventories (Brag) |
| F9 pin age per track + last update run | da02b06, d40bfff | `tests/unit/test_doctor_pins.py`, `test_check_records_when_a_pin_was_found_current` | `--promote` still leaves `head_date` stale (MP6) |
| F10 README benchmark conditions | 7c7c576 | — (docs) | `RESULTS.md` regenerated; `QUALITY.md` stub |
| F11 `used` counts loaded context only | 77b73a9 | `TestUsedReport`, `TestDiagnosticsWriteNoRouteEvents` | |
| F12 duplicate UI/UX Pro Max file | f578f33 | `TestSkillOwnedCopies` | **deviation:** not excluded — each skill links its own copy; plan §2.1 (whole skills) wins; doctor now tells per-skill copies from accidental duplicates |
| F14 invalid upstream-updates workflow | 6ed7aad | `tests/structural/test_workflows.py` | actionlint clean; **owner action:** one manual `check` dispatch on GitHub after merge to `main` |
| F15 auto-route every prompt (D-048) | e6d9e7c | `tests/hosts/test_prompt_hook.py` | latency p50 112 ms, p95 113 ms (100 runs, incl. Python start-up) |

### Phase 1 gate (candidate engine home, then installed)

```
unittest discover -s tests     → Ran 300 tests — OK (skipped=3)
agylite doctor                 → 60 passed, 0 failed, 1 warning (weekly pins beyondseo, unlazy 18 days > 14)
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → 26/26 routing; OLD ≈ 360,338 · NEW ≈ 210,409 (42% less); route p95 0.60 ms
actionlint .github/workflows/*.yml → no findings
installed engine (~/.agylite)  → bundle 5cb3ec9b15bc known-good + intact; registry valid; doctor 0 failed
                                 (2 warnings: actionlint not on PATH; the installed copy has no git history, so pins
                                 date from the 2026-10-03 capture)
```

MP1 definition-of-done routes (`--brief`):
- stripe.com/linear.app → `design/design-system, design/design-direction` (no security/backend)
- mind map of this repo → UNMATCHED (diagrams arrive in MP5)
- grill me → `engineering/implementation, engineering/planning` (no media/local-verification)
- summarise this YouTube video → UNMATCHED (research arrives in MP5)
- write a YouTube script → still the new-product engineering set (YouTube domain arrives in MP5)

### F15 acceptance (paid, AgyLite arm only, Opus 5.5, `--setting-sources project,local --plugin-dir <checkout>`)

| Cell | Pilot (before MP1) | Now | Evidence |
|---|---|---|---|
| Addy TDD eval 2 (Addy's grader) | 2/3 | **3/3** (failing test first, fair split, full suite) | $0.19, 7 turns, 27 s |
| Ponytail vibe-todo (Ponytail's `run.py` scorer) | 198 source lines | **151 source lines**, correct | $0.20, 3 turns, 33 s (no skill 208, Ponytail 65 in the pilot) |
| Route injected | 0 `agylite` calls | `PROMPT_ROUTED` in both sessions (686 / 694 est. tokens injected) | AgyLite event log; stream-json shows only SessionStart hook output |
| `agylite` Bash calls | 0 | 0 | the agent used the injected route and cards but did not load L2 context itself |

This is not a quality-parity claim (n = 1, one arm). The remaining gap (the agent does not load the skill itself) is
what Phase 3 addresses: whole-skill loading, with the hook telling the agent to run `agylite skill load <primary>`.

## Phase 2: quality benchmarks (MP2) — DONE (built) on `impl/p2-benchmarks` (2026-10-21); baselines partial

### MP2 report

| Item | Commit | Test that proves it | Notes |
|---|---|---|---|
| Tier 0 (T0.1 routing OOD, T0.2 context selection, T0.3 fidelity, T0.4 tokens, T0.5 self-tests) | 2ba2c4d | `tests/benchmark/test_quality.py` | baseline `docs/benchmarks/quality-baseline-2026-10-21-tier0.json` |
| Tier 1 harness (three arms, pilot isolation, `init` event checked, frozen plugin snapshot) | 2ba2c4d, 8703773 | `TestIsolation`, `TestDryRunAndSpend` | each suite uses the upstream's own instrument |
| Suites: eng-addy, eng-ponytail, eng-pocock, design-taste, diagram-archify | 2ba2c4d, 04ed767, 41d09f3 | `TestSuiteSchema` | credits, license and full SHA per suite |
| Parity ledger (`docs/plan/parity-ledger.json` → generated `PARITY_LEDGER.md`) | 41d09f3 | `TestLedger` | every run appends a row |
| Usage-limit stop + `--resume` | e3bb448, 35db7b3, c1db1da | `TestUsageLimit` | a limit reply stops the run (no grading); resume reruns only missing cells; c1db1da fixed a false positive (an agent answer about HTTP 429) |

**Tier 1 baselines (n = 1, Opus 5.5).** Paid sessions were run under the master prompt's spending rule until the
owner withdrew it on 2026-10-21 (≈ $7.30 of usage). No paid session runs from now on unless the owner asks.

| Suite | Metric: no skill / original / AgyLite | Verdict | Cost no skill / original / AgyLite |
|---|---|---|---|
| eng-ponytail | src_loc 45.4 / 19.6 / 42.6 (retained 0.11) | INCONCLUSIVE (noise at n = 1) | $1.21 / $0.92 / $1.14 |
| eng-addy | expectations_passed 0.903 / 1.0 / 0.958 (retained 0.57); 1 original-arm cell ungraded | INCONCLUSIVE | $0.74 / $1.02 / $0.95 |
| eng-pocock | 9/30 cells | not measured | — |
| design-taste, diagram-archify | — | not measured | — |
| design-extract, youtube, browser-qa, research, routing | instruments arrive in Phases 5–7 | not measured | — |

The baseline finding that matters: in every AgyLite session the hook routed the prompt (`PROMPT_ROUTED`) but the
agent loaded no context (`context_loaded` 0). Plan B (Phase 3) and MP3 (Phase 4) address this.

### Phase 2 gate (this checkout's code)

```
unittest discover -s tests     → Ran 317 tests — OK (skipped=3)
agylite doctor                 → 59 passed, 0 failed, 2 warnings (actionlint not on PATH; weekly pins beyondseo/unlazy 18 days > 14)
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → 26/26 routing; OLD ≈ 360,338 · NEW ≈ 210,383 (42% less); route p95 0.45 ms
benchmark --quality --tier 0   → PASS; tokens +0.0% vs the Tier 0 baseline; fidelity review 35%, visual-quality 16% (Plan B fixes)
```

## Phase 3: Plan B conversion (IMPLEMENTATION_PLAN §2.1) — DONE on `impl/p3-plan-b` (2026-10-21)

| Item | Commit | Test that proves it |
|---|---|---|
| Whole primary skills at L2 (no section picking, no truncation), skill files listed for on-demand reading; `L2.primary_skill: whole`, `max_whole_skills_per_task: 2`, `max_tokens_per_task: 40000` | ddafa70 | `tests/context/test_whole_skill.py` |
| `agylite skill load <upstream>/<name>`; the prompt hook names it | ddafa70 | `TestSkillLoadCommand`, `test_prompt_hook.py` |
| `catalog.json` (every SKILL.md of every pinned upstream; translations/host ports skipped; policy-flagged skills listed, never fetched) + `agylite skills search/get` | ddafa70 | `tests/catalog/test_catalog.py` ("SwiftUI" → `ecc/swiftui-patterns`, never `docs/ja-JP/`) |
| Token report per message (L0 + hook) and per task; "(96% more)" instead of "(-96% less)" | df22d31 | `test_diagnostics.py` |

Real bundle (temporary engine home): catalog 828 skills, 749 copies skipped, 0 missing, 69 policy-flagged; gstack
`ship` (≈ 9.9K tokens) and `investigate` (≈ 4.4K) load whole. Gate: 332 tests OK, doctor 58/0, validate 23/0,
routing 26/26, Tier 0 PASS with fidelity 100% for every primary.

## Phase 4: engineering best of the best (MP3) — DONE on `impl/p4-engineering` (2026-10-22)

### MP3 report

| Item | Commit | Test that proves it | Notes |
|---|---|---|---|
| §1.1 upstream `pocock` (mattpocock/skills@5beb35b, 2026-10-19, 191 files, weekly) | 8865c59 | `test_security` (16 pins) | inventory + scan via `tools/audit/scan_upstream.py` |
| §1.2 extraction rules (ADAPT 13, COPY 19; 0 open closure gaps) | 8865c59, 0adb751 | extraction matrix | bundle paths keep `skills/` (`files/pocock/skills/…`), as §1.2 allows |
| §1.3 mechanics-only rewrites: tracker → living plan, Skill tool → `agylite skill load pocock/<name>`, research → `agylite skills get`, no `disable-model-invocation` | 8865c59 | `TestPocockRewrites` (no shortening; drift fails the build) | **deviation:** tdd, code-review, handoff are ADAPT (one mechanics line each); Plan B's `skill load` instead of `context --file` |
| §1.3 `plan add-task --depends` repeatable | 8865c59 | `test_add_task_takes_several_blockers` | |
| §1.4 rules requirements-grilling, spec-tickets, diagnose, architecture-deepening + 4 scenarios; OOD `pending: MP3` removed | 0adb751 | `test_scenarios`, `test_ood` | also fixed: the highest-*ranked* capability loads whole (was: first listed), so "Diagnose why the checkout test is flaky" loads diagnosing-bugs, not security |
| §2.1 GENERATED decision; `files/ponytail/RULESET-lite.md` from `getPonytailInstructions('lite')` | 71ce26f | `TestGeneratedRuleset` | untrusted JS: no codegen from strings, empty env, 10 s, ≤ 8 KB text; inputs `ponytail-config.js` and `skills/ponytail/SKILL.md` hash-checked; 2,916 chars |
| §2.2 ruleset always on in L0 (`ponytail_ruleset: lite|off`), never truncated; doctor line | e19d9db | `tests/context/test_discipline.py` | L0 ≈ 307 → ≈ 1,089 tokens (+782 per session); stays under 1,500, so the budget was not raised |
| §2.3 `ponytail-review` → engineering/review (first), gstack review second; `agylite-review` follows its structure | 377d87b | `TestReviewSkill` | simplicity stays explicit-only, lowest priority |
| §3.1 completion gate added to every NEW_FEATURE/FEATURE_CHANGE/BUG_FIX/REFACTOR/SECURITY/PERFORMANCE route (dependency) | 3c8d00f | `test_multi_step_changes_add_completion` | MIGRATION_CHANGE is not a change type; 8 scenario expectations updated |
| §3.2 installer enables Unlazy's Stop hook; prints what changed; doctor line | 9c2b47b | `tests/runtimes/test_unlazy_hook.py` (temp HOME) | not run on this machine (the installed engine is untouched) |
| §3.3 completion → Unlazy first; Taste `output-skill` EXCLUDE SUPERSEDED | (MP1) | T0.2 | confirmed |
| §4 `sources_priority` for every engineering/testing capability; T0.2 lists every first file; Agency never ahead of a non-Agency source | 97ad182, 4642657 | Tier 0 T0.2 (24/24) | **deviation:** Addy documentation-and-adrs moved to engineering/documentation (a file has one capability) |
| §5 ECC skills added after the pin classified | f635ff5 | — | not in the pinned inventory yet |
| §6.4 token baseline | 6a56c47 | `test_p25` | every-turn NEW 3,677 B → 6,805 B |
| §6.6 Tier 1 `eng-simplicity-review`, `eng-core` | — | — | **not run**: the owner withdrew paid sessions on 2026-10-21 |

### Phase 4 gate (temporary engine home `home-p4`, bundle `52e8c1108c39`, 2,737 files)

```
unittest discover -s tests     → Ran 357 tests — OK (skipped=3)
agylite doctor                 → 59 passed, 0 failed, 4 warnings (Unlazy Stop hook disabled in the temp home; actionlint
                                 not on PATH; graphify not installed in the temp home; weekly pins beyondseo/unlazy 19 days)
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → 30/30 routing; per message: L0 ≈ 1,089, hook p50 ≈ 521 / max ≈ 791 tokens;
                                 tasks OLD ≈ 70,905 · NEW ≈ 153,011 (116% more: whole skills)
benchmark --quality --tier 0   → PASS; OOD 54/54; Addy triggers 42/82 (51%); T0.2 24/24; Agency first-two: none;
                                 fidelity 100% for all 23 primaries; self-tests unlazy/uiuxpromax exit 0
```

MP3 §6.3 sign-off commands:
```
$ agylite route "Grill me on this plan before I build it" --brief
PLAN_CHANGE · high (rules) · engineering/planning, engineering/implementation + deps: engineering/stack-packs
$ agylite context --request "Grill me on this plan" engineering/planning | grep '^### files/'
### files/pocock/skills/productivity/grilling/SKILL.md — grilling (skill pocock/grilling, whole)
$ agylite context --request "Review this diff" engineering/review | grep '^### files/'
### files/ponytail/skills/ponytail-review/SKILL.md — ponytail-review (skill ponytail/ponytail-review, whole)
$ agylite context --request "Fix the flaky checkout test" engineering/debugging | grep '^### files/'
### files/pocock/skills/engineering/diagnosing-bugs/SKILL.md — diagnosing-bugs (skill pocock/diagnosing-bugs, whole)
$ agylite bootstrap --host claude-code | tail -30
… "## The smallest complete change" … "## Levels" … "| **lite** | Build what was asked. …" …
Full principles (Karpathy): `agylite context engineering/principles`.
```

Still not the same / open:
- Addy's own trigger prompts route to the right skill 42/82 times (51%); the goal is ≥ 95% (Phase 9).
- No Tier 1 numbers after MP3 (paid sessions are off); eng-addy and eng-ponytail baselines stay INCONCLUSIVE at n = 1.
- The installed engine in `~/.agylite` still runs v2.1.6 + MP1; installing this bundle (and the Unlazy hook) is
  the owner's step: `scripts/install` from this checkout.

MP3 §7 proposals for the owner (not implemented): Karpathy's four principles in L0 too (≈ 400 tokens); Ponytail
`full` as an opt-in level once measured; Pocock `triage` when an external tracker is used; trim ECC to stack packs,
AI systems and release patterns (≈ 60 files of overlap).

## MP3 Tier 1 measurement (paid, owner-approved 2026-10-22)

38 new sessions ($5.95 + grader calls), Opus 5.5, n = 1, AgyLite arm = `main` after MP3 with bundle `52e8c1108c39`.
The no-skill and original arms were reused from the MP2 runs (`--reuse-from`, unchanged configurations); cells MP2
never reached were run now. Rows are in `PARITY_LEDGER.md`.

| Suite | Metric | No skill | Original | AgyLite before MP3 | AgyLite after MP3 | Retained | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| eng-ponytail | source lines (lower better) | 45.4 | 19.6 | 42.6 | **23.0** | 0.87 | INCONCLUSIVE (near, n = 1) |
| eng-ponytail | vibe-todo lines | 207 | 49 | 166 | **68** | — | — |
| eng-ponytail | safe | 6/7 | 7/7 | 7/7 | 7/7 | 1.0 | — |
| eng-addy | expectations passed | 0.903 | 1.0 | 0.958 | **0.903** | 0.0 | INCONCLUSIVE |
| eng-pocock | expectations passed | 0.47 | 0.745 | (not run) | **0.572** | 0.37 | INCONCLUSIVE |

Cost per arm (whole suite): Ponytail $1.21 / $0.92 / $1.16; Addy $0.74 / $1.06 / $0.96; Pocock $1.23 / $1.73 / $1.54
(no skill / original / AgyLite).

Diagnosis (IMPLEMENTATION_PLAN §6 checklist): (1) the route arrived in every AgyLite session (`PROMPT_ROUTED`);
(2) **the agent never loaded the skill** — 0 `agylite skill load` calls in all 37 AgyLite sessions, despite the hook's
"Before the first edit, load the whole skill" line. Ponytail improved because its rules are in L0 and need no load;
Addy and Pocock depend on the agent loading the skill, and it does not (Addy TDD pressure case: fixed first, test
after; Addy code review: no severity labels; Pocock to-spec/to-tickets: no spec structure). Pocock tdd#1 (AgyLite)
was ungraded (invalid grader reply). Note: Pocock's own tdd skill scored below no skill on both tdd cases (0.2, 0.0
vs 0.6, 1.0).

Next fix (Phase 9 round 1, needs a code change): deliver the primary skill's text in the prompt hook instead of only
naming the load command (within a budget), then re-run the AgyLite arm only.

## Phase 5: design best of the best (MP4) — code DONE on `impl/p5-design` (2026-10-22); parity not yet same

### MP4 report

| Item | Commit | Test that proves it | Notes |
|---|---|---|---|
| §1 Taste v2.1 (pin 6010f91), `agylite design taste draw/lint/inspect/scenes/assets/status`, bundle self-test, `sources_priority` | 2830226 | Tier 0 self-test `taste: exit 0` | Taste leads design direction and visual quality |
| §2.2–2.4 designlang upstream, `design/inspiration-extract`, `agylite design extract` (1-3 URLs → one DESIGN.md, brand colour shifted 24°, MERGE_NOTES.md, never replaces without `--replace`), `agylite runtime install designlang`, `design_check_overrides` | 6c7512f, 06254b8 | `tests/design/test_extract.py` | |
| §2.5 routing rule `design-inspiration` (`requires_urls`), `url_only` | f0ecfc0 | routing scenarios | |
| §3.3 style/markup changes add design check + Taste lint + inspect; NOT_RUN = BLOCKED | bfd1003 | verify tests | policy on for design only (the rest is Phase 7) |
| §3.2 INSPIRATION lifecycle step + BLOCKING question `design-md-approved` | a9c8ea2 | `tests/design/test_inspiration_flow.py` | |
| §3.1, §4 design entry skill (paths A/B, precedence), `docs/architecture/DESIGN_MD.md` | 10e1885, 676d9a2 | `test_sections_match_designlangs_formatter` | |
| §6 real run (network): `runtime install designlang`, `design extract https://linear.app https://vercel.com` | 1248801 | `TestFuseScript` (fails without the fix) | 27 s; 8 sections; stops for approval. Fixed: breakpoints printed `[object Object]px` (designlang 13.3.2 formatter bug), duplicate radius labels collapsed YAML keys (4 of 6 radii kept), summary printed `spacing base: None` |
| §6 `design-extract` suite (free) | d1ca77c | `TestDesignExtractSuite` | was planned but missing; built and run |

### Phase 5 gate (temporary engine home `home-p5`, bundle `22bf70be985e`)

```
unittest discover -s tests     → Ran 391 tests — OK (skipped=3)
agylite doctor                 → 59 passed, 0 failed, 4 warnings (Unlazy Stop hook disabled in the temp home; actionlint
                                 not on PATH; graphify not installed in the temp home; weekly pins beyondseo/unlazy 19 days)
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → routing 33/33; route p95 0.46 ms; L1+L2 p95 48 ms
benchmark --quality --tier 0   → PASS (self-tests unlazy, uiuxpromax, taste exit 0); NEW ≈ 187,169 est. tokens / 33 scenarios
```

### MP4 Tier 1 measurement (2026-10-22, Opus 5.5, n = 1)

`design-extract` (free, 6 extractions): every site **same** on every metric. stripe.com colour ✓ font ✓, linear.app
colour ✗ font ✓ (designlang misses #5e6ad2 in both arms), gov.uk ✓ ✓; DESIGN.md 8/8 sections in both arms. The pooled
colour verdict reads inconclusive only because site-to-site spread counts as run noise.

`design-taste` (paid, 9 sessions + blind judge, **$12.94**: $1.87 / $8.02 / $3.05 no skill / original / AgyLite):

| Eval | Inspector FAIL (no skill / original / AgyLite) | Lint FAIL | Judge overall | What the AgyLite agent did |
|---|---|---|---|---|
| 1 landing page | 13 / 0 / **0** | 25 / 0 / **0** | 6.5 / 6.85 / **7.45** | `skill load taste/design-taste-frontend`, taste draw, assets, lint, inspect → **same** |
| 2 restaurant site | 7 / 0 / **5** | 9 / 0 / **7** | 6.5 / 7.5 / **6.3** | no skill load, no lint/inspect → regressed |
| 7 app screen | 2 / 0 / **2** | 1 / 0 / **0** | 6.5 / 7.5 / **6.5** | loaded `addy/incremental-implementation` (wrong skill) → regressed |

Suite: REGRESSED (inspector retained 0.68; lint 0.80 and judge 0.32 inconclusive). Diagnosis: when Taste is routed and
loaded, AgyLite matches or beats the original (eval 1). Two causes for the rest: (1) **routing** — "Make a one-page
website…" routes to design/frontend only (no design/design-direction, so Taste is never named), and "Build the main
screen of … app" routes PLAN_CHANGE with engineering/implementation first (eval 1 itself routed TESTING_CHANGE but kept
design-direction); (2) **skill loading** — the agent loads the skill only sometimes (the MP3 open fix).

Fix (owner, 2026-10-22: right after this benchmark): route page/site/screen builds to design/design-direction first,
deliver the primary skill's text in the prompt hook, then re-run the AgyLite arm only with `--reuse-from` this run.

### MP4 re-measure after the fixes (2026-10-22, AgyLite arm only, `--reuse-from`, Opus 5.5, n = 1)

Fixes 7e6fad9 (page/site/screen builds route to Taste first) and cff519f (the prompt hook carries the whole primary
skill, the MP3 open fix). The no-skill and original arms are reused from the earlier runs.

| Suite | Before | After | Cost (AgyLite arm) | What the traces show |
|---|---|---|---|---|
| design-taste | REGRESSED: inspector 0.68, judge 0.32 | inspector **0.955 same**, lint 1, judge **0.919** (inconclusive at n = 1) | $7.45 | every eval routes to Taste first and gets it whole; the 10.7k-token hook output is long enough that Claude Code saves it to a file and the agent reads it with `sed` |
| eng-pocock | 0.372 retained | **0.709** (near) | $1.61 | Pocock skills delivered whole; grilling/to-spec cells still score 0.2–0.5; one to-tickets prompt routed to gstack/ship |
| eng-addy | 0 (= no skill) | **0** (= no skill) | $0.96 | the skill text arrives (1.9–3.1k tokens per prompt), but Addy's TDD, debugging and review tasks route to the MP3 primaries `pocock/tdd`, `pocock/diagnosing-bugs` and `ponytail/ponytail-review`, so Addy's own skill never loads — a design choice (one best primary per capability), not a loading bug |

Carried into Phase 9 (owner decision needed): per-upstream parity vs one best primary per capability. With one primary,
the suite of every upstream that is not the primary for its task can never reach "same" — Addy here, and any later
overlap. Options: route by upstream on the upstream's own trigger phrases, load two primaries for overlapping tasks, or
accept the chosen primary and measure the capability instead of the upstream.

## Phase 6: new domains (MP5: research, YouTube, diagrams) — code DONE on `impl/p6-new-domains` (2026-10-22)

### MP5 report

| Item | Test that proves it | Notes |
|---|---|---|
| §1.3/§2.2/§3.2 upstreams `agentreach` (Panniantong/Agent-Reach@94f06c1), `ytagent` (Jakeschincariol/youtube-agent-skill@a2feb21), `archify` (tt-a1i/archify@25cf370): pins, hashes, scans, licenses, notices, rules, tracking (monthly / monthly / weekly, self-tests) | `test_security` (20 pins), extraction matrix 0 open gaps | Deviation: the YouTube upstream key is `ytagent`, not `youtube` (the domain is `youtube`; capability ids never carry upstream names) |
| §1.4 domain `research` (web, social, video, code, synthesis); Agylite-authored `GUIDE.md` per channel (< 1,000 tokens), loaded as skills `agylite/research-<x>` (new card field `guide`, schema + registry checks); synthesis = Pocock `research` (now bundled) | `test_registry`, Tier 0 T0.2 | `research/web` is `mixed` (it owns the Agent-Reach LICENSE + constraints.txt) |
| §1.2 research runtime: Agent-Reach at the audited commit (`--no-deps`) + constraints.txt; `agylite research read/rss/video/video-search/channel/github/x/reddit/doctor/enable/disable`; Jina guard; secrets in Keychain (stdin, never argv) or 0600 file | `tests/research/test_research.py` (20) | twitter-cli and rdt-cli read browser cookies on their own when credentials are missing/stale: both are installed without `browser-cookie3`, children get a private empty HOME (deleted) and a PATH without `uv`; yt-dlp `--no-cookies-from-browser --ignore-config` |
| §2.3 domain `youtube` (script, packaging, repurpose, analytics, channel-ops, seo); `agylite youtube hookscore/title/deadair/chapters/retention/swipe`, `voice init/status`; rewrites (voice path, tools, `/yt-x`, transcripts via research, no whisper) | `tests/youtube/test_youtube.py` (golden outputs), bundle self-test | `research channel --swipe collected.json` feeds `youtube swipe` (yt-viral's input format) |
| §3 `engineering/diagrams` + `agylite diagram` (Archify CLI from the bundle, update check off, credentials stripped); rewrites (commands, explainers on demand only, Agylite owns updates) | `tests/diagram/test_archify.py`, self-test validates 24 examples | Deviation: all JSON examples kept (Archify's doctor/compare/guide read them), only the 12 MB rendered pages excluded |
| Owner decision 2026-10-22: Archify's headless Chrome **browser-check runs on every diagram whenever Chrome is present** (`BROWSER_SCOPED_CAPABILITIES`, `config/verification.yaml` `diagram_verification` + `scoped_browser_use`, the verify guard's one scoped gate); without Chrome finalize runs validate → deliver → check and `verify --diagram` records browser-check BLOCKED | `TestVerifyGate`, real run: finalize + browser-check PASS at 1440/1600/1920/2048 | |
| §1.5/§2.4/§3.3 routing: `RESEARCH_CHANGE`, `YOUTUBE_CHANGE`, rules (research, research-report, research-lookup, research-social, research-video, research-youtube, yt-*, diagram, diagram-kinds, diagram-repo), new `url_hosts` rule condition; diagrams are `DOCUMENTATION_CHANGE` | 16 MP5 scenarios + OOD set 55/55 | Deviations: bare `channel`, `thumbnail`, `retention`, `subscribers`, `timestamps`, `timeline`, `find out`, `look up` count only next to a video / web / diagram word (they also name app features); "Edit this footage…" → `youtube/repurpose` (edit decision list, no rendering), media keeps launch videos |
| Entry skills `agylite-research`, `agylite-youtube`, `agylite-diagrams`; adapters rendered; Agent Office seats Scout and Creator; L0 ≈ 1,126 tokens (budget 1,500) | adapters render, `test_dashboard` | |

### Phase 6 gate (temporary engine home `home-p6`, bundle `8880741f98e6`, 2,994 files, fetched over the network)

```
unittest discover -s tests     → Ran 435 tests — OK (skipped=3)
agylite doctor                 → 62 passed, 0 failed, 4 warnings
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → routing 48/48; route p95 0.62 ms; L1+L2 p95 98 ms
benchmark --quality --tier 0   → PASS (OOD 55/55; self-tests unlazy, uiuxpromax, taste, youtube, archify exit 0)
```

Sign-off (real network): `runtime install research` 13 s; `research doctor`; `research read` via Jina and `--direct`;
`rss` (hnrss); `video --meta/--subs/--comments` ("Me at the zoo"); `video-search`; `channel --swipe` × 2 → `youtube
swipe`; `youtube voice init` (twice, idempotent); `youtube hookscore`; `diagram validate` and `finalize` with
browser-check; `verify --diagram` PASSED with receipts as artefacts. `github` not run: `gh` is not installed here.

### MP5 Tier 1 measurement (2026-10-22, Opus 5.5, n = 1, 36 sessions, ≈ $16)

New suites e5789e8: `youtube` (three yt-script tasks; the HOOK line scored by youtube-agent-skill's own hookscore.py;
on-screen beats) and `research` (four fetch tasks with checkable answers; functional, not a parity claim).

| Suite | Verdict | Metrics (no skill / original / AgyLite) | Cost (no skill / original / AgyLite) | Reading |
|---|---|---|---|---|
| research | **same** | success 1 / 1 / 1 (page, RSS, YouTube transcript, GitHub) | ≈ $0.46 / $0.42 / $0.51 | all pass; the transcript task is too famous (plain Claude may answer from memory) |
| youtube | regressed | hook_verdict 38 / 66.3 / 52 (retained 0.49); on_screen_beats 0.33 / 1 / 1 (same) | $0.50 / $1.20 / $1.01 | AgyLite routes to yt-script, gets it whole and runs hookscore twice like the original; the gap is which hook lands on the HOOK line — likely n = 1 noise, the harness cannot tell at n = 1 |
| diagram-archify | inconclusive | first-pass usable 0.2 / 0.2 / 0.2 (same); semantic 0.2 / 0.4 / 0.4 (retained 1); validation 0.4 / 1 / 1 (retained 1) | $2.05 / $2.93 / $2.77 | AgyLite equals the original on every metric; "inconclusive" is only the n = 1 noise rule |

Errors: none (36/36 cells valid). Carried into Phase 9: youtube and diagram-archify at n = 3; a less-known video for
research; X/Reddit once the owner enables them.

### Owner decision (2026-10-22): overlapping skills load both primaries (option 2)

When a task matches skills of more than one upstream (Addy and Pocock both have TDD, debugging and review skills), the
prompt hook loads both whole, one marked as leading, within a token limit — instead of one primary per capability
(which keeps Addy's own suite at no-skill). Rejected: routing by each upstream's trigger wording (option 1; ambiguous
for real requests) and measuring capabilities instead of upstreams (option 3; gives up per-upstream parity).
Implement in Phase 9, then re-run the AgyLite arm of eng-addy and eng-pocock with `--reuse-from`.

### MP5 sign-off

Code e5789e8 + 153a317 on `main`; gate green (435 tests, doctor 62/0, validate 23/0, routing 48/48, Tier 0 PASS); paid
suites run once (research same, youtube regressed at n = 1, diagram-archify equal to the original). **Phase 6 exit
criteria met. Stopped for the owner's go-ahead on MP6.**

## Phase 8: update workflow (MP6: review → benchmark → the owner approves) — DONE on `impl/p8-update-workflow` (2026-10-22)

### MP6 report

| Item | Test that proves it | Notes |
|---|---|---|
| §1 `agylite update --review [--repo X…] [--due] [--track …] [--to SHA] [--out DIR] [--tier1-plan]`: non-merge commits from the blobless mirror, per-commit classes (BREAKING, PRIMARY, BUNDLED, NEW_SKILL, NEW_UNCLASSIFIED, POLICY, SECURITY, IRRELEVANT) + conventional type, section-level diffs with token deltas (unified diff for PRIMARY, > 200 lines to `.diff`), runtime versions + changelog, candidate built and checked with `update(activate=False)`, Tier 0 on the candidate vs current, Tier 1 plan (never run), verdicts, proposals (rename / delete / new skill via BM25 top 3 → REFERENCE / unclassified / rewrite drift with the failing pattern), `REPORT.md` + `report.json` + `<repo>-proposed-rules.patch` | `tests/update/test_review.py` (14, real temp git upstream) | POLICY counts what would reach the bundle (a bundled MCP/hook file, a new bundled installer, MCP config or telemetry newly added to bundled code/config, a license change) plus any new MCP config file; prose that mentions telemetry is not POLICY |
| §2 `--approve REPO[@SHA] [--review DIR]` (refuses unreviewed, HOLD/NEEDS_RULES and stale reviews; decision in `updates/decisions.jsonl`), `--reject REPO@SHA --reason`, `--pending`; `--latest` = `--review --due` with the approval note; `track.latest()` builds candidates only unless `activate=True`; L0 line `updates: N reviewed upstream update(s) awaiting approval` from local files only | `test_review`, `test_track.test_latest_never_activates_by_default` | a candidate is built against the other upstreams' current pins, so approving one makes the others stale (re-review) |
| §3 entry skill `agylite-update-review`, capability `observability/updates` (guide), routing rule `upstream-updates` → OBSERVABILITY_CHANGE | scenario `mp6-review-updates` | |
| §4 CI: review → approve only ADOPT / SECURITY_FAST_TRACK in the runner's throwaway home (one upstream at a time) → promote → PR labelled `needs-owner-approval` with REPORT.md as body (merge = the owner's approval), review folder as an artifact | actionlint clean | Actions history: the workflow runs now (scheduled run 2026-10-22 succeeded after MP1 F14) |
| §5 all 20 upstreams tracked; `releases` (designlang): a pin newer than the newest tag reads UP_TO_DATE | `test_real_policy_file_covers_every_upstream` | |
| Found and fixed: `fetch_commit` skipped generator inputs (Ponytail's `hooks/ponytail-config.js`, so every Ponytail update failed); `gc` would delete the designlang and research runtimes; `--bundle` for Tier 1 (the AgyLite arm runs a candidate) | real review | |

### Phase 8 gate (temporary engine home `home-p6`, bundle `8880741f98e6`)

```
unittest discover -s tests     → Ran 450 tests — OK (skipped=3)
agylite doctor                 → 64 passed, 0 failed, 3 warnings
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → routing 49/49
benchmark --quality --tier 0   → PASS
```

### Sign-off: real `agylite update --review --due --tier1-plan` (2026-10-22; `current` 8880741f98e6 before and after)

| Upstream | Commits | Verdict | Why |
|---|---:|---|---|
| agency | 57 | SECURITY_FAST_TRACK | 6 security commits; candidate 3587f53c87c0, Tier 0 PASS |
| beacon | 294 | SECURITY_FAST_TRACK | 70 security-worded commits (detection rules); 1 new skill proposed as REFERENCE |
| ecc | 171 | SECURITY_FAST_TRACK | 1 security commit; a PRIMARY file changed (no Tier 1 suite measures it yet) |
| graphify | 35 | SECURITY_FAST_TRACK | 6 security commits; candidate builds, self-tests pass |
| opendesign | 68 | SECURITY_FAST_TRACK | 1 security commit; 1 new skill proposed as REFERENCE |
| uiuxpromax | 7 | SECURITY_FAST_TRACK | 1 security commit |
| ponytail | 44 | SECURITY_FAST_TRACK | a PRIMARY file changed: Tier 1 (eng-ponytail) recommended |
| addy | 14 | ADOPT_AFTER_TIER1 | 2 PRIMARY commits; Tier 1 plan eng-pocock + eng-addy |
| gstack | 91 | NEEDS_RULES | the `review/SKILL.md` QA rewrite no longer matches upstream (pattern shown in the report) |
| 11 others | 0 | UP_TO_DATE | designlang: the pin is newer than its newest release tag |

Nothing was approved: the owner approves (`agylite update --pending` lists 8 approvable candidates).

## Phase 7: browser verification (IMPLEMENTATION_PLAN §2.2, D-049) — DONE on `impl/p7-browser` (2026-10-23)

Owner decisions (2026-10-22): gstack telemetry **off**; install gstack **with its optional global hooks skipped**.

| Item | Test that proves it | Notes |
|---|---|---|
| Policy `tests-and-browser` (D-049 supersedes D-035; D-035's text unchanged): `config/verification.yaml` `browser_verification`, only `simulator_recording_loop` disabled; policy, validate, state, schema (any domain may need a browser), router (`browser: required \| not-needed`, schema 6), engine evidence mode, dashboard seat, entry skills and docs | updated tests (registry, project, dashboard, routing `s23a-*`/`vp-*`, verify, integration) in the same change | the domain transform no longer appends "browser verification is disabled" to browser steps (closer to upstream text) |
| `testing/browser-verification` (enabled, CORE): Addy `browser-testing-with-devtools` ADAPT — MCP setup → `agylite verify --browser` + the `chrome-devtools` CLI of chrome-devtools-mcp@1.12.0 (`--isolated --headless --usageStatistics=false`), every MCP tool mapped, Security Boundaries verbatim; ECC click-path-audit, e2e-testing, browser-qa, e2e-runner; Agency evidence-collector + reality-checker | `test_each_rewrite_applies` | chrome-devtools sends Google usage statistics by default: always off |
| `testing/browser-qa` → gstack `/qa` (rule `browser-qa`: QA, test the site, click through) | scenarios | deviation: a separate capability (the plan put gstack under browser-verification, whose primary is Addy) |
| Browser runtime `agylite runtime install browser` (Playwright 1.64.0 + Chromium, throwaway context per viewport) and `agylite verify --browser [--url] [--flows]` / `agylite browser-check`: serves index.html or starts preview/dev/start, screenshots 1440/768/390, console + page errors, failed same-origin requests, overflow at 390 px, images without alt, flows (plain steps; scripts refused), evidence + report.json with sha256; automatic for style/markup changes; BLOCKED without the runtime | `tests/browser/test_browser.py` (7) | the old "verify may not start a browser" guard is gone |
| §4.1 fixtures: `broken-site` FAILS with all 5 planted defects (+ the 404's console line); `fixed-site` PASSES with 3 screenshots and matching hashes; CI `browser` job (actionlint clean) | `TestFixtureSites` | |
| gstack full: `agylite runtime install gstack` — Bun 1.4.4 (Homebrew), `~/.claude/skills/gstack` at the pinned 5cb5e1c, `gstack-config set telemetry off` + `update_check false`, `./setup --host claude --no-plan-tune-hooks --no-timeline-stop-hook`; `~/.claude/settings.json` **unchanged** (diffed) | real install | gstack ships ~60 skills into `~/.claude/skills/` (incl. setup-browser-cookies, scrape, setup-gbrain, which registers MCP if the owner runs it); "outside reviews" (Codex passes in /review and /ship) left at gstack's default |
| gstack `/qa` on `broken-site` (real session, $1.39): found and fixed all 5 planted defects (missing alt reported inside the 404-image defect), re-verified, health 86 → 100 | session transcript | Aside not installed → gstack's own headless browser |

### Phase 7 gate (temporary engine home `home-p6`, bundle `aead351f7a0e`, built from a fresh fetch)

```
unittest discover -s tests     → Ran 455 tests — OK (skipped=3)
agylite doctor                 → 64 passed, 0 failed, 3 warnings
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → routing 49/49
benchmark --quality --tier 0   → PASS
```

## Owner-approved upstream updates (2026-10-23)

The owner approved the 7 SECURITY_FAST_TRACK upstreams of the 2026-10-22 review. Each was re-reviewed against the
Phase 7 rules and approved one at a time (`agylite update --review --repo X` → `--approve X`): uiuxpromax 67803ea →
28327f2 (9 commits), ponytail 9b58c1f → 09c434a (44), graphify b90b9df → c588b72 (35), opendesign 17e2559 → e03d5c2
(68), agency f99f6aa → 4e3ac3c (57), beacon 2462839 → cfbd7b1 (298), ecc 2d515e4 → 90606c8 (171; the first attempt
hit a transient `git ls-remote` failure and was retried). Then `agylite update --promote`, rescans (from shallow
clones; the blobless staging made the scanner fetch every blob), extraction matrix, matrix docs, notices and cards.

- Ponytail's `hooks/ponytail-instructions.js` now requires `./ponytail-config`: both are generator inputs read at
  build time (RULESET-lite.md ships, neither file does) → accepted gap.
- `tools/audit/render_matrix_docs.py` had a hand-written license table without the MP4/MP5 upstreams; it now falls
  back to `third_party/licenses.json`.

Gate: bundle 1bcd9beb5094 known-good, self-tests unlazy/uiuxpromax/taste/youtube/archify exit 0; 455 tests OK; doctor
64/0; validate 23/0; Tier 0 PASS; routing 49/49. Not applied: addy (ADOPT_AFTER_TIER1, waits for its Tier 1 run),
gstack (NEEDS_RULES: review/SKILL.md rewrite drift).

## Phase 9: parity loop — code DONE on `impl/p9-parity-loop` (2026-10-23)

| Item | Test that proves it | Notes |
|---|---|---|
| Option 2 (owner 2026-10-22, D-050): `skill_overlaps` in config/priorities.yaml (Pocock tdd / diagnosing-bugs / to-spec / to-tickets / grilling, Ponytail review / ponytail ↔ their Addy counterparts); the hook carries both whole, lead first and named (`prompt_hook.overlap_skill_max_tokens` 6,000) | `test_prompt_hook` (overlap, reversed side, partner over budget) | eng-addy's 6 prompts now get Addy's skill next to the lead; before, never |
| Diagnosis item 3 (traces): rule `skill:` + route `skill_hints` (schema 7); rules `to-spec`, `to-tickets`, `code-review`, `tdd`; `release` ignores "in release 2.3.0" | `TestSkillHints`, OOD +4 (59/59) | before: to-spec → grilling, to-tickets → Addy docs, "review the diff that adds…" → implementation, "fix it test-first" unmatched, "slower in release 2.3.0" → gstack/ship |
| `agylite validate` checks overlap and hint paths against the bundle | `test_overlap_and_rule_skill_paths_must_be_bundled` | |
| gstack review rewrite (MP6 NEEDS_RULES): the D-035 text ("never open a browser") contradicted D-049 and drifted; now only the anchor line points at gstack's own install, upstream text verbatim; `qa/sections/exploratory.md` accepted gap (GSTACK_INSTALL) | `test_gstack_review_qa_points_at_gstacks_install_in_both_upstream_wordings` | re-review 5cb5e1c → b04cc35: SECURITY_FAST_TRACK, candidate c12a18c20c27, Tier 0 PASS — **not approved** (owner) |
| Found: the bundle id ignores transform code, so an edited rewrite reused the old bundle text; TRANSFORM_VERSION 6 → 7 and a test pins the transform sources' hash to the version | `TestTransformVersion` | |
| Found: the browser fixtures' `.agylite/flows.yaml` were never committed (`.gitignore` `.agylite/`), so Phase 7's fixture tests failed on a clean checkout | `test_browser` | |
| research `youtube-transcript` task: a little-known video (EI4rvzpTDj8, ~44k views; 110 °F at 1:07, Minnesota at 2:21) instead of "Me at the zoo" | grader accepts the transcript answer, rejects a guess | |
| addy re-review 1be8e34 → aeac41d: ADOPT_AFTER_TIER1, candidate fdf51ff600ac, Tier 0 PASS | — | the eng-addy original arm already runs aeac41d, so the AgyLite arm on this candidate is the like-for-like run |

### Phase 9 gate (engine home `home-p9`, bundle 70c7149c3e1b, self-tests unlazy/uiuxpromax/taste/youtube/archify exit 0)

```
unittest discover -s tests     → Ran 465 tests — OK (skipped=10)
agylite doctor                 → 64 passed, 0 failed, 3 warnings
agylite validate               → 23 passed, 0 failed
agylite benchmark --compare    → routing 49/49
benchmark --quality --tier 0   → PASS (OOD 59/59)
```

### gstack update applied (owner approval 2026-10-23)

`agylite update --approve gstack@b04cc35` (SECURITY_FAST_TRACK, 97 commits, 5 security fixes) → `--promote` → rescan
(fresh shallow clone at b04cc35), extraction matrix (closure: 0 open), matrix docs, notices, cards.

- Found while rebuilding from the repo pins: a build from a **full** gstack clone rendered `plan-design-review` and
  `design-consultation` with gstack's Codex "outside voices" and design-daemon board, while the update's sparse fetch
  (and every earlier bundle) had Agylite's replacements. Cause: the template renderer learned placeholder expansions
  from every staged template, including the excluded `design-review`. Fix: only bundled templates teach expansions;
  TRANSFORM_VERSION 8. Proof: the same pins built from the full clone and from the sparse fetch are byte-identical
  (6c8821eb00b7), and equal to the approved candidate c12a18c20c27.

Gate (bundle 6c8821eb00b7): 466 tests OK (skipped=3); doctor 64/0; validate 23/0; routing 49/49; Tier 0 PASS (OOD 59/59).

## Phase 9 paid run — resume (stopped 2026-10-23 on the owner's request)

Owner go-ahead 2026-10-23: every suite, all three arms, n = 3, in chunks (chunk 1 = eng-ponytail, eng-addy,
eng-pocock; then two chunks of 3–4 suites; ask before each chunk). Also built for it: the `browser-qa` suite
(9279259). AgyLite arm on candidate **3509e18d39d9** (= 6c8821eb00b7 + addy aeac41d, only 7 addy files differ, Tier 0
PASS). Original arms: ponytail 09c434a, pocock 5beb35b, addy aeac41d (= the pins).

| Suite | Done | Cost | Run dir (also copied to `~/.agylite/benchmarks/quality/`) |
|---|---|---:|---|
| eng-ponytail | 63/63 | $9.40 | `/private/tmp/claude-501/-Users-vikhyathmgowda007-Developer-vikhyath-ai-engineering-os/0c1adb4b-e048-41d1-aeab-df61d6096ee7/scratchpad/home-p9/benchmarks/quality/20261023T160330Z-eng-ponytail` |
| eng-addy | 54/54 run, AgyLite 4/18 valid | $8.42 | `/private/tmp/claude-501/-Users-vikhyathmgowda007-Developer-vikhyath-ai-engineering-os/0c1adb4b-e048-41d1-aeab-df61d6096ee7/scratchpad/home-p9/benchmarks/quality/20261023T163255Z-eng-addy` |
| eng-pocock | 16/90, AgyLite 0/5 valid, paused | $2.40 | `/private/tmp/claude-501/-Users-vikhyathmgowda007-Developer-vikhyath-ai-engineering-os/0c1adb4b-e048-41d1-aeab-df61d6096ee7/scratchpad/home-p9/benchmarks/quality/20261023T193809Z-eng-pocock` |

2026-10-24: the resume ran with `~/.agylite/core/bin` on PATH, so the plugin launcher ran the installed v2.1.6 engine
in every AgyLite session it started (C1-1 in IMPLEMENTATION_PLAN "Paid-run findings"). eng-pocock was paused at 16/90.
Before resuming, take `~/.agylite/core/bin` off PATH (`export PATH=$(echo "$PATH" | tr : '\n' | grep -v
'.agylite/core/bin' | paste -sd: -)`), then re-run the invalid AgyLite cells. eng-addy reported no skill 0.931 ·
original 1 · AgyLite 0.986 (14 of 18 AgyLite cells on the old engine). Cost: baseline $2.35, original $2.95, AgyLite $3.12.

eng-ponytail (n = 3): correct 0.905 / 1 / 1 and safe 0.857 / 1 / 1 (retained 1); source lines 55 / 21.5 / 23 (0.955);
wrote tests 0.952 / 0.952 / 1; **cost $0.156 / $0.129 / $0.163 per task — AgyLite costs more than no skill**. Verdict
"inconclusive" only by the noise rule. Next fix to look at: the prompt hook's per-prompt tokens (cards + whole skill).

Resume (engine home and checkout: this session's scratchpad `home-p9` and `wt-p9`, both in /tmp — if a reboot cleared
them, clone a new engine home from `~/.agylite` staging/mirrors, rebuild the bundle from `main`, re-run
`agylite update --review --repo addy` for a new candidate, and start eng-addy from the copy in ~/.agylite):

```bash
export AGYLITE_HOME=/private/tmp/claude-501/-Users-vikhyathmgowda007-Developer-vikhyath-ai-engineering-os/0c1adb4b-e048-41d1-aeab-df61d6096ee7/scratchpad/home-p9
cd <checkout at main with .staging>   # wt-p9: /private/tmp/claude-501/-Users-vikhyathmgowda007-Developer-vikhyath-ai-engineering-os/0c1adb4b-e048-41d1-aeab-df61d6096ee7/scratchpad/wt-p9
B=$AGYLITE_HOME/bundles/3509e18d39d9
# chunk 1b: eng-addy (dry-run checked: 42 sessions planned, 12 reused)
PYTHONPATH=. python -m agylite.cli benchmark --quality --tier 1 --suite eng-addy --runs 3 --bundle $B --yes-spend \
  --resume $AGYLITE_HOME/benchmarks/quality/20261023T163255Z-eng-addy
# chunk 1c: eng-pocock (90 sessions)
PYTHONPATH=. python -m agylite.cli benchmark --quality --tier 1 --suite eng-pocock --runs 3 --bundle $B --yes-spend
# chunk 2 (ask first; update the gstack install to b04cc35 before browser-qa): research, youtube, browser-qa, design-extract
# chunk 3 (ask first): diagram-archify, design-taste
```

## RESUME FROM

<!-- p7-progress:start -->
**NOW: the Phase 9 full paid run, stopped on the owner's request (usage running out) after 76 sessions. Continue it
when the owner says "continue the paid test" — exact commands in "Phase 9 paid run — resume" below. The progress
checklist is in IMPLEMENTATION_PLAN.md → "Resume here".**
<!-- p7-progress:end -->

How to work (any phase):
1. Read `/Users/vikhyathmgowda007/Developer/os/MASTER_PROMPT_4_DESIGN_BEST_OF_BEST.md` and IMPLEMENTATION_PLAN §2.2.
2. Branch `impl/p5-design` from `main`; work in a worktree; build bundles in a temporary `AGYLITE_HOME` (copy
   `staging/` and `mirrors/` from the last temp home with `cp -cR` so only new upstreams are downloaded).
3. Gate per phase: `PYTHONPATH=. python -m unittest discover -s tests`, `agylite doctor`, `agylite validate`,
   `agylite benchmark --compare`, `agylite benchmark --quality --tier 0` (run the checkout's code with
   `PYTHONPATH=<checkout> python -m agylite.cli …`; `bin/agylite` runs the installed engine).
4. **No paid Tier 1 sessions** (`claude -p`) unless the owner asks again; report those suites as not measured.
5. After MP4: report, update this log and this section, push, stop for approval.
6. **Open fix (owner asked not to forget it):** the agent never loads the skill (see "MP3 Tier 1 measurement").
   Deliver the primary skill's text in the prompt hook instead of only naming `agylite skill load`, then re-measure
   the AgyLite arm. MP4/MP5 skills depend on it too, so fix it early (before or at the start of Phase 9).
7. Paid Tier 1 runs: at the end of every master prompt (owner rule 2026-10-22) — run its suites, record results and
   errors, fix them now or carry them into the next phases in the plan files. MP4: design-taste (+ design-extract).
8. **After MP6 (owner request):** run all tests incl. every paid Tier 1 suite, then build a results website showing,
   per task, the output of plain Claude, the original skill and AgyLite side by side (code, grader checks, answer,
   score, cost). Do not build it before MP6 is finished. Measure a new AgyLite build with
   `--arms agylite --reuse-from <earlier run dir>` (only the AgyLite arm is paid again).
