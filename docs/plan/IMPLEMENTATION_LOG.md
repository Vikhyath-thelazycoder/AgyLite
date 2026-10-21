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

## Phase 1: critical fixes (MP1) — IN PROGRESS on `impl/p1-critical-fixes`

Gate commands run this checkout's code with `PYTHONPATH=. python -m agylite.cli …`: `bin/agylite` execs the
installed engine in `~/.agylite/core`, so it would test the old code. (The Tier 1 AgyLite arm needs the same care:
`--plugin-dir` alone runs the installed engine, not this checkout.)

| Item | State | Commit | Proof |
|---|---|---|---|
| F13 OOD routing set (54 requests) | done | 925d70a | `tests/routing/test_ood.py` (red first: 21 failures) |
| F1 URLs/domains masked (`urls` in route, schema 5) | done | eb3d9d0 | `tests/routing/test_urls.py` |
| F2 over-broad single-word keywords → phrases | done | 5eadb6b | OOD set; audit script output in the commit |
| F3 BM25 domain agreement, stop-words, floor 4.0 / 0.75, ≥ 2 shared terms | done | 913340b | `test_routing.py::test_bm25_needs_domain_signal`, OOD set |
| F4 unmatched routes (`unmatched`, `fallback_guidance`, `ROUTE_UNMATCHED` event) | done | 298685b | `tests/routing/test_unmatched.py` |
| F5 `sources_priority` + `--request` in every entry skill | done | 2459b3e | `tests/context/test_sources_priority.py`, `test_entry_skills.py` |
| F6 removed/moved Taste skills → EXCLUDE SUPERSEDED | done | f0d60f7 | `tests/bundle/test_rules.py`; candidate bundle `68a7954e901a` known-good |
| F7 Taste tracking `manual` | done | 88e907a | `config/upstreams.yaml` |
| F8 Graphify 0.9.93 + Brag secrets rule | **in progress, uncommitted** | — | see below |
| F9 doctor pin age per track, last update run | todo | | |
| F10 README benchmark conditions | todo | | |
| F11 `agylite used` counts only loaded context | todo | | |
| F12 duplicate UI/UX Pro Max file | todo | | |
| F14 invalid upstream-updates workflow (actionlint) | todo | | |
| F15 `UserPromptSubmit` auto-route hook | todo | | |

Known open items carried forward:
- OOD `ood-addy-interview` is `pending: MP3` (needs rule `requirements-grilling`); `ood-research` is
  `pending_forbid: MP5` (weak `database` tag until the research domain exists). Both markers are strict.
- The installed engine (`~/.agylite`, bundle `2502140a790a`) is untouched. All bundle work so far is in the temporary
  engine home `<scratchpad>/home-f6` (bundles `68a7954e901a` → `5b079d678640` → `8b6e64123863`).

### F8 state at the stop (2026-10-21)

- In the temporary home, `agylite update graphify b90b9df…` and `agylite update brag 069432c…` (with `--source` trees
  from `git archive` of the clones, `--self-test`) both **activated**; `runtime install graphify` → `graphify 0.9.93
  ready`. One rule change was needed: `tests/test_code_only_update_all_hosts.py` imports the excluded
  `tools/skillgen` → EXCLUDE (same reason as D-046's `test_skill*.py`).
- `update --promote` wrote the new pins into `docs/audit/evidence/`, and the matrix, docs, notices and cards were
  regenerated (uncommitted in the working tree).
- **Suspicious, not committed:** the promoted `upstream-file-hashes/brag.tsv` has 1,235 rows with repeated blob hashes
  (the clone tracks 369 files; the old inventory had 371 rows), so `extraction-summary.json` shows Brag EXCLUDE
  57 → 921 files. Graphify's inventory looks right (1,085 rows vs 1,083 tracked files). The likely cause is the
  inventory taken from a `--source` directory instead of `git ls-tree`. Do not commit F8 until this is understood.

## RESUME FROM

**Phase 1 · F8 · step "verify the promoted Brag inventory".**
1. `git diff docs/audit/evidence/upstream-file-hashes/brag.tsv` and compare with `git -C ~/Developer/os/brag
   ls-tree -r HEAD`; find why `inventory_from_dir` (agylite/update/core.py) produced duplicate rows. Fix the cause
   (test first) or regenerate the inventory from `git ls-tree`, then re-run `update --promote` in the temporary home.
2. Re-run the regenerators (`tools/audit/extraction_matrix.py`, `render_matrix_docs.py`, `python -m
   agylite.bundle.notices`, `registry cards`, `registry build`), run the suite, commit F8.
3. Continue with F9 → F10 → F11 → F12 → F14 → F15, then the Phase 1 gate (tests, doctor, validate, benchmark
   --compare, actionlint, the F15 acceptance re-run of two pilot cells), then activate the green bundle in
   `~/.agylite` and start Phase 2.
