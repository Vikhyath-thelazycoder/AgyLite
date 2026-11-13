# Phase 9 parity report

Paid Tier 1 run on the frozen candidate bundle `3509e18d39d9`, model `claude-opus-5-5`, n = 3 per task and arm.
Finished 2026-11-05. 9 suites, 378 sessions, **$119.29** in total (chunk 1 $32.86 · chunk 2 $15.97 · chunk 3 $70.46).
Nothing has been fixed yet. Fixes start only after the owner's go-ahead.

Retained = (AgyLite − no skill) ÷ (original − no skill), with the sign flipped when lower is better. Same ≥ 0.90 ·
near 0.70–0.90 · regressed < 0.70 or worse than no skill · inconclusive when the original's own gain is within
run-to-run noise. Full rows: `PARITY_LEDGER.md`. The evidence behind each finding is in `IMPLEMENTATION_PLAN.md` →
"Paid-run findings".

## Results per suite

| suite | run | metric: no skill / original / AgyLite (retained) | verdict | cost no skill / original / AgyLite |
|---|---|---|---|---|
| eng-ponytail | 20261023T160330Z | correct 0.905 / 1 / 1 (1) · safe 0.857 / 1 / 1 (1) · src_loc 55 / 21.5 / 23 (0.955) | inconclusive | $3.27 / $2.71 / $3.42 |
| eng-addy | 20261023T163255Z | expectations 0.931 / 1 / 0.986 (0.8) | inconclusive | $2.35 / $2.95 / $3.12 |
| eng-pocock | 20261023T193809Z | expectations 0.532 / 0.753 / 0.768 (1.07); without tdd 0.465 / 0.908 / 0.744 (≈ 0.63) | inconclusive | $3.62 / $5.44 / $6.02 |
| research | 20261103T140925Z | success 0.917 / 1 / 1 (1) | inconclusive | $1.61 / $1.49 / $1.82 |
| youtube | 20261104T133241Z | hook_verdict 34.1 / 71.4 / 51.6 (**0.467**) · on_screen_beats 0.333 / 1 / 1 (1) | **regressed** | $1.60 / $3.69 / $3.03 |
| browser-qa | 20261104T141003Z | defects reported 5 / 5 / 5 · fixed 5 / 5 / 5 | same | $0.63 / $1.40 / $0.69 |
| design-extract | 20261104T141924Z | color_hit 0 / 0.667 / 0.667 (1) · font_hit 0 / 1 / 1 · DESIGN.md sections 0 / 8 / 8 | same / inconclusive | $0 (no model) |
| diagram-archify | 20261104T143729Z | validation 0.533 / 1 / 1 (1) · semantic 0.067 / 0.333 / 0.2 (0.5) · first pass 0 / 0.133 / 0 (0) | inconclusive, **no-skill arm invalid (C3-2)** | $5.88 / $6.97 / $7.73 |
| design-taste | 20261104T182103Z | inspector FAIL 6.78 / 0 / 0 (1) · lint FAIL 11.8 / 0.111 / 0 (1.01) · judge 6.5 / 6.96 / 6.97 (1.04) | inconclusive (inspector, lint same) | $6.87 / $20.94 / $22.07 |

**In short:** one real regression, youtube (C2-1). No other suite is worse than the original, but most verdicts
are "inconclusive" because the original's own gain is small against n = 3 noise. The eng-pocock suite mean hides a
gap on action prompts where the agent never opens the saved hook (C1-10). diagram-archify cannot be trusted until
its no-skill arm is isolated (C3-2). AgyLite costs 5–26% more than the original on 6 suites (ponytail +26%,
research +22%, pocock +11%, archify +11%, addy +6%, taste +5%), mainly from the oversized hook and the fixed L0
overhead (C1-2, C1-3). It is cheaper on youtube (because it iterates less, C2-1) and on browser-qa.

## Cells that ran the old installed engine (C1-1)

- eng-addy: 12 of 18 AgyLite cells (the 2026-10-24 resume had `~/.agylite/core/bin` on PATH).
- eng-pocock: 5 of 30 AgyLite cells (they explain the to-spec dip: old engine 0.4 / 0.2, new 1.0 / 1.0).
- eng-ponytail, every chunk 2 suite and every chunk 3 suite: none. Every AgyLite trace has the Ponytail L0 of the
  engine under test.

## Findings

