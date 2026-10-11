# Vikhyath AI Engineering OS v2 — Implementation Plan (living document)

| Field | Value |
|---|---|
| Branch | `feat/v2-os-transformation` (from `main` @ `d77834e`, v1.0.1) |
| Spec | Vikhyath AI Engineering OS Master Build Spec (Updated) |
| Total phases | **28 (P0–P27)** |
| Execution model | Phases are grouped into **8 milestones (M0–M7)** (D-007). Within a milestone, every phase is still tested, verified, committed and updated in this plan. Work stops for user review **only at the end of each milestone**. |
| Hard gate | Spec §64 gate **passed** at the end of M1 (D-025). File-level tasks for P4–P27 are in [FILE_LEVEL_PLAN.md](FILE_LEVEL_PLAN.md); deviations found while building are recorded there as "As built" notes and in the decisions log. |
| Decisions | [docs/audit/21_AUDIT_DECISIONS.md](../audit/21_AUDIT_DECISIONS.md) |
| Amendments | **A-1 (2026-10-05)**: Appllama selective merge (D-034) + local test-first verification, browser/Chrome/screenshot verification disabled by policy (D-035, D-036). Audit: [22](../audit/22_APPLLAMA_AND_VERIFICATION_POLICY_AUDIT.md). Every phase re-evaluated below ("Amendment A-1 — phase reconciliation"). |
| Verification policy | `config/verification.yaml`: **LOCAL TEST-FIRST** for every phase, project and host. Chrome DevTools, browser visual verification and screenshot verification are not part of any phase's verification method. |

Status vocabulary (spec §25): NOT_STARTED · PLANNED · IN_PROGRESS · PARTIALLY_COMPLETE · BLOCKED · READY_FOR_VERIFICATION · VERIFIED · COMPLETED · INTENTIONALLY_DEFERRED

## Milestones (review stops)

| Milestone | Phases | Status |
|---|---|---|
| M0 Baseline | P0 | **COMPLETED** |
| M1 Audit & final plan | P1, P2, P3 (ends at the spec §64 hard gate) | **COMPLETED** (gate passed, D-025) |
| M2 Foundation & bundle | P4, P5, P6, P7 | **COMPLETED** (reviewed; user started M3 on 2026-10-04) |
| M3 The brain | P8, P9, P10, P11, P18 | **COMPLETED** (accepted; user started M4 on 2026-10-10) |
| A-1 Amendment | P0–P3, P5–P8, P10, P11, P18 (built phases amended); P12–P27 plans updated | **COMPLETED** (2026-10-05; accepted with M3) |
| M4 Main domains | P12, P13, P14, P15 | **COMPLETED** (2026-10-10; accepted, user started M5) |
| M5 Specialist domains | P16, P17 | **COMPLETED** (2026-10-10; accepted, user started M6) |
| M6 Hosts | P19, P20, P21, P22 | **COMPLETED** (2026-10-11; accepted) |
| M7 Dashboard & ship | P23, P24, P25, P26, P27 | **COMPLETED** (2026-10-11; awaiting user review and release go-ahead) |

## Phase index

| Phase | Name | Stage | Depends on | Status |
|---|---|---|---|---|
| P0 | Current repository audit | Audit | — | **COMPLETED** |
| P1 | Upstream deep audit (14 repos) | Audit | P0 | **COMPLETED** |
| P2 | Capability, domain & extraction architecture | Audit | P1 | **COMPLETED** |
| P3 | Cross-cutting audits, target architecture, definitive file-level plan — **GATE** | Audit/Plan | P2 | **COMPLETED** |
| P4 | Core runtime & CLI foundation | Build: core | P3 | **COMPLETED** |
| P5 | Provenance & third-party notices | Build: supply | P4 | **COMPLETED** |
| P6 | Upstream bundling (staging → local bundle) | Build: supply | P5 | **COMPLETED** |
| P7 | Capability registry (single source of truth) | Build: core | P6 | **COMPLETED** |
| P8 | Routing engine | Build: core | P7 | **COMPLETED** |
| P9 | Context engine (levels, budget, cache) | Build: core | P8 | **COMPLETED** |
| P10 | Project state, plan index, decision memory | Build: core | P4 | **COMPLETED** |
| P11 | Multi-project isolation | Build: core | P10 | **COMPLETED** |
| P12 | Codebase domain (Graphify) | Build: domain | P9, P11 | **COMPLETED** |
| P13 | Engineering domain (+ lifecycle, completion discipline, project docs) | Build: domain | P12 | **COMPLETED** |
| P14 | Design domain (incl. merged Appllama native-mobile rules, D-034) | Build: domain | P9 | **COMPLETED** |
| P15 | Testing domain + local test-first verification (D-035) | Build: domain | P13 | **COMPLETED** |
| P16 | SEO domain + isolated BeyondSEO runtime | Build: domain | P15 | **COMPLETED** |
| P17 | Media domain (Brag) | Build: domain | P9 | **COMPLETED** |
| P18 | Observability (event model, history) | Build: core | P10 | **COMPLETED** |
| P19 | Claude Code adapter | Build: hosts | P8–P11, P18 | **COMPLETED** (files) |
| P20 | Codex adapter | Build: hosts | P19 | **COMPLETED** (files) |
| P21 | Cursor adapter | Build: hosts | P19 | **COMPLETED** (files) |
| P22 | Antigravity adapter | Build: hosts | P19 | **COMPLETED** (files) |
| P23 | Dashboard | Build: UX | P18 | **COMPLETED** |
| P24 | Update & rollback | Build: supply | P6, P7 | **COMPLETED** |
| P25 | Diagnostics & measured benchmarks | Verify | P4–P24 | **COMPLETED** |
| P26 | Documentation & migration guide | Docs | P25 | **COMPLETED** |
| P27 | Full integration, offline & host validation, final report | Verify | all | **COMPLETED** |

Ordering rationale vs. spec §66 anchors (D-004):
- **P4 core foundation is new.** v1.0.1 has no runtime (finding E-1), and every engine needs a package, CLI and test harness to live in.
- **The spec's "upstream audit" is split into P1–P3**, so the §64 gate items (matrices, target architecture, file-level plan) each have a verifiable phase.
- **P10 depends only on P4**, so project state can proceed in parallel with the registry/routing work if desired.

---

## P0 — Current repository audit · COMPLETED (2026-10-03)

| Item | Detail |
|---|---|
| Objective | Establish the factual v1.0.1 baseline before any change (spec §1, §98 steps 1–2). |
| Inputs | Repo @ `d77834e`; user's uncommitted `.claude-plugin/marketplace.json`. |
| Changes | Created branch; `.gitignore` += `.staging/`; added `docs/audit/{00,01,02,03,21}*.md`, `docs/audit/evidence/{phase0-file-inventory.tsv,upstream-staging-snapshot.yaml}`, this plan. `tests/security/test_security.py`: MCP walk now skips gitignored `.staging/` (it failed on `.staging/upstream/uiuxpromax/stack/.mcp.json`, which is upstream audit input, not plugin content). **No runtime file modified.** |
| Also done | Complete upstream snapshots of all 14 repos staged in `.staging/upstream/` (spec §3 staging rule, §98 steps 3–4); HEAD SHAs recorded. free-for-dev excluded and not fetched. |
| Tests | Baseline: unittest 20/20, doctor 50/0, validate 27/0 (with PyYAML). Without PyYAML: fails (E-1). |
| Acceptance criteria | ✔ every tracked file inventoried with hash · ✔ current routing, capability model and host support traced to evidence · ✔ every file classified (provisional) · ✔ gap analysis maps every spec area to a phase · ✔ MCP and free-for-dev status verified · ✔ v1.0.1↔v2 conflicts recorded with decisions. |
| Verification | Evidence files above; commands recorded in 01 §6–8. |
| Rollback | `git switch main && git branch -D feat/v2-os-transformation`; `rm -rf .staging`. |
| Evidence | `docs/audit/01_CURRENT_REPOSITORY_AUDIT.md` §1–11. |

## P1 — Upstream deep audit · COMPLETED (2026-10-03)

| Item | Detail |
|---|---|
| Objective | Audit all 14 complete snapshots per spec §3 steps 1–20 (code, config, scripts, hooks, agents/skills/workflows, plugin manifests, tests, deps, install/update, runtime, host assumptions, license files, network, filesystem, telemetry/background behavior, **MCP presence**). |
| Inputs | `.staging/upstream/*` @ SHAs in `upstream-staging-snapshot.yaml`. |
| Changes | `docs/audit/04_UPSTREAM_REPOSITORY_AUDIT.md` (one section per repo); `10_PROVENANCE_LICENSE_AUDIT.md` (inventory only, non-blocking per D-002); `12_SECURITY_AUDIT.md` (third-party script/hook/network/telemetry findings); `evidence/upstream-file-hashes/<repo>.tsv` (path, bytes, sha256). Pin decision per repo recorded in 21. |
| Dependencies | P0. |
| Tests | Script check: every tracked file of every snapshot appears in its hash TSV; every repo section answers all 20 audit points (or UNKNOWN + why/how/impact per §88). |
| Acceptance criteria | 14/14 repos audited; every MCP surface located; every executable/install/hook mechanism listed with a risk note; pins chosen. |
| Rollback | Docs only; delete files. |
| Known so far | MCP surfaces already seen: ECC (installed plugin exposes chrome-devtools MCP), UI/UX Pro Max (`stack/.mcp.json`: playwright, chrome-devtools, shadcn). Must be excluded from extraction (§2.1). |
| Result | **Done.** 14/14 repos audited (`04_UPSTREAM_REPOSITORY_AUDIT.md`), license inventory (`10_…`), third-party security audit with 16 controls (`12_…`), scanner `tools/audit/scan_upstream.py`, per-file hashes for all 26,588 files (inventory check: 14/14 PASS). Runtimes executed: Unlazy 188/188 ok; UI/UX Pro Max 164/164 OK; Graphify install + update + query OK; BeyondSEO 232/250 (9 browser-extra failures, UNKNOWN to confirm in P3). Pins: D-008. |
| Note | Largest audit phase (≈26k upstream files; OpenDesign alone is 12,940). Hash inventories are generated; reading focuses on executable surfaces, manifests, skills/agents and runtimes. |

