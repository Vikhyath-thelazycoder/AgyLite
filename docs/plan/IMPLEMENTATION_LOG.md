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
