---
name: spec-review
description: Review a spec, plan, RFC or design doc before code in one pass with EGM's eight lenses, then keep, fix or ask on each finding.
---

# Spec review (one pass)

EGM's reviewer checklists, run by you in one pass. Do not start subagents. A full EGM review (about 9 Opus
subagents, 10–20× the cost) runs only when the user asks for it by name ("full EGM", "goldfish review"):
then use `agylite skill load egm/egm-review` instead of this guide.

1. **Read the whole doc first.** Then write a paraphrase in 2–5 sentences under **What this proposes** and **How the
   existing system works, per this doc**. A section you cannot paraphrase is a Blocker.
2. **Decide the kind of doc:** feature spec, implementation plan, or both. Lens H applies only to plan sections.
3. **Go through the lenses in order.** For each finding note the severity (Blocker, Major or Nit), the section or
   lines, what is wrong and what to do.
   - **A. Zoom out.** Does it solve the root problem or a symptom? Features, options or abstractions for a
     speculative future (YAGNI)? A new helper or module that already exists? Search the code before you say so.
     Caching, queues or partitioning with no measured bottleneck? Pseudocode where interfaces and data flow belong?
   - **B. Comprehension.** Project-specific terms, services or tools used but not defined or linked (general
     engineering terms are fine)? Steps that assume setup the doc never states? "It handles this automatically"
     without saying how?
   - **C. Design critic.** Required questions unanswered: goals, success metric, cost, risks, rollout? Claims about
     performance, data or external systems with no evidence? Failure modes, single points of failure, scaling
     limits or security gaps the design creates but does not handle?
   - **D. Hidden trade-off.** A bottleneck or compromise accepted as unavoidable when splitting the parts or putting
     something between them would remove it? Errors only logged, with no retry, backpressure or fallback? Say "no
     false compromise found" when there is none.
   - **E. Code check.** Every file, function, endpoint, table or flag the doc says exists now: does it? A doc that
     describes current behaviour the code does not have is a Blocker. Constants, environment variables, retries and
     edge cases in the code that the doc leaves out? Files the plan will create are not findings.
   - **F. Structure.** Required sections missing (use the project's template in `docs/` if it has one), skipped
     heading levels, broken tables or code blocks, dead links.
   - **G. Style.** Hype ("flawless", "revolutionary"), buzzwords, filler, opinions about code quality, two words for
     one idea, and claims stronger than the evidence. For each hedge or caveat say drop, calibrate or move it.
   - **H. Ready to build** (plan sections only). For each step: do you know exactly which file to change, and what
     and how? Flag every choice left to the implementer: data type, API signature, error strategy, migration,
     test.
4. **Resolve each finding** with the author: **fixed** (edit the doc), **kept** (state the reason) or **asked**
   (one question to the user, when the author's intent decides it). Do not fix a Major or Blocker silently.

## Report

- The paraphrase from step 1.
- Findings sorted Blocker → Major → Nit, each with its lens letter, scope, problem and recommendation.
- How each finding was resolved: fixed, kept (with reason) or asked.
- Lenses with no findings, by letter, so the reader sees they were checked.

## Before you finish

- Every "exists now" reference in the doc was checked against the code, not from memory.
- No subagent was started unless the user asked for a full EGM review.
- Nothing outside the reviewed doc was changed.