## P2 — Capability, domain & extraction architecture · COMPLETED (2026-10-03)

**Result:** 7 domains / 62 capabilities (`tools/audit/domain-model.yaml`); machine-readable extraction rules (`tools/audit/extraction-rules.yaml`) applied to all 26,588 upstream files → **2,644 bundled files (50.7 MB)** after P3's AgentShield exclusion: ADAPT 973, COPY 644, PRESERVE 1,027; REFERENCE 686; EXCLUDE 21,257, each with a reason code. Dependency closure: **0 open gaps** (37 accepted with reasons; 23 closure files added). 37 in-bundle duplicate groups → content-addressed storage in P6. Docs 05–09 written; 05/06 generated by `tools/audit/render_matrix_docs.py`. Review correction: ECC `taste*` skills reclassified (music-video + paid fal.ai).


Produces `05_CAPABILITY_MATRIX.md` (§61), `06_DOMAIN_MAPPING.md` (§5–12), `07_SOURCE_EXTRACTION_MATRIX.md` (COPY/ADAPT/WRAP/REFERENCE/PRESERVE/EXCLUDE per component, §38–39), `08_DUPLICATION_ANALYSIS.md` (§37), `09_DEPENDENCY_RUNTIME_MATRIX.md`. Acceptance: every capability has the §13 metadata draft; every domain/subdomain is justified by a source path (no empty domains); complete-subsystem claims (Graphify, BeyondSEO, Brag) are proven by dependency traces.

## P3 — Cross-cutting audits, target architecture, file-level plan · COMPLETED (2026-10-03, gate passed D-025) · **GATE**

**Result:** docs 11, 13–20 written; decisions D-009…D-022; **file-level plan for P4–P27 in [FILE_LEVEL_PLAN.md](FILE_LEVEL_PLAN.md)**. Measured OLD-MODEL baseline: ≈30.4k est. tokens always loaded (v1.0.1 ≈212 + ECC ≈30,170). Host evidence: Claude Code installed (v1.0.1 + ECC); Codex/Cursor/Antigravity dirs present but CLIs absent and v1.0.1 not installed in them; the Antigravity "Runtime Tested" claim is unsupported. UNKNOWNs resolved: BeyondSEO browser extra → 250/250 OK (557 MB browser); AgentShield → `security-scan` excluded. §64 checklist: audit ✔, upstream audit ✔, capability matrix ✔, domain mapping ✔, gap analysis ✔, target architecture ✔, implementation plan ✔ (file-level), migration order ✔ (D-022), test plan ✔ (doc 17). **Open: Q-1 (BLOCKING for P6 only), Q-2/Q-3 (IMPORTANT, defaults set).** Gate passes on user review.


Produces `11_HOST_COMPATIBILITY_AUDIT`, `13_TOKEN_CONTEXT_AUDIT` (measured OLD-MODEL baseline incl. installed upstream plugins), `14_MULTI_PROJECT_ISOLATION_AUDIT`, `15_DASHBOARD_OBSERVABILITY_AUDIT`, `16_UPDATE_ROLLBACK_AUDIT`, `17_TESTING_AUDIT`, `18_MIGRATION_RISKS`, `19_OPEN_QUESTIONS`, `20_TARGET_ARCHITECTURE_RECOMMENDATION`, `00_EXECUTIVE_SUMMARY` (final), and **rewrites P4–P27 below as file-level tasks** (FILE · ACTION · PURPOSE · DEPENDENCIES · INPUTS · OUTPUTS · TEST · ROLLBACK, spec §63) with a migration order and test plan. Acceptance: §64 checklist complete; no open BLOCKING question; user review.

---

## P4 — Core runtime & CLI foundation · COMPLETED (2026-10-03, commit `dcdfd52`)

| Item | Detail |
|---|---|
| Changes | `pyproject.toml` (package `vikhyath`, Python ≥3.10, PyYAML); `vikhyath/{__init__,__main__,paths,cli}.py`; `vikhyath/diagnostics/{doctor,validate,benchmark}.py`; `scripts/{doctor,validate,benchmark}` → compatibility wrappers; `tests/manifests` read `VERSION`; `tests/unit/*`; CI installs the package. |
| Tests | 32/32; doctor 52/0 (50 legacy + 2 environment); validate 27/0; no-PyYAML path prints an install hint instead of crashing (E-1 fixed). |
| Acceptance | ✔ fresh-venv install · ✔ counts match v1.0.1 · ✔ `benchmark --baseline` reproduces doc 13 (ECC 120,682 B ≈ 30,170 est. tokens; total 121,523 B ≈ 30,380). |
| Deviations | Benchmark counts description-less agents by file stem (as hosts display them): v1.0.1 = 841 B, not 850 B; doc 13 corrected. Planned commands not yet built exit 2 with "planned for P<n>". |
| Evidence | `docs/evidence/P4/run.md` |
| Rollback | `git revert dcdfd52` |

## P5 — Provenance & third-party notices · COMPLETED (2026-10-03, commit `0d8553e`)

| Item | Detail |
|---|---|
| Changes | `vikhyath/bundle/{rules,provenance,notices}.py`; `tools/audit/extraction_matrix.py` imports the shared engine; generated `third_party/licenses.json` + `THIRD_PARTY_NOTICES.md`; `tests/bundle/{test_rules,test_provenance}.py`. |
| Tests | 45/45. Matrix regenerated from scratch after the move: byte-identical. |
| Acceptance | ✔ one provenance record per planned file, all valid, `original_hash` = audited blob SHA-1 · ✔ 14 upstreams: 12 MIT, 2 Apache-2.0, Karpathy recorded as declared-MIT without license text. |
| Rollback | `git revert 0d8553e` |

## P6 — Upstream bundling & central install · COMPLETED (2026-10-03, commit `2d08a91`)

| Item | Detail |
|---|---|
| Changes | `vikhyath/bundle/{closure,checks,store,build,fetch}.py`, `vikhyath/bundle/transforms/{__init__,gstack,rewrites}.py`, `vikhyath bundle fetch|build|verify|list`, `scripts/install`; rules updates (gstack generated files → renderer inputs, Angular MCP doc and UI/UX tooling tests excluded); CONTRIBUTING + PR template + security test updated for D-023; `tests/bundle/{test_build,test_transforms}.py`. |
| Result | Known-good bundle **`c98667e034f7`**: 2,594 files (50.3 MB), 64 transformed, 0 errors (closure, MCP config, provenance). Bundled Unlazy and UI/UX Pro Max self-tests pass. **A fresh networked `scripts/install` reproduced the identical bundle id** (153 MB sparse download vs ~1.1 GB full clones; 1m54s). |
| Tests | 60/60. |
| Deviations | **D-026:** hardlinked blob store dropped (broke Unlazy's single-link tamper check; saved only ~1 MB): files are plain copies, integrity via provenance hashes. **D-027:** gstack renderer uses strong anchors only (a weak anchor had put ship's table into review); unresolved placeholders (15 files) and adaptation debts (8 MCP mentions, 52 gstack runtime paths) are listed in `BUILD.json` and owned by P13–P17. Planned `strip_directives`/`section_split` transforms replaced by targeted rewrites now and section indexing in P9. |
| Open | Nothing installed into the real `~/.vikhyath` yet (all builds in scratch homes). |
| Evidence | `docs/evidence/P6/run.md` |
| Rollback | `git revert 2d08a91`; delete `$VIKHYATH_HOME/bundles/<id>` |

## P7 — Capability registry · COMPLETED (2026-10-03, commit `3eb2195`)

| Item | Detail |
|---|---|
| Changes | `capabilities/<domain>/<sub>/{card.yaml,CARD.md}` ×62, `capabilities/<domain>/domain.yaml` ×7, `capabilities/defaults.yaml`; `vikhyath/registry/{schema,loader,generate}.py`; `vikhyath registry check|cards|build|list|show`; `bundle build` writes `<bundle>/registry.yaml`; `config/priorities.yaml` → conflict hierarchy (role names) + `domain_defaults`; doctor/validate/tests/CI/docs moved off the retired files. **Removed:** `config/capabilities.yaml`, `integrations/*.yaml` (9), `tools/audit/domain-model.yaml`, `tests/validation/`. |
| Result | One registry source (D-028). Generated registry has all 29 spec §13 fields for all 62 capabilities; provenance fields derived, never authored. Web QA classes: 7 CORE + browser-fallback FALLBACK (headless OPTIONAL / visible FALLBACK) — *superseded by A-1/D-035: 8 CORE + `testing/browser-exception` DISABLED_BY_POLICY; 63 capabilities*. Real bundle rebuilt: same id **`c98667e034f7`**, registry valid, self-tests pass. Docs 05/06 and the extraction matrix regenerate unchanged from the cards. |
| Tests | 79/79 (19 new registry tests incl. planted-violation checks); doctor 45/0 (was 52: 9 integration-file checks replaced by 3 registry checks, `config/capabilities.yaml` YAML check removed); validate 20/0 (registry + 14 pins instead of 9 integration files). |
| Acceptance | ✔ exactly one registry (retired files gone; grep test finds no references outside history docs) · ✔ no repo-name capability ids (validator + test) · ✔ web QA classes recorded (§23A.13) · ✔ schema-validated, every §13 field present. |
| Findings for later phases | Engineering's 17 cards total ≈2,341 est. tokens: above D-014's provisional L1 ≤2k/domain, so P9 must load routed cards (or an index), not whole domains. `config/routing.yaml` is still v1 repo-keyed (replaced in P8). `conflicts` empty by design (D-028). |
| Evidence | `docs/evidence/P7/run.md` |
| Rollback | `git revert 3eb2195`; delete `$VIKHYATH_HOME/bundles/<id>/registry.yaml` (regenerated by the next build). |

## M2 review summary

M2 (P4–P7) delivered the foundation: the `vikhyath` core + CLI (P4), shared extraction rules + provenance + notices (P5), a reproducible local bundle with central install (P6), and the single capability registry generated into every bundle (P7). Bundle `c98667e034f7`: 2,594 files, 0 errors, reproducible from pins. **Next: M3 (P8 routing → P9 context → P10 state → P11 isolation → P18 observability)** after user review.

