# engineering/spec-review — Spec review

Fresh-context review of a spec, plan, RFC or design doc before code, then keep-or-fix resolve of each finding.

- **Use when:** spec review, design doc review, rfc review, fresh eyes review, goldfish review, review the plan before
- **Activation:** on-demand · priority 50 · context L2
- **Needs:** runtime none; codebase analysis first
- **Loads:** 30 bundled files; entry points: bootstrap_orchestrator, codebase_details, comprehension, design_critic, egm-bootstrap, egm-brainstorm (+10 more)
- **Done means:** every reviewer ran as a fresh subagent (no same-context review) · each finding resolved as kept (with reason), fixed or asked · report written to the working directory
- **Related:** engineering/planning, engineering/review · **Fallback:** —
