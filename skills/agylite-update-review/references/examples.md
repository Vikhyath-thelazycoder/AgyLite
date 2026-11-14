# Update review: a good and a weak review

Both are for the same update: two upstreams have new commits. The repository names, commit ids and numbers below
are made up to show the shape.

## Weak

> I reviewed the updates. Both upstreams have some improvements and bug fixes. Everything looks good and the tests
> pass, so I've approved both. The bundle is now up to date!

Why it is weak:

- "some improvements" does not say what an agent will do differently after the update.
- Both were approved without asking the owner. The owner decides, one upstream at a time.
- "Everything looks good" hides whether anything was removed or made always-on.
- No commit ids, no candidate bundle, no Tier 0 result, no risk.

## Good

> Review of 14 Nov: 2 upstreams with new commits; candidate bundle `4c1f09aa77e2`; Tier 0 PASS
>
> | Upstream | Verdict | What changes for agents | Risk | Recommendation |
> |---|---|---|---|---|
> | review-kit@`a81c3f2` | improves | Findings must now state the input that triggers the defect; a new check for unhandled promise rejections | None seen: adds 14 lines to the primary skill, no step removed | approve |
> | plan-kit@`77de014` | worse | The "write acceptance criteria" step is removed; a new section tells the agent to always open a tracking issue through a hosted service | Plans lose their acceptance criteria; the new section needs a tool that Agylite excluded | reject |
>
> **review-kit** — the lines that decide it (`skills/review/SKILL.md`):
> `+ Each finding states the concrete input or sequence that triggers it.`
> `+ - Unhandled promise rejections in async handlers`
>
> **plan-kit** — the lines that decide it (`skills/plan/SKILL.md`):
> `- 4. Write acceptance criteria for every task.`
> `+ ## Tracking` / `+ Always create an issue for the plan before you start.`
> The commit message calls this "streamline planning". For Agylite it removes the step that the lifecycle's PLAN
> exit depends on.
>
> Two questions follow, one per upstream.

After the owner answered (approve review-kit, reject plan-kit):

> Approved: `agylite update --approve review-kit@a81c3f2` — done.
> Rejected: `agylite update --reject plan-kit@77de014 --reason "removes the acceptance-criteria step; adds an
> always-on step that needs an excluded tool"` — done.
> Pending: none.

Why it is good:

- Each row says what changes for an agent, in concrete terms.
- The verdict on the second upstream goes against its commit message, and the quoted lines show why.
- The owner was asked per upstream, and only then anything was switched.
- The reason for the rejection is recorded in the command.