## P8 — Routing engine · COMPLETED (2026-10-04, commit `fec0373`)

| Item | Detail |
|---|---|
| Changes | `config/routing.yaml` v2 (D-029); `vikhyath/routing/{classify,rules,select,fallback_bm25,router}.py`; `vikhyath route`; `tests/routing/{scenarios.yaml,test_scenarios.py,test_routing.py}`; validate's routing section; `seo/ai-search` → depends on `seo/evidence`; routing entry skill + CLAUDE.md/AGENTS.md/Antigravity skill point at the CLI. |
| Result | Deterministic pipeline: rules/paths (strong) + card intent tags (weak) → suppression ("forbidden pairings") → project stage (new: no codebase; existing: impact analysis first) → limit → declared conflicts → dependency closure → fallbacks → BM25 only when not confident. Output: §54 change type, domains, capabilities in conflict-hierarchy order, dependencies, fallbacks, browser policy (`none`/`fallback-only`/`explicit-visual`; *A-1/D-035: `disabled`/`exception-requested` + `verification_mode`*), pipeline, suppressed list with reasons. |
| Tests | 96/96 (17 new). All 19 spec scenarios (§14 ×5, §23A.14 ×4, §70 A–H, Ponytail explicit-only ×2) pass with expected **and** forbidden sets. Doctor 45/0, validate 20/0. |
| Acceptance | ✔ all scenarios pass · ✔ routing p95 **0.333 ms** (< 100 ms; 950 calls) · ✔ no LLM call; BM25 only below the confidence threshold. |
| Deviations | Spec capability names without a registry id are mapped by an alias table in the scenario file (e.g. `testing/integration` → `testing/web-verification`). §70 I (multi-project) is tested in P11. |
| Evidence | `docs/evidence/P8/run.md` |
| Rollback | `git revert fec0373` |

## P9 — Context engine · COMPLETED (2026-10-04, commit `9b4b63a`)

| Item | Detail |
|---|---|
| Changes | `config/budgets.yaml` (D-014 values, each with a `why`); `vikhyath/context/{sections,budget,cache,loader,levels}.py`; `vikhyath/project/identity.py` (project id + `ProjectRef`, pulled forward from P10 because the cache is keyed by project); `vikhyath bootstrap`, `vikhyath context`; `tests/context/{fixtures,test_budgets,test_cache}.py`. |
| Result | L0 bootstrap (306 est. tokens here); L1 = routed CARD.md only; L2 = most relevant entry files' sections within 8k (≤ 3 capabilities full, rest index-only); L3 = one explicit `--file` (≤ 12k). Per-bundle context index (0.40 s once, 10 ms after). Per-project, per-session cache: bundle files keyed by provenance sha256 (no stat/read), project files by size+mtime. D-030. |
| Tests | 114/114 (18 new). |
| Acceptance | ✔ L0 ≤ 1.5k on fixtures (and on this repo: 306) · ✔ second identical load = cache hit with **no file reread** (instrumented reads; 12 real scenarios: all hits, 0 B read) · ✔ L3 only with an explicit flag. Every measured L1 ≤ 2k/domain, L2 ≤ 8k. |
| Deviations | `project/identity.py` built in P9 (needed for cache keys); P10 adds state on top. The cache elides content only when a session id is given (`--session`/`$VIKHYATH_SESSION_ID`); without one every load is sent. |
| Evidence | `docs/evidence/P9/run.md` |
| Rollback | `git revert 9b4b63a`; delete `$VIKHYATH_HOME/cache/context-index/` and `$VIKHYATH_HOME/projects/*/sessions/` (regenerable). |

## P10 — Project state, plan index, decisions · COMPLETED (2026-10-04, commit `7c145c9`)

