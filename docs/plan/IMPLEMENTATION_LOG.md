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

## RESUME FROM

**Phase 2 (MP2 quality benchmarks), step 1: build `agylite/benchmark/quality/`** on branch `impl/p2-benchmarks`
(from `impl/p1-critical-fixes`).
1. Tier 0 suites T0.1–T0.5, `agylite benchmark --quality --tier 0`, baseline file.
2. Tier 1 harness with the pilot's isolation (`--setting-sources project,local`, AgyLite arm via `--plugin-dir`, a fresh
   workspace outside git, `AGYLITE_HOME` = a per-run home with `bundles/current` linked and no `core`, so
   `bin/agylite` runs the checkout's code). Suites per IMPLEMENTATION_PLAN §5.
3. Record the Tier 1 baseline (n = 1) in `docs/benchmarks/quality-baseline-<date>.json`; start the parity ledger.
