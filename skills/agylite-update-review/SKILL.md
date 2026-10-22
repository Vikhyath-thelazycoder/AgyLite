---
name: agylite-update-review
description: Review new upstream commits with the owner — what each changes, whether it is useful to Agylite, how to adopt it without breaking anything or lowering the benchmarks — and switch only what the owner approves.
---

# Agylite Update Review

1. **Review:** `agylite update --review --due --tier1-plan` (or read the latest
   `~/.agylite/updates/review-<date>/REPORT.md` if it is less than 24 hours old). The review classifies every commit,
   diffs the sections agents read, builds and checks a candidate bundle and runs Tier 0 on it. It never activates.
2. **Judge, per upstream** (security fast-track first):
   - PRIMARY section diffs: does the change **improve** the guidance (clearer steps, new checks, fixed errors), is it
     **neutral** (wording, formatting), or is it **worse** (removes steps, couples to a tool Agylite excluded, adds
     always-on behaviour)?
   - NEW_SKILL: does it fill a gap? Compare its description with the proposed capability. Recommend `REFERENCE`
     (keep watching), `ADOPT as L3`, or `ADOPT as primary` (the last only with a Tier 1 run).
   - NEEDS_RULES: check `<repo>-proposed-rules.patch` against the upstream tree, apply it on a branch, re-run
     `agylite update --review --repo <repo>`.
3. **Ask:** one table — | Upstream | Verdict | What changes for agents | Risk | Recommendation | — then one question
   per upstream (use the host's question tool): approve · approve after Tier 1 (show the session count and cost
   estimate from the Tier 1 plan) · reject (with a reason) · hold.
4. **Act only on the owner's choice:** `agylite update --approve <repo>@<sha>` (refuses a stale review) or
   `agylite update --reject <repo>@<sha> --reason "…"`. `agylite update --pending` lists what is waiting.

Never run Tier 1 without the owner's yes on the cost estimate. Never approve on your own. Rules and rewrites are the
only way to adapt upstream content; never edit upstream files to make a check pass.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
