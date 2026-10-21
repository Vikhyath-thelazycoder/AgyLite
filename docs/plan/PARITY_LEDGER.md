# Parity ledger

Generated from `docs/plan/parity-ledger.json` by `agylite/benchmark/quality/ledger.py`; do not edit by hand.
Retained gain = (AgyLite − no skill) ÷ (original − no skill), sign flipped when lower is better. Same ≥ 0.90 ·
near 0.70–0.90 · regressed < 0.70 or worse than no skill · inconclusive within run-to-run noise.

| date | suite | n | bundle | AgyLite commit | model | metric: no skill / original / AgyLite (retained, verdict) | verdict | cost no skill / original / AgyLite | fix applied | next step |
|---|---|---:|---|---|---|---|---|---|---|---|
| 20261021T162010Z | eng-ponytail | 1 | 5cb3ec9b15bc | 87037736 | claude-opus-5-5 | correct: 1 / 1 / 1 (—, same)<br>safe: 0.857 / 1 / 1 (1, inconclusive)<br>src_loc: 45.4 / 19.6 / 42.6 (0.11, inconclusive)<br>wrote_tests: 1 / 1 / 1 (—, same)<br>cost: 0.173 / 0.131 / 0.163 (0.233, inconclusive) | **inconclusive** | $1.21 / $0.92 / $1.14 | — (Phase 2 baseline: AgyLite v2.1.6 + MP1) | Phase 4: Ponytail lite rules in L0, ponytail-review first; Phase 3 whole skills |
| 20261021T163611Z | eng-addy | 1 | 5cb3ec9b15bc | e3bb448e | claude-opus-5-5 | expectations_passed: 0.903 / 1 / 0.958 (0.571, inconclusive) | **inconclusive** | $0.74 / $1.02 / $0.95 | — | — |

## Notes

- 20261021T172159Z eng-pocock: stopped by a usage limit after 9/30 cells; resume: `agylite benchmark --quality --tier 1 --suite eng-pocock --yes-spend --resume /Users/vikhyathmgowda007/.agylite/benchmarks/quality/20261021T172159Z-eng-pocock`
- Correction to the 20261021T172159Z eng-pocock note: that stop was a false positive of the usage-limit detector (the agent's rate-limiter spec mentioned HTTP 429), fixed in c1db1da. 9/30 cells were recorded; the run was not resumed.
- 2026-10-21: the owner withdrew permission for paid Tier 1 sessions. eng-pocock (9/30), design-taste and diagram-archify baselines are not run; eng-addy keeps one ungraded cell (debugging#1, original arm). These suites are reported as not measured, never as Same.
- design-extract, youtube, browser-qa, research and routing (Tier 1) wait for their instruments and AgyLite capabilities (Phases 5-7), and for paid sessions to be allowed again.