| Item | Detail |
|---|---|
| Changes | `vikhyath/project/{state,plan_index,decisions,change,lifecycle,questions,reconcile}.py`; `config/questions.yaml`; `templates/project-docs/*.md` ×9; CLI `project init|status|questions|answer|relink`, `state`, `plan index|show|locate|add-task|set-status|reconcile`, `decide add|list|show`; `bootstrap`/`route`/`context` read the state (stage, stack, phase, plan pointer, relevant decisions); `tests/project/test_project.py`. |
| Result | `<project>/.vikhyath/{state,plan-index,decisions,verification}.yaml` (D-011, D-031). The markdown plan stays the one human document; the index answers per-turn questions (0.21 ms, one stat). Reconciliation adds a change to the right phase of that plan (§21, §56) with a §55 impact record; §25 transitions enforced, done states need evidence; §53 question engine; decisions separately discoverable by kind. |
| Tests | 130/130 (16 new). Doctor 45/0. |
| Acceptance | ✔ state read ≪ full docs: 2.35 KB state+index (158 B in L0) vs 9.1 KB of near-empty templates; < 1/5 with filled docs (test) · ✔ “Add Google Maps navigation to bookings” → T-3.3 in P3 Booking System, no new file in the project. |
| Deviations | `project relink` built here (listed for P10's CLI) rather than P11. Spec §56.7 "record decision if architecture changed" is surfaced as `decision_needed` in the reconcile report (the OS cannot invent the decision text). |
| Evidence | `docs/evidence/P10/run.md` |
| Rollback | `git revert 7c145c9`; projects keep their `.vikhyath/` files (plain YAML) and docs. |

## P11 — Multi-project isolation · COMPLETED (2026-10-04, commit `6172057`)

| Item | Detail |
|---|---|
| Changes | `vikhyath/isolation/{guard,locks,atomic}.py`; context loader/cache and every project state/plan/decision/session read and write routed through the guard, per-project locks and atomic writes (D-032); `tests/isolation/{test_multi_project,test_concurrency,test_cache_keys}.py`. |
| Result | Structural isolation: allowed roots = own project, own data dir, OS files; resolved paths (no `..`/symlink escape); violations reported to hooks for P18. Plan edits re-read the index under the lock. |
| Tests | 141/141 (11 new). |
| Acceptance | ✔ doc 14 tests: three interleaved projects, audit-hooked opens → 0 cross-project reads, other projects unchanged, no foreign decisions or credentials in output · ✔ 4×25 concurrent increments = 100 · ✔ 15 concurrent task adds = unique ids · ✔ no partial file under 300 concurrent reads · ✔ cache keys per project · ✔ relink (P10). |
| Evidence | `docs/evidence/P11/run.md` |
| Rollback | `git revert 6172057`; lock files under `$VIKHYATH_HOME/projects/*/locks/` are empty and disposable. |

## P18 — Observability · COMPLETED (2026-10-04, commit `7e54375`)

| Item | Detail |
|---|---|
| Changes | `vikhyath/events/{schema,redact,log,rules_cel}.py`; lifecycle emission from bootstrap, route, context loader, plan reconcile/status, decisions, init and the isolation guard; `vikhyath events list|observe|rules`; `tests/events/{test_events,test_rules}.py`, `tests/unit/test_redact.py`; routing CLI tests use a temporary home. D-033. |
| Result | Per-project, redacted, append-only JSONL event log with the doc 15 envelope; risk detection runs the bundled Beacon rules (77 rules, 535/535 embedded tests) over host tool events, with session correlation. |
| Tests | 160/160 (19 new). Doctor 45/0, validate 19/0. |
| Acceptance | ✔ events emitted for the full routing lifecycle (exact sequence asserted) · ✔ no secrets in logs (11 planted kinds; demo grep = 0) · ✔ each rule's embedded tests run as unit tests · ✔ observability cards (4) already in the registry since P7. |
| Deviations | Beacon rules are COPY'd, not adapted: they evaluate Beacon-shaped *host tool events* (`events observe`, fed by the P19+ adapters), while OS lifecycle events go to the log. The redactor runs on events; applying it to `doctor`/diagnostics output is left to P25 (diagnostics) and recorded there. |
| Evidence | `docs/evidence/P18/run.md` |
| Rollback | `git revert 7e54375`; event logs under `$VIKHYATH_HOME/projects/*/events/` are append-only data and can be deleted. |

## M3 review summary

M3 (P8, P9, P10, P11, P18) delivered the brain: a deterministic router (19 spec scenarios, p95 0.33 ms), a budgeted L0–L3 context engine with a per-session cache (second load: 0 bytes read), compact project state with one living plan, reconciliation, decisions and questions (Google Maps → existing booking phase, no new file), structural multi-project isolation (0 cross-project opens; no lost updates), and a redacted event log with Beacon risk detection (535/535 rule tests). 160 tests. **Next: M4 (P12 codebase → P13 engineering → P14 design → P15 testing)** after user review.

## Amendment A-1 — phase reconciliation (2026-10-05) · COMPLETED

**Change:** (a) Appllama audited against OpenDesign/Taste/UI-UX Pro Max/ECC; only proven-unique native-mobile rules merged into `design/frontend` + `design/motion` (APPLLAMA_STATUS = MERGED, D-034). (b) Browser visual verification, Chrome DevTools, screenshot verification/comparison, visual browser QA and simulator recording loops removed from the verification model; one global policy `config/verification.yaml` = **local test-first** (D-035); testing reshaped (D-036). **Reason:** user specification update (2026-10-05). **Dependencies:** none new; phase order unchanged. **Provenance:** Appllama pinned `dd5caae` (MIT), 4 files bundled; 15 browser/visual files moved to EXCLUDE (BROWSER_POLICY). **Rollback:** `git revert` of the A-1 commit + delete bundle `cb0635dbf824`. **Evidence:** [docs/evidence/D034-D036/run.md](../evidence/D034-D036/run.md). Details: doc 22.

Verification method for **every** phase below: local deterministic checks only — unit/integration tests, `vikhyath validate`, `vikhyath doctor`, `vikhyath registry check`, `vikhyath bundle build/verify`, measured numbers. No phase uses a browser, Chrome DevTools or screenshots as acceptance.

| Phase | Objective (A-1 view) | Deps | Affected capabilities | Affected files | Implementation changes | Test plan | Acceptance | Rollback | Status |
|---|---|---|---|---|---|---|---|---|---|
| P0 Repo audit | Locate every browser/Chrome/screenshot/MCP path; set up Appllama audit | — | testing/*, design/* | doc 22 §1 | Repo-wide search; classification required/optional/duplicated/incompatible | grep evidence | All browser + Appllama references identified ✔ | docs only | **AMENDED · COMPLETED** |
| P1 Upstream audit | Audit Appllama; classify browser/MCP/screenshot/remote deps in all 15 upstreams | P0 | — | `upstream-file-hashes/appllama.tsv`, `upstream-scan/appllama.json`, `upstream-staging-snapshot.yaml`, doc 22 §2–3 | Appllama snapshot pinned; scanner run; table UPSTREAM→BROWSER?→MCP?→EXTRACT/EXCLUDE | inventory + scan | 15/15 classified ✔ | delete evidence files | **AMENDED · COMPLETED** |
| P2 Capability/domain architecture | Appllama not a domain; design stays unified; testing = local verification | P1 | design/frontend, design/motion, testing/* | `capabilities/testing/*`, `capabilities/design/{frontend,motion,design-review}` | `web-verification`→`local-verification`, `browser-fallback`→`browser-exception` (DISABLED_BY_POLICY), + `testing/evidence`; no repo-named ids | registry tests | 63 capabilities; no `design/appllama` ✔ | revert cards | **AMENDED · COMPLETED** |
| P3 Cross-cutting / plan | Reconcile plan, file-level plan, target architecture | P2 | — | `docs/plan/*`, doc 22, D-034–D-036 (D-020 superseded) | This section; FILE_LEVEL_PLAN P12–P27 rows | review | One plan, one decision log ✔ | revert docs | **AMENDED · COMPLETED** |
| P4 Core | — | — | — | — | **NO CHANGE REQUIRED**: package/CLI unaffected; the new module `vikhyath/verify/` is packaged automatically | full suite | — | — | COMPLETED |
| P5 Provenance | Record Appllama source/license; record exclusions | P4 | design/frontend, design/motion | `tools/audit/extraction-rules.yaml` (reason codes BROWSER_POLICY, PAID_SERVICE), `third_party/licenses.json`, `THIRD_PARTY_NOTICES.md` | Regenerated notices: 15 upstreams (13 MIT, 2 Apache-2.0) | `tests/bundle/test_provenance.py` (2,583 records, SHA-1 = audited blob) | Exact SHA + license + paths for every extracted file ✔ | revert + regenerate | **AMENDED · COMPLETED** |
| P6 Bundling | Bundle only required files; no browser verification files; Appllama 3 files only | P5 | testing/*, design/* | rules, `vikhyath/bundle/transforms/rewrites.py` (Appllama SKILL 11 rewrites, gstack review exploratory step) | Exclusions; accepted closure gaps with reasons | `tests/bundle/test_transforms.py`; `bundle build --self-test` | Known-good `cb0635dbf824`: 2,583 files, 0 errors, closure 0 open, self-tests pass ✔ | `git revert`; previous bundle via `previous` | **AMENDED · COMPLETED** |
| P7 Registry | Every entry states `runtime_status`; browser verification DISABLED_BY_POLICY | P6 | all | `vikhyath/registry/{schema,generate}.py`, cards | `WEB_QA_CLASSES` = CORE/OPTIONAL/DISABLED_BY_POLICY; `requires_browser` only in SEO/media; disabled card can't be enabled | `tests/structural/test_registry.py` (+2 tests) | Registry valid; normal routing cannot reach the disabled card ✔ | revert | **AMENDED · COMPLETED** |
| P8 Routing | No browser for ordinary work; mobile → design/frontend; webhook → tests + security | P7 | testing/local-verification, design/frontend | `config/routing.yaml`, `vikhyath/routing/{rules,router}.py`, `tests/routing/scenarios.yaml` | `browser: disabled\|exception-requested`, `verification_mode`; rules `mobile-native`, `webhook-verification`; rule validation rejects disabled targets; BM25 method-label fix | 22 scenarios (3 new: webhook, React website, React Native) | Spec routing examples pass with forbidden sets ✔ | revert | **AMENDED · COMPLETED** |
| P9 Context | Never load browser/screenshot/Appllama-MCP instructions | P8 | — | — | **NO CHANGE REQUIRED** (code): those files no longer exist in the bundle; BM25 file ranking loads Appllama only for mobile queries (measured, doc 22 §8) | measured L2 runs | Web query loads 0 Appllama bytes ✔ | — | COMPLETED |
| P10 State | Record verification mode, disabled mechanisms, last result, evidence, exceptions | P4 | testing/evidence | `vikhyath/project/state.py` | `verification_block()` from policy; `record_browser_exception()`; L0 policy line | `tests/project/test_project.py` (+2) | `state.yaml` shows `mode: local-test-first`, 3 mechanisms `disabled` ✔ | revert; extra keys ignored by old readers | **AMENDED · COMPLETED** |
| P11 Isolation | Exceptions/evidence/test state never cross projects | P10 | — | `tests/project/test_project.py` | Exceptions written through the guard into the project's own `verification.yaml` | two-project test | Other project has no exception and no event ✔ | revert | **AMENDED · COMPLETED** |
| P12 Graphify | Graphify picks *what to test* (affected files → relevant tests); not a verifier | P9, P11 | codebase/impact-analysis, testing/local-verification | FILE_LEVEL_PLAN P12 | + `affected` → test-file mapping output for P15 selection | fixture repo: change → test set | Affected-file query also returns the relevant tests ✔ | revert | **COMPLETED** (2026-10-10) |
| P13 Engineering | Engineering material without browser execution paths | P12 | engineering/*, testing/strategy | FILE_LEVEL_PLAN P13 | D-027 debts + residual browser mentions in adapted gstack/ECC/Addy text removed or reframed (doc 22 §3) | grep test over engineering/testing bundle files | No executable browser step in engineering/testing files ✔ | revert | **COMPLETED** (2026-10-10) |
| P14 Design | One canonical design architecture incl. merged Appllama rules | P9 | design/* | FILE_LEVEL_PLAN P14 | Overlap matrix done (doc 22 §2); design-token checks (accent/grey/radius counts) as local tests; no screenshot design review | scenario D + mobile scenario | No duplicate design rules; mobile route loads the native rules ✔ | revert | **COMPLETED** (2026-10-10) |
| P15 Testing | **Local test-first verification engine** | P13 | testing/* | FILE_LEVEL_PLAN P15 (rewritten) | Test discovery, impact-based selection, run, diagnose, targeted rerun, static/build/security/a11y/perf checks, evidence writer, `vikhyath verify [--exception]`; **no Playwright runtime, no browser module** | `tests/verify/*` with fixture projects | Payment-webhook change selects unit/signature/integration/idempotency/security + typecheck/build; no browser process ever started; evidence machine-readable ✔ | revert | **COMPLETED** (2026-10-10) |
| P16 SEO | Unchanged architecture; browser use stays inside the SEO runtime | P15 | seo/* | FILE_LEVEL_PLAN P16 note | SEO capture evidence never becomes engineering verification | as planned | Scenarios E/F/I; SEO browser only in `runtimes/seo-*` ✔ | revert | **COMPLETED** (2026-10-10) |
| P17 Media | Showcase output separate from verification | P9 | media/* | FILE_LEVEL_PLAN P17 note | Media screenshots/videos are never verification evidence | as planned | Scenario H ✔ | revert | **COMPLETED** (2026-10-10) |
| P18 Observability | Record exceptional browser requests; no browser telemetry workflow | P10 | observability/events | `vikhyath/events/schema.py`, `project/state.py` | `BROWSER_EXCEPTION_REQUESTED` replaces `BROWSER_FALLBACK_ACTIVATED` | project test asserts the event | Event logged per project only ✔ | revert | **AMENDED · COMPLETED** |
| P19–P22 Hosts | Same verification policy on all four hosts | P8–P11, P18 | — | FILE_LEVEL_PLAN P19–P22 | Adapters render the policy reference; may not enable Chrome DevTools, screenshots, visual QA or MCP; test asserts it | `tests/hosts/test_policy.py` | Every adapter output references `config/verification.yaml`; none contains MCP/browser enablement ✔ | revert | **COMPLETED** (2026-10-11) |
| P23 Dashboard | Show verification status, evidence, disabled capabilities | P18 | observability/* | FILE_LEVEL_PLAN P23 | Read-only views of state/evidence; no visual-QA view; off unless a session is active or explicitly opened | `tests/dashboard/*` | Fixture data → correct status; no browser verification UI | revert | NOT_STARTED (plan updated) |
| P24 Update/rollback | Pin + diff + re-audit Appllama extracted files only | P6, P7 | — | FILE_LEVEL_PLAN P24 | Update of an upstream re-runs the overlap check for its extracted files; no MCP config handled | `tests/update/*` | Appllama update touches only its 4 bundled files (inventory diff reports exactly the bundled paths changed) ✔ | revert | **COMPLETED** (2026-10-11) |
| P25 Diagnostics | Detect policy violations | P4–P24 | — | `vikhyath/diagnostics/validate.py` (done), FILE_LEVEL_PLAN P25 | Done now: policy section + forbidden bundle paths. P25 adds doctor: host-installed MCP / Chrome DevTools detection, duplicate design rules, stale pins | fixture-based tests | The four example errors of the spec are emitted on planted violations ✔ (host Chrome DevTools/Playwright MCP, duplicate design files, pin age, policy violations in validate) | revert | **COMPLETED** (2026-10-11) |
| P26 Docs | Document local test-first default, Appllama status, no MCP | P25 | — | FILE_LEVEL_PLAN P26 | + `docs/architecture/VERIFICATION_POLICY.md`; TESTING/DESIGN architecture reflect D-034/D-035 | doc review | Docs state the policy verbatim ✔ | revert | **COMPLETED** (2026-10-11) |
| P27 Integration | Final reconciliation incl. the A-1 checklist | all | all | FILE_LEVEL_PLAN P27 | + checks: no MCP, no Appllama MCP, no paid dependency, no browser default, no screenshot verification, no repo-dump, no duplicate design/capability sources, no project-local OS | e2e + offline | doc 22 §9 checklist all ✔ ✔ | — | **COMPLETED** (2026-10-11) |

## P12 — Codebase (Graphify) · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `vikhyath/runtimes/{graphify,graphify_probe}.py` (isolated runtime: install, health, allowlist, per-project `GRAPHIFY_OUT`); `vikhyath/codebase/{impact,structural}.py` (affected files + related tests, code-surface limit, §74 structural fallback); CLI `vikhyath runtime status\|install graphify`, `vikhyath codebase affected\|update\|query\|path\|explain`; router `impact` step (route schema v3); doctor "Runtimes" section (MR-09); `skills/vikhyath-codebase/SKILL.md`; `graphify/serve.py` EXCLUDE → PRESERVE (rules, matrix, notices regenerated). D-037. |
| Result | Change → Graphify reverse traversal (depth 2) → ≤ 12 files + the tests that cover them, with `omitted` and `unknown` always reported. Graph lives in `$VIKHYATH_HOME/projects/<id>/graph`; the project is never written to (no `graphify-out/`, hooks or rule files). Graph rebuilt only when code changed (this repo: 3.2 s build, 0.15 s per later query). Without the runtime: structural fallback with the §74 notice. `hook/install/watch/serve/extract/label` blocked; no `graphify-mcp` script, no `mcp` package, no API keys passed. |
| Tests | 184/184 (19 new: `tests/context/test_code_surface.py` 9, `tests/runtimes/test_graphify.py` 10 incl. 3 opt-in real-runtime tests, run against the built bundle). Doctor 47/0, validate 23/0, registry valid. |
| Acceptance | ✔ affected-file query narrows the code surface on a fixture repo (32 candidate files → 12 + `omitted: 20`) · ✔ related tests returned (A-1 duty for P15) · ✔ graph outside the project, project tree unchanged · ✔ excluded subcommands blocked · ✔ §74 fallback with notice · ✔ known-good bundle `68fcabbc8e1b` (2,584 files, 0 errors, self-tests pass); runtime installs from it in 5.8 s. |
| Deviations | No `sections.yaml` files: the P9 context engine already splits bundle files into sections, so the 3 codebase cards needed no change beyond the re-rendered CARD.md. `affected` is a command the route points to (`impact` field), not run inside `vikhyath route` (D-037e). Upstream pytest: 5,853 passed / 66 failed / 263 skipped; the captured failures are optional language extras the OS does not install (Terraform, VB.NET, Erlang); full per-file breakdown deferred to P25. The closure trace missed `serve.py` (absolute import inside a function); P25 extends the trace. Old runtime directories are not garbage-collected yet (P24). |
| Evidence | `docs/evidence/P12/run.md` |
| Rollback | `git revert` of the P12 commit; delete `$VIKHYATH_HOME/runtimes/graphify-*` and `$VIKHYATH_HOME/projects/*/graph/` (regenerable); previous bundle `cb0635dbf824` via `bundles/previous`. |

## P13 — Engineering · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `config/lifecycle.yaml` + `vikhyath/project/lifecycle.py` (load/validate/steps_for); router `lifecycle` (schema v4); `vikhyath/bundle/transforms/domain.py` (TRANSFORM_VERSION 3) + 2 targeted rewrites; `laravel-plugin-discovery` excluded; `vikhyath/runtimes/unlazy.py`, `vikhyath gates`, `vikhyath runtime unlazy-hook`; entry skills engineering/security/review/production and the 3 agents rewritten (frontmatter); `workflows/` removed; doctor/README/CONTRIBUTING updated. D-038. |
| Result | Every engineering route carries its lifecycle with OS commands and exit criteria. Bundle `2d1356913230` (2,583 files, 0 errors): **D-027 debts cleared** — `unresolved_placeholders {}`, `debts {}` (was 13 files / 54 files); 253 gstack runtime code lines removed with markers, 94 prose lines marked, frontmatter hooks dropped from 5 skills. Unlazy gates run from the bundle; Stop hook only in `~/.claude/settings.json`, pointing at `bundles/current`. |
| Tests | 194/194 (10 new in `tests/engineering/test_engineering.py`; 3 opt-in skipped). Doctor 45/0, validate 22/0 (no unittest step), registry valid; bundle self-tests (Unlazy, UI/UX Pro Max) exit 0. |
| Acceptance | ✔ scenarios A, B, C route with lifecycle (A: requirements questions first; B: reconcile into the plan; C: bug fix test-first) · ✔ D-027 debts in engineering/testing files: none · ✔ no executable browser step left un-annotated in engineering/testing/codebase files. |
| Deviations | No per-capability `sections.yaml` (P9 sections cover it, as in P12). gstack's own runtime tools are removed, not ported; the affected steps point to OS commands. Graphify runtime lock now hashes only code + pins (doc rewrites no longer force a reinstall). |
| Evidence | `docs/evidence/P13/run.md` |
| Rollback | `git revert` of the P13 commit; previous bundle via `bundles/previous`; `vikhyath runtime unlazy-hook --disable` removes the hook. |

## P14 — Design · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `vikhyath/runtimes/uiux.py`; `vikhyath/design/tokens.py` + `config/design.yaml`; CLI `vikhyath design search\|system\|check`; `runtime status` lists uiuxpromax; `skills/vikhyath-design/SKILL.md`; domain transform covers design (TRANSFORM_VERSION 4). D-039. |
| Result | Design work has a deterministic local check (accents, grey families, radii, fonts) instead of screenshot review; the UI/UX engine searches and generates design systems from the bundle and persists only into the project's `design-system/`. Design decisions use the P10 memory (`--kind design`). Bundle `495f026f381e` (2,583 files, 0 errors, `debts {}`, self-tests pass). |
| Tests | 199/199 (5 new in `tests/design/test_design.py`; 3 opt-in skipped). Doctor 46/0, validate 22/0. |
| Acceptance | ✔ scenario D routes to design only (no lifecycle, no other domain) · ✔ React Native request selects `design/frontend` (merged Appllama native rules) · ✔ D-027 design debts cleared (gstack design-consultation / plan-design-review placeholders and runtime steps, D-038 transform) · ✔ design-token checks run as local tests. |
| Deviations | The 10 design cards already existed (P7) and needed no change; no `sections.yaml` (P9). `--persist` writes `design-system/<slug>/MASTER.md` (UI/UX Pro Max layout) rather than `DESIGN.md`. |
| Evidence | `docs/evidence/P14/run.md` |
| Rollback | `git revert` of the P14 commit; previous bundle via `bundles/previous`. |

## P15 — Testing & local test-first verification · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `vikhyath/verify/{detect,select,run,evidence,engine}.py`; CLI `vikhyath verify [--plan] [--paths] [--all] [--kind] [--include-e2e] [--task]`, `vikhyath verify exception --reason`, `vikhyath test`; `skills/vikhyath-testing/SKILL.md`. D-040. |
| Result | A change's impacted tests (P12) are run with the project's own runner, plus typecheck/lint/build; failures are diagnosed and rerun once; results are evidence JSON in the project and the project's last verification. No browser on any path. |
| Tests | 209/209 (10 new in `tests/verify/test_verify.py`; 3 opt-in skipped). Doctor 46/0, validate 22/0. |
| Acceptance | ✔ payment-webhook change selects webhook (api), signature (security), idempotency, integration flow and security tests — not the unrelated reports test — plus the build check · ✔ every subprocess recorded: no chrome/playwright/puppeteer/screenshot/browser · ✔ evidence has command + exit code + result + at, counts (5 passed) and validates; visual claims rejected · ✔ failing change → FAILED with counts, diagnosis and rerun · ✔ exception records only, no subprocess · ✔ on this repository: `vikhyath verify --paths vikhyath/verify/select.py` selected 13 tests + build, PASSED in 2.9 s (an earlier run caught a real failing assertion). |
| Deviations | Static/security checks run only when the project configures the tool (no installs); dependency audits needing the network (npm audit, pip-audit) are not run by default. Evidence lives in the project's `.vikhyath/evidence/` (project-owned state, D-011). |
| Evidence | `docs/evidence/P15/run.md` |
| Rollback | `git revert` of the P15 commit; evidence files are plain JSON and can be deleted. |

## M4 review summary

M4 (P12–P15) delivered the main domains: codebase intelligence (Graphify graph + structural fallback, affected files and their tests within 12 files), one engineering lifecycle in every route with gstack/MCP/browser adaptation debts cleared from the bundle (D-027 closed for engineering/testing/design), Unlazy gates with a central-only Stop hook, the design engine with deterministic design-token checks, and the local test-first verification engine with machine-readable evidence. 209 tests; known-good bundle `495f026f381e`. **Next: M5 (P16 SEO → P17 Media)** after user review.

## P16 — SEO · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `vikhyath/runtimes/{venv,seo,seo_probe}.py` (Graphify moved onto the shared venv helper); `vikhyath/seo/{evidence,authorization}.py`; CLI `vikhyath runtime install seo [--browser] [--reports]`, `vikhyath seo run\|evidence\|authorize`; `skills/vikhyath-seo/SKILL.md`. D-041. |
| Result | BeyondSEO 2.9.1 runs isolated (installed from the bundle in 3.0 s, core only); crawl output lands in the project's data dir; every claim can be labelled from the capture; live-site edits are gated per task. |
| Tests | 218/218 overall (6 new in `tests/seo/test_seo.py`). Upstream BeyondSEO suite in the SEO venv, core only: **340 passed, 9 failed, 17 skipped** — all 9 need the browser extra (rendered/auto-mode tests, `No module named 'playwright'`), as in the P3 baseline. |
| Acceptance | ✔ failed capture → "could not be inspected" (real crawl of a loopback site, refused by BeyondSEO's private-address guard → UNKNOWN) · ✔ `edit apply` blocked without authorization; scoped to site/task, expires, use logged · ✔ `watch` blocked · ✔ scenarios E/F route to SEO only (I: multi-project, P11) · ✔ browser only inside `runtimes/seo-*` and only on explicit `--browser`. |
| Deviations | No per-capability `sections.yaml` (P9). Browser-extra suite (250/250 in P3) not re-run here: it needs the 557 MB Chromium download, which stays opt-in. |
| Evidence | `docs/evidence/P16/run.md` |
| Rollback | `git revert` of the M5 commit; delete `$VIKHYATH_HOME/runtimes/seo-*` and `projects/*/seo/`. |

## P17 — Media · COMPLETED (2026-10-10)

| Item | Detail |
|---|---|
| Changes | `vikhyath/runtimes/brag.py`; CLI `vikhyath media plan [--full]`, `vikhyath media music-cues <audio>`, `vikhyath runtime install brag`; `skills/vikhyath-media/SKILL.md`. D-041. |
| Result | Dry run on a fixture project: mode `brag-slim` (Q-4 default), skill `files/brag/skills/brag-slim/SKILL.md` (7.8 KB) with its load command, tools found (ffmpeg, ffprobe, node, npx, python3), output `brag-output/`. `--full` without local Hyperframes stays on brag-slim and says why. |
| Tests | 3 new in `tests/media/test_media.py`. |
| Acceptance | ✔ scenario H ("Make a launch video plan for our product.") → `media/launch-video` only, no lifecycle, no impact step, no backend capability · ✔ media output marked as never verification evidence. |
| Deviations | The music-cue analyser venv (librosa) is installed only on request and was not installed in this run. |
| Evidence | `docs/evidence/P17/run.md` |
| Rollback | `git revert` of the M5 commit. |

## M5 review summary

M5 (P16, P17) delivered the specialist domains: an isolated BeyondSEO runtime (core by default, browser extra opt-in and scoped), evidence-labelled SEO claims from real capture quality, a per-task authorization gate for live-site edits, and the Brag media workflow (brag-slim default, full only with local Hyperframes). 218 tests; bundle `495f026f381e` unchanged. **Next: M6 (P19–P22 host adapters)** after user review.

## P19–P22 — Host adapters · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | `vikhyath/adapters/{base,hosts}.py`; `bin/vikhyath` launcher; `hooks/hooks.json` (SessionStart bootstrap only); generated `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `.agents/skills/vikhyath-os/SKILL.md`; `vikhyath adapters status\|render [--check]\|install\|uninstall`; bootstrap records host runs and shows the CLI path in L0; every entry skill names `config/verification.yaml`; README Codex command `codex plugin add` (H-4). D-042. |
| Result | One entry-skill set (11 skills) packaged for four hosts; no logic in adapters; honest status per host. |
| Tests | 228/228 (10 new in `tests/hosts/test_hosts.py`; 3 opt-in skipped). Doctor 49/0, validate 22/0. |
| Acceptance | ✔ adapters import no routing/state/context code · ✔ every adapter output references the verification policy; none contains MCP, Chrome DevTools, screenshot or Playwright enablement · ✔ Claude hooks = SessionStart bootstrap only · ✔ manifests match `VERSION` · ✔ Cursor/Antigravity install → INSTALLED, bootstrap record → RUNTIME_VERIFIED, uninstall removes only managed skills, foreign skills never overwritten · ✔ launcher bootstrap works with no central install (plugin source fallback) and records the run. |
| Host status on this machine | Claude Code: **FILES_PRESENT** — the v1.0.1 plugin is no longer in `installed_plugins.json` (ECC, UI/UX Pro Max and Open Design are installed directly); RUNTIME_VERIFIED needs the plugin installed from this branch and one session start. Codex, Cursor, Antigravity: **FILES_PRESENT**, host CLIs/apps absent → NOT VERIFIED (D-024). |
| Deviations | No Codex/Cursor hooks (formats not verified on this machine); skills instruct `vikhyath bootstrap --host <name>` instead. Version stays 1.0.1 until the release phase (P26/P27). |
| Evidence | `docs/evidence/P19-P22/run.md` |
| Rollback | `git revert` of the M6 commit; `vikhyath adapters uninstall --host cursor|antigravity`. |

## M6 review summary

M6 (P19–P22) packaged the OS for Claude Code, Codex, Cursor and Antigravity from one entry-skill set: generated manifests, a SessionStart-only Claude hook, a launcher that works with or without the central install, user-level installs for Cursor/Antigravity, and §34 status levels where RUNTIME_VERIFIED is recorded only from a real host bootstrap. 228 tests. **Open:** install the plugin from this branch in Claude Code to reach RUNTIME_VERIFIED there. **Next: M7 (P23 dashboard → P24 update/rollback → P25 diagnostics/benchmarks → P26 docs → P27 integration)** after user review.

## P23 — Dashboard (Agent Office) · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | `config/dashboard.yaml` (6 rooms, 31 seats covering all 63 capabilities); `vikhyath/dashboard/{agents,api,server}.py`, `demo_events.json`, `static/{index.html,office.css,office.js}`; `vikhyath dashboard [--demo] [--open] [--port] [--idle-minutes]`; package data in `pyproject.toml`. D-043. |
| Result | The approved Agent Office runs live from the project's event log: agents light up on CAPABILITIES_SELECTED / CONTEXT_LOADED, wait on dependencies, block with a reason on failed verification, blocked tasks or risk alerts, and return to idle after 10 min; Browser QA is always disabled, Simplicity off unless asked for. Hosts and runtimes panels; activity log. |
| Tests | 236/236 (8 new in `tests/dashboard/test_dashboard.py`; 3 opt-in skipped). |
| Acceptance | ✔ every capability seated exactly once (validator catches double/missing seats) · ✔ fixture event sequences → exact states and bubble text · ✔ server binds 127.0.0.1 only, serves page + 5 JSON endpoints, 404 on path escape, 405 on POST (read-only) · ✔ stops by itself when idle, emitting DASHBOARD_STARTED / DASHBOARD_SLEEPING · ✔ no web fonts or external scripts (offline; CSP `default-src 'self'`) · ✔ event text inserted as text, never markup. |
| Deviations | Rendering is checked by the API/state tests and a served-page check, not by browser automation (D-035). A YAML pitfall was caught by the tests: a bare `off` parses as false, so fixed states are quoted. |
| Evidence | `docs/evidence/P23/run.md` |
| Rollback | `git revert` of the P23 commit. |

## P24 — Update & rollback · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | `vikhyath/update/{__init__,core}.py`; CLI `vikhyath update`, `vikhyath rollback`, `vikhyath gc`; `tests/update/test_update.py`. D-045. |
| Result | Explicit, checked upstream updates that never touch the running bundle until everything passes; one-command rollback to a verified bundle; retention of current, previous and recent failures. |
| Tests | 242/242 (6 new; 3 opt-in skipped). |
| Acceptance | ✔ broken update (upstream removes a file a bundled skill links to) → failed with "dangling reference …", `current` unchanged · ✔ interrupted build (KeyboardInterrupt mid-transform) → `current` unchanged and intact · ✔ good update → new bundle active, `previous` = old, diff lists the changed bundled path and affected capability, the bundle records its new pin · ✔ rollback refuses a tampered bundle · ✔ gc keeps current/previous/recent failed, removes the rest and orphaned runtimes · ✔ real bundles: `rollback` → previous and back (`--to`), `gc --dry-run` lists 3 old bundles + 2 stale Graphify runtimes. |
| Deviations | The network fetch path (`git ls-tree` on a blobless clone) is not exercised offline; the same logic runs on local trees in the tests. Normal commands make no network calls (verified offline since P12: this machine has no DNS). |
| Evidence | `docs/evidence/P24/run.md` |
| Rollback | `git revert` of the P24 commit. |

## P25 — Diagnostics & measured benchmarks · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | `vikhyath/diagnostics/benchmark.py` (`compare`, `render`, `--compare --out`); `vikhyath/diagnostics/doctor.py` (Host Environment + Supply Chain sections, redacted output); `vikhyath/bundle/closure.py` (absolute imports); rule excluding `graphify/tests/test_skillgen.py`; `docs/benchmarks/RESULTS.md`; `tests/unit/test_p25.py`. D-046. |
| Result (measured on this machine) | Every turn: OLD **31,792** est. tokens (ECC 2.2.3, Open Design 1.0.0, UI/UX Pro Max 2.13.0 descriptions) vs NEW **915** (own 13 skills/agents + 1,196 B L0). 22 spec tasks: OLD ≈ **1,019,809** vs NEW ≈ **176,408** est. tokens (**83 % less**). Routing **22/22**, p50 0.23 ms / p95 0.34 ms; L0 2 ms; L1+L2 p50 12 ms. Doctor on this machine: 50 passed, 0 failed, 10 warnings (3 separate plugins; Chrome DevTools/Playwright/Open Design/shadcn MCP servers enabled by them; 1 duplicate UI/UX design file). |
| Tests | 245/245 (3 new; 3 opt-in skipped). Bundle `a6c52114bc4d` known-good, 2,582 files, self-tests pass. |
| Acceptance | ✔ benchmarks measured, estimates labelled · ✔ planted host MCP (chrome-devtools) and `~/.claude.json` servers reported; secret-looking values never printed · ✔ the closure trace now catches function-local absolute imports (found and fixed one real gap). |
| Deviations | OLD per-task cost counts only the skill files a task triggers, not MCP tool schemas or hook output, so OLD is a lower bound. OLD routing accuracy is not measured (the host model chooses; no deterministic baseline). |
| Evidence | `docs/evidence/P25/run.md`, `docs/benchmarks/RESULTS.md` |
| Rollback | `git revert` of the P25 commit. |

## P26 — Documentation, migration and the Agylite rename · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | Rename (D-044): package `agylite/`, CLI `agylite` (+ `vikhyath` alias), `~/.agylite` / `.agylite/` with pre-rename fallbacks, `AGYLITE_*` env (`VIKHYATH_HOME` still read), skills `agylite-*`, plugin `agylite@agylite-marketplace`, launcher `bin/agylite` (+ `bin/vikhyath`); 17 docs in `docs/architecture/` (incl. VERIFICATION_POLICY); `docs/migration/V1_TO_V2.md`; README, CLAUDE.md, AGENTS.md, CONTRIBUTING, CHANGELOG (2.0.0) rewritten; VERSION 2.0.0; Claude marketplace file generated by the adapter; CI checks `adapters render --check`. |
| Result | Docs describe the system as built, with measured numbers; the v1 claims ("zero vendoring", "runtime tested", "route to ECC") are gone. Bundle `07cd36edb5d9` (the rename changed transformed text only). |
| Tests | 245/245 (home fallback test covers fresh, legacy-only and both). Doctor 50/0, validate 22/0, adapter files current. |
| Deviations | The GitHub repository keeps its name (`Vikhyath-thelazycoder/vikhyath-ai-engineering-os`) until the owner renames it; audit and plan history keep the original names. |
| Rollback | `git revert` of the rename and docs commits; the `vikhyath` alias and legacy paths keep old setups working. |

## P27 — Integration, offline, hosts, final report · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Changes | `tests/integration/test_end_to_end.py` (whole flow with outbound network blocked); `route --project`; doc 22 §9 checklist closed; `docs/FINAL_REPORT.md`. |
| Result | 246 tests pass (+3 opt-in real-runtime Graphify tests pass against bundle `07cd36edb5d9`); doctor 50/0, validate 23/0, bundle intact, registry valid, adapter files current. Hosts: all FILES_PRESENT (Claude Code has v1.0.1 installed, others absent) — recorded as a limitation, not claimed. |
| Acceptance | ✔ end-to-end offline flow · ✔ doc 22 §9 all ✔ · ✔ final report with measured results and every limitation. |
| Evidence | `docs/evidence/P27/run.md`, `docs/FINAL_REPORT.md` |

## M7 review summary

M7 delivered the Agent Office dashboard, explicit update/rollback/gc, measured OLD vs NEW benchmarks (83 % fewer
est. tokens; 31.8k → 0.9k per turn; routing 22/22), host and supply-chain diagnostics, the Agylite rename with
compatibility aliases, the full documentation set and the final integration report. **The v2 transformation is
complete on the branch; release (merge to main, tag v2.0.0, reinstall in hosts) awaits the user's go-ahead.**

## P28 — Upstream tracking (weekly automatic updates) · COMPLETED (2026-10-11)

| Item | Detail |
|---|---|
| Request | User: upstreams update daily/weekly — the OS should pick up new commits automatically. |
| Changes | `config/upstreams.yaml`; `agylite/update/track.py` (check, mirror, latest, promote, schedule); `update()` accepts a mirror; CLI `agylite update --check \| --latest [--due] [--track] \| --promote \| --schedule install\|remove`; `.github/workflows/upstream-updates.yml`; `tests/update/test_track.py`. D-047. VERSION 2.1.0. |
| Result | Live check against GitHub: 11 of 15 upstreams have new commits since the 2026-10-03 audit. Real apply of Taste: 8 commits, mirror created, 13 bundled paths fetched, all checks passed, switched to bundle `392b5d77ffb9` (~75 s). |
| Tests | 251/251 (5 new, with real local git repositories as upstreams: check → latest via mirror, second run "none", incremental fetch of a further commit, broken upstream commit refused with current unchanged, due/manual/releases policies, promote, LaunchAgent opt-in; policy covers all 15 upstreams with their branches). |
| Rollback | `git revert`; `agylite rollback`; `agylite update --schedule remove`; disable the workflow. |

## P4–P27 — summary (file-level tasks: [FILE_LEVEL_PLAN.md](FILE_LEVEL_PLAN.md))

| Phase | Objective (outline) | Key acceptance criteria (outline) |
|---|---|---|
| P4 Core foundation | Python core package + `vikhyath` CLI; declared deps (fixes E-1); test harness; `scripts/{doctor,validate,benchmark}` become compatibility wrappers (§69). | Fresh venv: install + `vikhyath --version` + existing 20 tests pass (version assertions de-hardcoded). |
| P5 Provenance | Machine-readable provenance schema (§36), third-party notices tree (D-002), provenance validator. | Every bundled file traceable to repo+SHA+path+hash. |
| P6 Bundling | staging → extract → validate → bundle pipeline (§35); duplication control (§37); MCP stripping; known-good bundle snapshot. Replaces zero-vendor checks (D-001). | Bundle reproducible from pins; hashes match provenance; no MCP in bundle. |
| P7 Registry | One registry with full §13 metadata; retires `config/capabilities.yaml`, `integrations/*.yaml`, priority duplication (C-1). | Single source; schema-validated; web-QA classification CORE/OPTIONAL/FALLBACK recorded (§23A.13). |
| P8 Routing | Deterministic router per §15 (classification → domain → subdomain → capability set); semantic retrieval fallback only. | Spec routing examples (§14, §23A.14, §70) produce expected capability sets as tests. |
| P9 Context | Levels 0–3, budgets (§47), hash-keyed session cache (§17). | Measured bytes per level; cache hit skips reread. |
| P10 Project state | Compact `.vikhyath/` state, plan index (§49), decisions (§50–52), change classification (§54–56). | State read ≪ full docs; plan reconciliation test. |
| P11 Isolation | Structural per-project isolation (§2.4). | Concurrent A/B/C test: no cross-project reads. |
| P12 Codebase | Graphify integration as codebase-intelligence layer (§4.8, §23); failure fallback (§74). | Affected-file query narrows code surface on a fixture repo. |
| P13 Engineering | Engineering capabilities from ECC/Addy/Agency/gstack/Karpathy/Unlazy/Ponytail; lifecycle UNDERSTAND→RECONCILE; completion states; project doc templates; requirements question engine (§53). | Scenarios A, B, C (§70) route and plan correctly. |
| P14 Design | Unified design domain (OpenDesign + Taste + UI/UX Pro Max + merged Appllama native-mobile rules, D-034); inspectable anti-slop criteria (§27) as local token checks. | Scenario D routes to design only; mobile requests load the native rules; no duplicate design rules. |
| P15 Testing | Testing domain; **local test-first** verification engine (D-035): impact-based test selection, execution, diagnosis, reruns, static/build/security/a11y/perf checks, machine-readable evidence; browser only as a logged per-project exception the user operates. | Webhook change selects the right local suites; **no browser process ever started**; evidence recorded in project state. |
| P16 SEO | SEO domain; isolated, pinned BeyondSEO runtime with health/start/stop/test; evidence model FACT…UNKNOWN (§28). | Scenarios E, F, I; core env untouched by SEO deps. |
| P17 Media | Media domain from Brag (§29). | Scenario H (launch video) activates no backend capabilities. |
| P18 Observability | Event model (§30), history, redaction (§78–79). | Events emitted for full routing lifecycle; no secrets in logs. |
| P19–P22 Hosts | Thin adapters for Claude Code, Codex, Cursor, Antigravity (§33); separate statuses "files installed" vs. "host runtime verified" (§34). | Per-host evidence; no business logic in adapters. |
| P23 Dashboard | **Agent Office** (approved design D-043, `docs/design/agent-office-mockup.html`): pixel office, one agent per capability with live state from the event log; loopback-only, read-only, no daemon (§31–32). | Starts on demand, sleeps on idle, agent states follow a fixture event sequence exactly; reflects real state. |
| P24 Update/rollback | `vikhyath update` / `rollback` (§41–42). | Simulated broken update rolls back bundle+registry+provenance atomically. |
| P25 Diagnostics/benchmarks | Complete doctor (§59); measured token & performance benchmarks, OLD vs NEW (§92–93). | Benchmarks are measured, labeled estimates where tokenizer unavailable. |
| P26 Documentation | `docs/` per §80–83; README/CONTRIBUTING/SECURITY rewritten; migration guide (§69). | Docs describe the actual final architecture. |
| P27 Integration & report | Final test matrix (§91), offline validation (§45), host validations, final report (§95). | Every acceptance criterion in §94 has evidence or a recorded limitation. |

---

## Resume here (next session)

1. `main` is released (v2.0.0 → v2.1.1); all phases M0–M7 and P28 are complete. No build work remains.
2. Central install done on this machine (2026-10-11): `~/.agylite`, bundle `2502140a790a` known-good, 0 errors; doctor 50/0.
   Add `export PATH="$HOME/.agylite/core/bin:$PATH"` to the shell profile.
3. Claude Code plugin `agylite@agylite-marketplace` v2.1.1 installed; **RUNTIME_VERIFIED** (SessionStart hook ran
   2026-10-11T08:34:45Z). The v1 plugin is removed.
4. All network checks VERIFIED 2026-10-11: live SEO crawl (owner's GitHub page and `example.com`) and Graphify
   `test_security` 60/60 (docs/evidence/P16, P25). Nothing open; Codex/Cursor/Antigravity runtime checks only if
   those hosts get installed. Tests: `python -m unittest discover -s tests`.

## Change history

| Date | Phase | Change |
|---|---|---|
| 2026-10-03 | P0 | Plan created; 28 phases defined (D-004); P0 completed; P1 set as next. Licensing made non-blocking (D-002). |
| 2026-10-03 | P0 | D-005: selective real extraction (actual files copied/adapted into the bundle; no reference-only capabilities). |
| 2026-10-03 | M1 | D-006: dependency closure (selected content pulls in everything it needs). D-007: 8 review milestones. M1 started. |
| 2026-10-03 | P1 | P1 completed: upstream audit, license inventory, security audit, pins (D-008). P2 started. |
| 2026-10-03 | P2 | P2 completed: domain model, extraction rules + per-file matrix, closure 0 open, duplication & runtime matrices. P3 started. |
| 2026-10-03 | P3 | P3 ready for verification: cross-cutting audits, target architecture, D-009…D-022, file-level plan; M1 awaiting user review (Q-1 blocks P6). |
| 2026-10-03 | M1 | Gate passed (D-025). Q-1 → build at install (D-023); Q-3 → NOT VERIFIED where host absent (D-024). M2/P4 started. |
| 2026-10-03 | P4 | P4 completed: `vikhyath` package + CLI (pyproject, Python ≥3.10, PyYAML declared), doctor 52/0 (50 legacy + 2 env), validate 27/0, measured `benchmark --baseline` (121,523 B ≈ 30,380 est. tokens), wrappers kept (§69), 32/32 tests, CI installs the package. Evidence: docs/evidence/P4/run.md. P5 started. |
| 2026-10-03 | P5 | P5 completed: shared rule engine `vikhyath/bundle/rules.py` (matrix regenerated byte-identical), §36 provenance records + validator (2,644 planned records, all valid, hashes = audited blob SHAs), `third_party/licenses.json` + generated `THIRD_PARTY_NOTICES.md` (12 MIT, 2 Apache-2.0), 45/45 tests. P6 started. |
| 2026-10-03 | P6 | P6 completed: `vikhyath bundle fetch/build/verify/list`, gstack template renderer (strong anchors), targeted rewrites with drift detection, hard MCP-config check, closure on transformed output, atomic activation with `previous`, `scripts/install`. Known-good bundle `c98667e034f7`: 2,594 files, 0 errors, Unlazy + UI/UX Pro Max self-tests pass from the bundle; **fresh networked install reproduces the identical bundle id** (153 MB sparse download, 1m54s). D-026 (single-link files), D-027 (render gaps/debts → P13–P17). 60 tests. Evidence: docs/evidence/P6/run.md. P7 started. |
| 2026-10-03 | P7 | Plan audit (user request): header, P3 heading, P4–P6 result sections, chronological history; FILE_LEVEL_PLAN "As built" notes for P5/P6 and D-027 duty in P13–P17; summary/doc 08 counts corrected. |
| 2026-10-03 | P7 | P7 completed: 62 capability cards + rendered L1 CARD.md, `vikhyath/registry` (schema, loader, generator), `registry.yaml` generated into every bundle (rebuilt `c98667e034f7`, valid), `vikhyath registry` CLI; retired `config/capabilities.yaml`, `integrations/*.yaml`, `domain-model.yaml`; priorities → role-named hierarchy + domain defaults (D-028). 79 tests, doctor 45/0, validate 20/0. Evidence: docs/evidence/P7/run.md. **M2 completed; awaiting user review before M3.** |
| 2026-10-04 | M3 | User started M3 ("lets do and finish M3 now"); M2 accepted. P8 started. |
| 2026-10-04 | P8 | P8 completed: routing config v2 + deterministic router + `vikhyath route` (D-029); 19 spec scenarios pass with expected and forbidden sets; p95 0.333 ms; 96 tests, doctor 45/0, validate 20/0. Evidence: docs/evidence/P8/run.md. P9 started. |
| 2026-10-04 | P9 | P9 completed: budgets config, L0–L3 assembly, section loading, per-bundle context index, per-session cache, project identity, `vikhyath bootstrap`/`context` (D-030). All 12 measured scenarios within L1/L2 budgets; second load all hits with 0 bytes read. 114 tests. Evidence: docs/evidence/P9/run.md. P10 started. |
| 2026-10-04 | P10 | P10 completed: compact project state, plan index, reconciliation into the one plan, §55 impact, §25 transitions, §53 questions, decision memory, 9 doc templates, CLI (D-031). Google Maps scenario lands in the booking phase with no new file; state read ≪ docs. 130 tests. Evidence: docs/evidence/P10/run.md. P11 started. |
| 2026-10-04 | P11 | P11 completed: path guard, per-project locks, atomic writes wired into context and project state (D-032). Doc 14 tests pass: 0 cross-project opens over six interleaved turns, no lost updates, no partial files, per-project cache keys. 141 tests. Evidence: docs/evidence/P11/run.md. P18 started. |
| 2026-10-04 | P18 | P18 completed: event envelope, redaction, per-project JSONL log, lifecycle emission, CEL-subset Beacon rule engine with correlation (77 rules, 535/535 embedded tests), `vikhyath events` (D-033). 160 tests. Evidence: docs/evidence/P18/run.md. **M3 completed; awaiting user review before M4.** |
| 2026-10-05 | A-1 | Amendment A-1 (user specification update; "You can continue"): audit first (doc 22), then implemented. Appllama `dd5caae` pinned as 15th upstream, APPLLAMA_STATUS = MERGED (3 files + LICENSE into design/frontend + design/motion; appllama-usage, MCP, simulator loop, duplicates excluded) — D-034. Local test-first verification: `config/verification.yaml`, `vikhyath/verify/policy.py`, `testing/browser-exception` DISABLED_BY_POLICY, `testing/local-verification`, `testing/evidence`, 15 browser/visual upstream files excluded, router `browser: disabled\|exception-requested`, state verification block + per-project exception log, `BROWSER_EXCEPTION_REQUESTED`, validate policy checks — D-035, D-036 (D-020 superseded). Every phase re-evaluated ("Amendment A-1 — phase reconciliation"). 165 tests, validate 23/0, doctor 45/0; known-good bundle `cb0635dbf824` (2,583 files, 0 errors). Evidence: docs/evidence/D034-D036/run.md. |
| 2026-10-10 | M4 | User started M4 ("yes start m4"); M3 and A-1 accepted. Branch `feat/v2-os-transformation` fast-forwarded to `main` (A-1). P12 started. |
| 2026-10-10 | P12 | P12 completed: Graphify runtime wrapper + `vikhyath runtime`/`codebase`, affected files + related tests within the 12-file code surface, §74 structural fallback, router `impact` step (schema v3), doctor runtime check, codebase entry skill; `graphify/serve.py` preserved (D-037). 184 tests, doctor 47/0, validate 23/0; known-good bundle `68fcabbc8e1b`. Evidence: docs/evidence/P12/run.md. P13 next. |
| 2026-10-10 | P13 | P13 completed: lifecycle config + route lifecycle, domain adaptation transform clears all D-027 debts, Unlazy gates + central Stop hook, thin entry skills/agents, workflows/ retired (D-038). 194 tests; bundle `2d1356913230`. Evidence: docs/evidence/P13/run.md. P14 next. |
| 2026-10-10 | P14 | P14 completed: UI/UX Pro Max runtime + `vikhyath design search|system|check`, design-token limits, design entry skill, design files covered by the policy transform (D-039). 199 tests; bundle `495f026f381e`. Evidence: docs/evidence/P14/run.md. P15 next. |
| 2026-10-10 | P15 | P15 completed: `vikhyath verify`/`test` — project command detection, impact-based selection, run + rerun + diagnosis, evidence JSON + state + events, exception records only (D-040). 209 tests. Evidence: docs/evidence/P15/run.md. **M4 completed; awaiting user review before M5.** |
| 2026-10-10 | M5 | User started M5 ("start with the next milestone, which is 5"); M4 accepted. |
| 2026-10-10 | P16 | P16 completed: shared venv helper, BeyondSEO runtime + `vikhyath seo run|evidence|authorize`, evidence labels over capture quality, live-site authorization gate (D-041). Upstream suite core-only 340 passed / 9 browser-only failures. Evidence: docs/evidence/P16/run.md. |
| 2026-10-10 | P17 | P17 completed: Brag media runtime (`vikhyath media plan|music-cues`), brag-slim default, scenario H media-only. 218 tests. Evidence: docs/evidence/P17/run.md. **M5 completed; awaiting user review before M6.** |
| 2026-10-11 | M6 | User started M6 ("m6 we go bro"); M5 accepted (live SEO crawl blocked by this machine's DNS; success path checked offline). |
| 2026-10-11 | P19–P22 | Host adapters completed: one entry-skill set, generated manifests, SessionStart-only Claude hook, launcher, Cursor/Antigravity user-level install, §34 status with recorded host runs (D-042). 228 tests. Evidence: docs/evidence/P19-P22/run.md. **M6 completed; awaiting user review before M7.** |
| 2026-10-11 | P23 (plan) | User approved the **Agent Office** dashboard design (pixel office, one agent per capability, live states) from mockup v2; FILE_LEVEL_PLAN P23 rewritten with files, state machine, API and constraints (D-043); mockup saved as `docs/design/agent-office-mockup.html`; "Resume here" section added. |
| 2026-10-11 | Name | User chose the product name **Agylite** (D-044); rename scheduled in P26. |
| 2026-10-11 | P23 | P23 completed: Agent Office dashboard (live states from events, loopback-only, read-only, idle exit, demo replay). 236 tests. Evidence: docs/evidence/P23/run.md. P24 next. |
| 2026-10-11 | P24 | P24 completed: `vikhyath update|rollback|gc` with dangling-reference check, atomic switch, per-bundle evidence (D-045). 242 tests. Evidence: docs/evidence/P24/run.md. P25 next. |
| 2026-10-11 | P25 | P25 completed: OLD vs NEW benchmark (83% fewer est. tokens over 22 spec tasks; 31.8k → 0.9k per turn; routing 22/22), host/supply-chain doctor checks with redaction, absolute-import closure (D-046). 245 tests; bundle `a6c52114bc4d`. Evidence: docs/evidence/P25/run.md. P26 next. |
| 2026-10-11 | P26 | P26 completed: Agylite rename with compatibility aliases (D-044), 17 architecture docs, migration guide, README/CLAUDE/AGENTS/CONTRIBUTING/CHANGELOG rewritten, VERSION 2.0.0. 245 tests. P27 next. |
| 2026-10-11 | P27 | P27 completed: end-to-end offline integration test, checklist closed, final report (246 tests). **M7 completed; v2 transformation complete on the branch; awaiting user review and release go-ahead.** |
| 2026-10-11 | Release | Merged to `main`, tagged and pushed `v2.0.0` (user go-ahead). |
| 2026-10-11 | P28 | P28 added on request and completed: automatic upstream tracking — daily check, weekly/monthly apply of new commits only through every check, CI pull request, optional Mac job (D-047). 251 tests. |
| 2026-10-11 | Trial | First hands-on trial (docs/TRY_AGYLITE.md) passed; its gaps fixed in v2.1.2: product routing by interface/exposure, phase roll-up + `last_task`, session-tagged and task events, enforced BLOCKING questions, empty template P1, `.agylite/` not a code change. 257 tests. |
| 2026-10-11 | Trial 2 | Second hands-on trial on v2.1.2 passed with no failures (route high, question gate, T-1.1, phase roll-up, session-tagged events, test-first). Polish in v2.1.3: same-status changes are no-ops; readable `events list`. 259 tests. |
