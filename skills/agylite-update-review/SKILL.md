---
name: agylite-update-review
description: Review new upstream commits with the owner (what each changes for agents, whether it is useful to Agylite, how to adopt it without breaking anything or lowering the benchmarks) and switch only what the owner approves — use when asked to check, review or apply updates of the bundled upstream skills.
disable-model-invocation: true
---

# Agylite Update Review

Produces one decision table for the owner: per upstream, what the new commits change for agents, the risk and a
recommendation. It then switches exactly what the owner approves. It never approves on its own and never edits
upstream files to make a check pass.

## Use when · Not for

- Use when: new upstream commits are waiting, or the owner asks what changed upstream and whether to take it.
- Not for: changing Agylite's own skills or code → `agylite-engineering` · adding a new upstream (that is an audit
  with the owner, not an update) · running benchmarks for other reasons.

## Before you start

- You work on a candidate, never on the active bundle: the review does not activate anything.
- Know the rule for adapting upstream content: rules and rewrites are the only way. Upstream files are never
  edited by hand.

## Steps

1. **Review.** `agylite update --review --due --tier1-plan` (or read the latest
   `~/.agylite/updates/review-<date>/REPORT.md` if it is less than 24 hours old). Expect: every commit classified,
   the diffs of the sections agents read, a candidate bundle built and checked, and Tier 0 run on it.
   Move on when: you have read the report and the section diffs, not only the summary.
2. **Judge each upstream**, security fast-track first:
   - **PRIMARY section diffs:** does the change **improve** the guidance (clearer steps, new checks, fixed
     errors), is it **neutral** (wording, formatting), or is it **worse** (removes steps, couples to a tool Agylite
     excluded, adds always-on behaviour)? Quote the lines that decide it.
   - **NEW_SKILL:** does it fill a gap? Compare its description with the proposed capability. Recommend
     `REFERENCE` (keep watching), `ADOPT as L3`, or `ADOPT as primary` (the last only with a Tier 1 run).
   - **NEEDS_RULES:** check `<repo>-proposed-rules.patch` against the upstream tree, apply it on a branch, and run
     `agylite update --review --repo <repo>` again.
3. **Ask.** Show the table (see Output), then one question per upstream with the host's question tool: approve ·
   approve after Tier 1 (show the session count and the cost estimate from the Tier 1 plan) · reject (with a
   reason) · hold.
4. **Act only on the owner's choice.** `agylite update --approve <repo>@<sha>` (it refuses a stale review) or
   `agylite update --reject <repo>@<sha> --reason "…"`. `agylite update --pending` lists what is still waiting.

## Output

```markdown
Review of <date>: <n> upstreams with new commits; candidate bundle <id>; Tier 0 <PASS | FAIL>

| Upstream | Verdict | What changes for agents | Risk | Recommendation |
|---|---|---|---|---|
| <repo>@<short sha> | improves / neutral / worse | <the concrete change, in one line> | <what could break or cost more> | approve / approve after Tier 1 (<n> sessions, ≈ $<x>) / reject / hold |
```

Under the table, for each upstream that is not "neutral": the lines from the diff that decide the verdict. After
the owner's answers: what was approved, rejected or held, and the output of `agylite update --pending`.

## Quality bar

Check each line before you answer:

- Every verdict rests on diff lines you read and can quote, not on the commit message.
- "What changes for agents" says what an agent will do differently, not "updated documentation".
- A change that removes a step, adds always-on text or names a tool Agylite excluded is called worse, even when
  the commit calls it a cleanup.
- The cost estimate and the session count are shown before any Tier 1 run is offered.
- Nothing was approved, rejected or activated without the owner's answer for that upstream.
- A failing check is reported as failing. No upstream file was edited to make it pass.
- A stale review (more than 24 hours old, or the upstream moved) was run again, not reused.

## Stop and ask

- Every approval, rejection and hold: one question per upstream.
- Any Tier 1 run: it costs money, so the owner says yes to the estimate first.
- A proposed rules patch that changes what a skill tells agents to do.

## When something fails

| What you see | What to do |
|---|---|
| `--approve` refuses a stale review | Run the review again and show the owner what changed since. |
| The candidate bundle fails a check or Tier 0 | Report which check and which upstream. Recommend hold or reject; do not approve the rest blindly. |
| A rules patch does not apply | Say which hunk fails. Adjust the rule on a branch and run the review for that repo again. |
| The network is unavailable | The review cannot fetch. Say so; do not judge from an old report older than 24 hours. |
| The owner does not answer for one upstream | It stays pending. Do not choose for them. |

## References (read only when needed)

- `references/examples.md` — a good and a weak review table for the same update, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