| id | suite | kind | finding (one line) |
|---|---|---|---|
| C1-1 | all | measurement | the plugin launcher prefers an installed `agylite` on PATH over the snapshot under test |
| C1-2 | all | cost + quality | the hook payload is over Claude Code's ≈ 10k-char hook limit, so it is saved to a file and the agent may never open it |
| C1-3 | all | cost | +3.6–4k tokens of fixed overhead on the first call (L0, plugin skill and agent descriptions, route cards) |
| C1-4 | all | cost | needless `agylite verify` / `route` / `context` calls and the hook-file read add turns |
| C1-5 | eng | routing | odd routes (a Ponytail task routed to slides) and a 3rd skill added to BUG_FIX and TDD |
| C1-6 | harness | robustness | run dirs linked into a scratchpad that a reboot cleared |
| C1-7 | harness | robustness | checkout `.staging/upstream` off its pins on 8 repos |
| C1-8 | harness | counter | `capabilities_selected` counts an event the engine never writes (always 0) |
| C1-9 | eng-pocock | grading | the original tdd asks questions instead of acting, now scored 0 |
| C1-10 | eng-pocock | quality | = C1-2 in action: diagnosing-bugs 0.46 vs original 0.79 when the hook file is not opened |
| C1-11 | eng-pocock | routing | = C1-5: diagnosing-bugs and tdd load a 3rd skill and become the largest payloads |
| C1-12 | ledger | bookkeeping | a ledger row records HEAD at append time, not the run's start commit |
| C2-1 | youtube | **regression** | AgyLite iterates hookscore 4–18× vs the original's 21–30× and settles on weaker hooks (hypothesis: Ponytail lite) |
| C2-2 | research | cost | = C1-2: +$0.33 over the original for the same score |
| C2-3 | browser-qa | gate | the browser runtime was missing, so 9 cells failed at $0 (installed, resumed) |
| C2-4 | docs | run script | a non-pass verdict exits non-zero; zsh `which` defeats the C1-1 guard |
| C2-5 | env | robustness | the Mac slept mid-run; run under `caffeinate -ims` |
| C3-1 | design-taste | measurement | 2 original inspector values lost to a stdout parse (both 0 in the saved report) |
| C3-2 | diagram-archify | **validity** | the no-skill arm found Archify outside the workspace in 11/15 cells; every no-skill validation pass is a leaked cell |
| C3-3 | diagram-archify | quality | AgyLite leaves out the `auth` participant in cache-miss 3/3 (original 1/3) (hypothesis: Ponytail lite, as C2-1) |
| C3-4 | diagram-archify | noise | the web-runtime first-pass gap rests only on the model visual reviewer's `label-overlap` |
| C3-5 | archify, taste | routing | = C1-5: diagram prompts route MEDIA/SECURITY with engineering cards; taste task 1 adds an Addy skill and scores like no skill |
| C3-6 | archify, taste | cost | = C1-2/C1-3: +5% (taste) and +11% (archify) over the original; the hook file was opened in every cell |
| C3-7 | design-taste | validity | 1 of 9 original cells never invoked its skill |
| C3-8 | ops | robustness | the run died when the Claude Code session that launched it closed |

## Fix order

