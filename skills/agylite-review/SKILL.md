---
name: agylite-review
description: Pre-merge code review (scope, correctness, security, tests) as numbered findings, each with file:line, a failure scenario and a fix — use when asked to review a diff, a branch or a pull request before it merges.
disable-model-invocation: true
---

# Agylite Review

Produces a review the author can act on without asking a question: a verdict, and numbered findings that each
name the line, the input that breaks it and the fix. It does not change the code unless asked, and it never
approves on "looks fine".

## Use when · Not for

- Use when: a diff, a branch or a pull request is to be reviewed before it merges.
- Not for: a spec or a plan document → the routed `engineering/spec-review` · a simplification audit → only when
  the user asks for one (`engineering/simplicity`) · a security change → `agylite-security` · how a UI looks →
  `agylite-design` · writing the fix → `agylite-engineering`.

## Before you start

- **Base branch.** `<base>` is the branch the change merges into; `git symbolic-ref --short
  refs/remotes/origin/HEAD` prints it (usually `origin/main`).
- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise:
  `agylite route "review this change" --paths $(git diff --name-only <base>)`, then
  `agylite context --request "<the user's request>" engineering/review` plus any security or testing capability
  the route selects.

## Steps

1. **Scope.** `agylite plan locate "<what the change is for>"`, then compare the diff with that task.
   Expect: two lists, what the diff does that was not asked (scope creep) and what was asked that the diff lacks.
   Move on when: both lists are written, even if empty.
2. **Impact.** `agylite codebase affected`. Expect: the changed files and the files and tests they reach. Read the
   code the change touches (callers, callees, tests), not just the diff.
3. **Evidence.** `agylite verify --plan` lists the checks the change needs; `agylite verify` runs them
   (policy: `config/verification.yaml`). A finding about untested behaviour names the missing test.
4. **Review.** Load `agylite skill load ponytail/ponytail-review` and follow its structure: number the findings in
   Must fix / Should fix / Nice to have, each with `file:line` and four parts: what it is, what goes wrong (a
   concrete failure scenario), the fix, and what happens if skipped. Then apply gstack's review checklists second
   (`agylite skill load gstack/review`).
5. **Several reviewers** (the route's `review_merge` is set: security, architecture or release joined): run them in
   parallel as fresh subagents, merge with `agylite:egm-synthesizer`, then resolve each finding with
   `agylite skill load egm/egm-resolve` (kept with reason / fixed / asked).

Severity:

- **Must fix** — a wrong result, lost data, a security hole, a crash, a broken build or a missing requirement, on
  an input that can really occur.
- **Should fix** — correct today but fragile: changed behaviour without a test, an unhandled error path, an
  unclear contract.
- **Nice to have** — naming, readability, a small simplification. At most five.

## Output

```markdown
## Review: <the change> — <BLOCK | APPROVE WITH FIXES | APPROVE>

Scope: <in scope | creep: … | missing: …>
Evidence: `agylite verify` → <counts per check> (<evidence file>)
Read beyond the diff: <files>

### Must fix
1. `path/file.py:42` — <what it is>
   - Goes wrong: <input or sequence> → <wrong result>
   - Fix: <the change>
   - If skipped: <consequence>

### Should fix
### Nice to have
### Not reviewed
<what you did not read or could not check, and why>
```

Verdict: BLOCK with any Must fix, a FAILED check or a missing requirement · APPROVE WITH FIXES with Should fix
only · APPROVE with neither and a passing `agylite verify`. An empty section says "None".

## Quality bar

Check each line before you answer:

- Every finding names a `file:line` you opened, and you re-read that line: the code does what the finding says.
- Every failure scenario has a concrete input or sequence. "Could cause issues" is not a scenario.
- No finding comes from the diff alone when the code around it already guards the case.
- No style preference presented as a defect, and nothing a linter or formatter already reports.
- No praise section and no general advice ("consider adding tests"): name the test and what it must assert.
- Zero findings is a valid result. Do not invent findings to fill a section.
- The verdict follows from the findings and the verify result, and "Not reviewed" is filled in honestly.

## Stop and ask

- The base branch or the thing to review is unclear.
- The diff is very large or mixes unrelated changes: propose a review per part.
- You are asked to fix the findings: say which ones you will fix before you edit.

## When something fails

| What you see | What to do |
|---|---|
| The base cannot be found | Ask for it, or use `main` and say that you did. |
| The diff is empty | Say so and ask what should be reviewed. |
| `plan locate` finds no task | Review against the request or the pull request text, and say there is no plan task. |
| `agylite verify` is FAILED or BLOCKED | The verdict cannot be APPROVE. Report the check and its output. |
| `skill load` does not know a skill | Go on without it, say which one was missing, and resolve findings by hand (kept with reason / fixed / asked). |
| No subagent tool on this host | Lead review only, and say so. |

## References (read only when needed)

- `references/examples.md` — a good and a weak finding for the same defect, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
