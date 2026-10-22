---
name: observability-updates
description: Review upstream updates with the owner — run agylite update --review, judge each change in plain words, ask one question per upstream, and approve or reject only what the owner chose.
---

<!-- Agylite-authored (MP6 §3). The procedure is the agylite-update-review entry skill; this guide is what routing loads. -->

# Upstream updates: review → benchmark → the owner approves

1. `agylite update --review --due --tier1-plan` (or read `~/.agylite/updates/review-<date>/REPORT.md` if it is under
   24 hours old). Nothing is activated by the review.
2. Per upstream, security fast-track first: read the section diffs of PRIMARY files and say whether the change
   **improves** the guidance agents get (clearer steps, new checks, fixed errors), is **neutral** (wording, format) or
   is **worse** (removes steps, couples to a tool Agylite excluded, adds always-on behaviour). For each NEW_SKILL:
   does it fill a gap? Recommend `REFERENCE` (keep watching), `ADOPT as L3`, or `ADOPT as primary` (only with Tier 1).
   For NEEDS_RULES: check `<repo>-proposed-rules.patch` against the upstream tree, apply it on a branch, re-run review.
3. One table: | Upstream | Verdict | What changes for agents | Risk | Recommendation |, then one question per upstream
   (use the host's question tool): approve · approve after Tier 1 (show the session count and cost estimate) ·
   reject (with a reason) · hold.
4. Run `agylite update --approve <repo>@<sha>` or `--reject <repo>@<sha> --reason "…"` only for what the owner chose.
   Never run Tier 1 without the owner's yes on the estimate; never approve on your own.
