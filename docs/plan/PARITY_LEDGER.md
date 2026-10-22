# Parity ledger

Generated from `docs/plan/parity-ledger.json` by `agylite/benchmark/quality/ledger.py`; do not edit by hand.
Retained gain = (AgyLite − no skill) ÷ (original − no skill), sign flipped when lower is better. Same ≥ 0.90 ·
near 0.70–0.90 · regressed < 0.70 or worse than no skill · inconclusive within run-to-run noise.

| date | suite | n | bundle | AgyLite commit | model | metric: no skill / original / AgyLite (retained, verdict) | verdict | cost no skill / original / AgyLite | fix applied | next step |
|---|---|---:|---|---|---|---|---|---|---|---|
| 20261021T162010Z | eng-ponytail | 1 | 5cb3ec9b15bc | 87037736 | claude-opus-5-5 | correct: 1 / 1 / 1 (—, same)<br>safe: 0.857 / 1 / 1 (1, inconclusive)<br>src_loc: 45.4 / 19.6 / 42.6 (0.11, inconclusive)<br>wrote_tests: 1 / 1 / 1 (—, same)<br>cost: 0.173 / 0.131 / 0.163 (0.233, inconclusive) | **inconclusive** | $1.21 / $0.92 / $1.14 | — (Phase 2 baseline: AgyLite v2.1.6 + MP1) | Phase 4: Ponytail lite rules in L0, ponytail-review first; Phase 3 whole skills |
| 20261021T163611Z | eng-addy | 1 | 5cb3ec9b15bc | e3bb448e | claude-opus-5-5 | expectations_passed: 0.903 / 1 / 0.958 (0.571, inconclusive) | **inconclusive** | $0.74 / $1.02 / $0.95 | — | — |
| 20261021T192046Z | eng-ponytail | 1 | 52e8c1108c39 | f3541718 | claude-opus-5-5 | correct: 1 / 1 / 1 (—, same)<br>safe: 0.857 / 1 / 1 (1, inconclusive)<br>src_loc: 45.4 / 19.6 / 23 (0.867, inconclusive)<br>wrote_tests: 1 / 1 / 1 (—, same)<br>cost: 0.173 / 0.131 / 0.166 (0.158, inconclusive) | **inconclusive** | $1.21 / $0.92 / $1.16 | — | — |
| 20261021T192422Z | eng-addy | 1 | 52e8c1108c39 | f3541718 | claude-opus-5-5 | expectations_passed: 0.903 / 1 / 0.903 (0, inconclusive) | **inconclusive** | $0.74 / $1.06 / $0.96 | — | — |
| 20261021T192855Z | eng-pocock | 1 | 52e8c1108c39 | f3541718 | claude-opus-5-5 | expectations_passed: 0.47 / 0.745 / 0.572 (0.372, inconclusive) | **inconclusive** | $1.23 / $1.73 / $1.54 | — | — |
| 20261022T041927Z | design-extract | 1 | 22bf70be985e | 1248801b | claude-opus-5-5 | color_hit: 0 / 0.667 / 0.667 (1, inconclusive)<br>font_hit: 0 / 1 / 1 (1, same)<br>design_md_sections: 0 / 8 / 8 (1, same) | **inconclusive** | $0.00 / $0.00 / $0.00 | none needed: per site every metric is same (identical values in both arms) | pooled colour verdict is inconclusive only because site-to-site spread counts as noise; linear.app colour is missed by designlang itself in both arms |

## Notes

- 20261021T172159Z eng-pocock: stopped by a usage limit after 9/30 cells; resume: `agylite benchmark --quality --tier 1 --suite eng-pocock --yes-spend --resume /Users/vikhyathmgowda007/.agylite/benchmarks/quality/20261021T172159Z-eng-pocock`
- Correction to the 20261021T172159Z eng-pocock note: that stop was a false positive of the usage-limit detector (the agent's rate-limiter spec mentioned HTTP 429), fixed in c1db1da. 9/30 cells were recorded; the run was not resumed.
- 2026-10-21: the owner withdrew permission for paid Tier 1 sessions. eng-pocock (9/30), design-taste and diagram-archify baselines are not run; eng-addy keeps one ungraded cell (debugging#1, original arm). These suites are reported as not measured, never as Same.
- design-extract, youtube, browser-qa, research and routing (Tier 1) wait for their instruments and AgyLite capabilities (Phases 5-7), and for paid sessions to be allowed again.
