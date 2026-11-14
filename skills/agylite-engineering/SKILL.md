---
name: agylite-engineering
description: Code changes through the Agylite lifecycle (understand, plan, implement, test, verify, reconcile), finished only with recorded evidence — use when asked to build a feature, fix a bug, refactor or migrate code.
disable-model-invocation: true
---

# Agylite Engineering

Produces a finished code change: inside the asked scope, covered by tests that fail without it, verified by
`agylite verify`, and recorded in the project plan. It never reports work as done on a confident guess, and it does
not deploy.

## Use when · Not for

- Use when: a feature, bug fix, refactor, migration or any other change to code.
- Not for: reviewing a finished change → `agylite-review` · auth, secrets, payments or input handling →
  `agylite-security` · only running the checks → `agylite-testing` · a release → `agylite-production` · how a UI
  looks → `agylite-design`.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done: use the capabilities it lists.
  Otherwise run `agylite route "<request>" --paths <files…>` and load only what it selects:
  `agylite context --request "<the user's request>" <capability-id>…`.
- **Guidance order** is the route's `capabilities` order (user requirements → project security → architecture →
  methodology → specialists → review → simplicity). When two sources disagree, the earlier one wins.
- **`confidence: low`** in the route: confirm the intent with the user before you edit.

## Steps

Follow the route's `lifecycle` in the order it gives; the order below is the default. Two change types differ:
a **bug fix** writes its failing regression test (step 4) before step 3; a **refactor** runs step 5 once before
step 3 and must be green both times.

1. **Understand.** `agylite plan locate "<request>"`, then `agylite codebase affected --paths <files…>`.
   Expect: the plan phase the request belongs to, and lists of `files`, `tests` and `unknown`. Read the listed files,
   not the repository. Move on when: you can say in one sentence what will change and name the files and tests.
2. **Plan.** `agylite plan reconcile "<request>"`. Expect: a task id (`T-…`) with acceptance criteria. A structural
   choice is recorded with `agylite decide add --kind architecture --topic … --decision … --reason …`. For several
   files or deliverables, write `GATES.md` (one gate per deliverable, each with the command that proves it) and run
   `agylite gates lint GATES.md`. Move on when: every criterion can be checked by a test or a command.
3. **Implement.** `agylite plan set-status <T-id> IN_PROGRESS`. Make the smallest change that meets the criteria, in
   the patterns the surrounding code uses, and update the callers, fixtures, config and docs it breaks.
   Move on when: nothing inside the task is left as a placeholder, a stub or a "later".
4. **Test.** Every changed behaviour gets a test. Run it without the change and see it fail for the right reason,
   then with the change and see it pass. Move on when: each new test has been seen both failing and passing.
5. **Verify.** `agylite verify --task <T-id>`; add `--browser` for UI work (policy: `config/verification.yaml`; a
   screenshot alone is never evidence). Expect: each check PASSED, FAILED, NOT_TESTED or BLOCKED, and an evidence
   file `.agylite/evidence/<time>.json`. Fix from the `diagnosis` lines and rerun. With gates:
   `agylite gates check GATES.md`. Move on when: every selected check is PASSED.
6. **Reconcile.** `agylite plan set-status <T-id> VERIFIED --evidence <evidence file>`. Work you left out becomes a
   task: `agylite plan add-task <phase> "<title>" --acceptance "<criteria>"`.

## Output

The final answer has these parts, in this order:

1. **What changed** — one or two sentences about behaviour, not about files.
2. **Files** — each changed file with one line on why.
3. **Tests** — each test added or changed and what it proves.
4. **Evidence** — the verify command, the counts (passed, failed), the evidence file path; every NOT_TESTED or
   BLOCKED check by name, with the reason.
5. **Not done** — what was left out and the task id it now has, or "None".
6. The output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every acceptance criterion is met, and you can name the test or check that shows it.
- No "should work", "should now" or "likely fixed": each claim that something works points to a check that ran.
- No placeholder, stub, commented-out code or TODO for work inside the task.
- The diff holds nothing the task did not ask for: no extra refactor, rename, option or dependency.
- A BLOCKED or NOT_TESTED check is reported as that, never as passed.
- The plan says VERIFIED with the evidence file, or the answer states the real status and why.

## Stop and ask

- The request has two readings that lead to different code.
- The change would delete data, change a public interface, add a dependency or contradict a recorded decision
  (`agylite decide list`).
- The work is much larger than the request suggests: give the size and the smaller option.
- Any deploy, push or migration on a real system.

## When something fails

| What you see | What to do |
|---|---|
| `agylite` is not on PATH | Use the `cli:` path from the session bootstrap; `agylite doctor` shows what is wrong. |
| Route says `unmatched: true` | Tell the user in one line that no capability covers it; work from `fallback_guidance`. |
| `codebase affected` prints a `notice` | The graph was not used. Say so, and treat `unknown` entries as unknown, not as unaffected. |
| No plan or project state | `agylite project init`, then step 2. |
| A check is BLOCKED (tool missing) | Report it as BLOCKED with the tool's name. Reading the code is not a replacement. |
| A test passes only on the rerun | It is flaky and counts as FAILED: fix the test or the cause. |
| A check fails in code you did not touch | Report it as a failure that was there before, with its output. Fix it only if asked. |
| Three real attempts and still red | Stop. `agylite plan set-status <T-id> BLOCKED`, and report what you tried and what you saw. |

## References (read only when needed)

- `references/examples.md` — a good and a weak final answer for the same bug fix, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
