---
name: agylite-testing
description: Verify a change locally and test-first (impacted tests, types, lint, build, plus the browser check for UI work) with recorded evidence from `agylite verify` — use when asked to test, verify or check that a change works.
disable-model-invocation: true
---

# Agylite Testing

Produces a verification result that someone else can check: each check with its result and counts, and an evidence
file. It never calls something verified because the code reads correctly or a page looks right.

## Use when · Not for

- Use when: a change has to be tested or verified, tests are missing, or a check is failing.
- Not for: making the change itself → `agylite-engineering` · exploratory QA of a running app → gstack `/qa` ·
  a release decision → `agylite-production` · judging how a UI looks → `agylite-design`.

## Before you start

- You need the change (the working tree, or `--paths <files…>`) and, when there is one, its plan task id (`T-…`).
- Policy: `config/verification.yaml`. Tests, types, lint and build for every change; UI work also runs the browser
  check. Evidence is a command with its exit code and counts.

## Steps

1. **Plan the checks.** `agylite verify --plan` (default: the working-tree changes; or `--paths <files…>`).
   Expect: the impacted tests by kind (unit, api, integration, idempotency, security, regression) and the project's
   typecheck, lint and build. Move on when: you know which checks will run and which changed behaviour has no test.
2. **Write the missing tests first.** Every changed behaviour needs a test that fails without the change. For a
   bug fix, write the failing regression test before the fix. Move on when: each new test has been seen failing
   for the right reason.
3. **Run.** `agylite verify --task <T-id>` (or `agylite test` for tests only; `--all` runs the full suites, which is
   for releases). Expect: each check PASSED, FAILED, NOT_TESTED or BLOCKED, and an evidence file
   `.agylite/evidence/<time>.json`. A failed test is rerun once; a pass on the rerun is reported as flaky and
   still counts as FAILED. A missing tool is BLOCKED, not passed.
4. **UI work.** `agylite verify --browser [--url <page>] [--flows .agylite/flows.yaml]` (it runs by itself for style
   and markup changes). Write the task's flows as plain steps in the flows file. The project's own headless E2E
   script runs only with `--include-e2e`.
5. **Fix and rerun** from the `diagnosis` lines until every selected check is PASSED.
6. **Record.** `agylite plan set-status <T-id> VERIFIED --evidence <evidence file>`.

## Output

```markdown
Verification: <PASSED | FAILED | BLOCKED>

| Check | Result | Counts | Note |
|---|---|---|---|
| tests | PASSED | 212 passed, 0 failed | impacted tests only |
| typecheck | PASSED | | |
| browser | BLOCKED | | browser runtime not installed |

Evidence: <path of the evidence file>
Tests added: <name — what it proves>, or "None"
Not covered: <behaviour with no automated check, and why>, or "None"
```

The overall result is PASSED only when every selected check is PASSED. Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every result in the table comes from a command that ran in this session, with its counts.
- Each new test was seen failing without the change. A test that cannot fail proves nothing.
- A flaky test is reported as FAILED, a missing tool as BLOCKED, and a thing only a person can judge (look and
  feel) as NOT_TESTED. None of them is reported as passed.
- No "looks correct" and no screenshot or look at the page alone as evidence; the browser check is a command with
  recorded results.
- Tests assert behaviour (inputs and results), not that a function was called or that a mock returned its mock.
- "Not covered" names what is still unverified. It is not left empty to make the result look complete.

## Stop and ask

- A check needs a tool or runtime that is not installed, and installing it needs the network or a large download.
- Making a test pass would mean changing the test's expectation, not the code: say which and why.
- A failure is in code the change did not touch.

## When something fails

| What you see | What to do |
|---|---|
| `verify --plan` selects no tests | The change has no covering test. Write one (step 2); do not report "nothing to run" as passed. |
| A check is BLOCKED | Name the missing tool. Reading the code does not replace the check. |
| The browser runtime is missing | `agylite runtime status`; `agylite runtime install browser` when the user agrees. Until then the browser check is BLOCKED. |
| A test fails only sometimes | It is flaky: find the cause (time, order, shared state, network). Do not rerun until green. |
| The suite was red before your change | Report those failures as there before, with their output, apart from the ones you caused. |
| No plan task exists | Run `agylite verify` without `--task` and say that no task was recorded. |

## References (read only when needed)

- `references/examples.md` — a good and a weak verification report, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