1. **Measurement first, so later numbers can be trusted:** C3-2 (isolate every arm from skill sources in the home
   folder; a no-skill cell that reads one fails), C1-1 (pin the launcher; the isolation check fails an old engine),
   C3-1 (read the inspector's report.json), C3-7 and C1-9 (count "skill not used" and "asked instead of acting").
2. **C1-2 / C1-10 / C2-2:** keep the hook under ≈ 9,000 chars with the lead skill inline. This is the biggest
   lever on quality (eng-pocock action prompts) and cost.
3. **C1-5 / C1-11 / C3-5:** at most lead + partner skill; diagram and page prompts route one skill, the right change
   type and no engineering cards.
4. **C2-1 / C3-3:** test exempting creative, youtube and diagram routes from Ponytail lite (or add an explicit
   iterate rule to those skills).
5. **C1-3, C1-4 / C3-6:** smaller L0 and fewer plugin descriptions; no needless verify/route/context calls.
6. **Robustness and bookkeeping:** C1-6, C1-7, C1-8, C1-12, C2-3, C2-4, C2-5, C3-8.

Then re-measure: diagram-archify in all three arms (its no-skill arm is invalid), and every other suite in the
AgyLite arm only (`--arms agylite --reuse-from <run>`).

## Step 3 re-measurement (AgyLite arm, started 2026-11-12)

Run with `AGYLITE_BENCH_HOME=real` (the owner's OAuth token could not be set; Read deny rules + leak check on), engine
commit 7d0d9fb, bundle 6c8821eb00b7, other arms reused from Phase 9.

| suite | run | expectations / metric: no skill / original / AgyLite | Phase 9 AgyLite | cost AgyLite (original) |
|---|---|---|---|---|
| eng-pocock | 20261112T094703Z | 0.53 / 0.75 / **0.86** (retained 1.48) | 0.77 | $4.95 ($5.44; Phase 9 $6.02) |
| eng-addy | 20261112T100647Z | 0.93 / 1.00 / **0.95** (0.954 with the re-parsed cell) | 0.986 (12/18 on the old engine) | $3.54 ($2.95; Phase 9 $3.12) |
| eng-ponytail | 20261112T123734Z | correct 0.90 / 1 / **1**, safe 0.86 / 1 / **1**, src_loc 55 / 21.5 / **22.9** | same | $4.17 ($2.71; Phase 9 $3.42) |
| research | 20261112T124734Z | 0.92 / 1 / **1** | 1 | $1.42 ($1.49; Phase 9 $1.82) |
| youtube | 20261112T125040Z | hook 34.1 / 71.4 / **70.7** (retained 0.98), beats 0.33 / 1 / **1** | 51.6 (regressed) | $4.03 ($3.69; Phase 9 $3.03) |
| browser-qa | 20261112T130526Z | 5 / 5 / **5** reported and fixed | 5 | $0.67 ($1.40; Phase 9 $0.69) |
| design-extract | 20261112T130745Z | colour 0 / 0.67 / **0.67**, font 0 / 1 / **1**, sections 0 / 8 / **8** | same | $0 |
| design-taste | 20261112T130841Z (stopped by the owner, 5/9 cells) | inspector 6.8 / 0 / **0**, lint 11.8 / 0.11 / **0**; judge not run | 0 / 0, judge 6.97 | $11.80 for 5 cells (Phase 9 $22.07 for 9) |

eng-pocock per task: diagnosing-bugs 0.75 / 0.75 (was 0.46 in Phase 9: C1-10 fixed by the hook cap), grilling, to-spec,
to-tickets 0.83–1.00 (= or > original), tdd#2 1.00 vs original 0.00 (the original asks; the "regressed" label is the
retention formula on a negative original gain), tdd#1 0.27 = original (both ask: the fixture already strips emoji).
Measurement fixes (2026-11-12, after the run): the C1-9 "asked" counter now checks the last three paragraphs, since
Ponytail's closing lines follow the question; Addy's grader parser takes the last valid JSON object (one eng-addy cell,
tdd#2 run 1, was ungraded because the grader wrote a draft and then a corrected reply: 3/3 on re-parse).

Findings from the re-measurement: youtube's hook regression is fixed (70.7 vs 71.4). eng-addy's only gap is C1-2:
code-review#1 misses Addy's per-finding severity labels in 2 of 3 cells (AgyLite groups findings under Must/Should
fix). eng-ponytail quality is unchanged but costs 22% more than Phase 9 (0.199 vs 0.163 per cell; original 0.129):
the router now picks 2-5 capabilities per prompt, where Phase 9 picked none.

### Step 3 verdicts (closed 2026-11-13, owner decisions)

| suite | verdict |
|---|---|
| eng-pocock | **beats original** (0.86 vs 0.75; Phase 9 0.77, C1-10 fixed) |
| eng-addy | **near parity** (0.954 vs 1.00); the gap is C1-2 severity labels, carried to Step 4 |
| eng-ponytail | **parity on quality**, cost +22% vs Phase 9 (router now picks 2-5 capabilities); carried to Step 4 |
| research | **parity** (1 = 1) |
| youtube | **parity** (hook 70.7 vs 71.4, regression fixed) |
| browser-qa | **parity** (5/5) |
| design-extract | **parity** (same as original) |
| design-taste | **partial parity accepted by the owner**: 5/9 cells, inspector 0 and lint 0 (= Phase 9), no judge score; not re-run |
| diagram-archify | **deferred to Step 5** by the owner (needs the OAuth token and the per-session HOME) |
