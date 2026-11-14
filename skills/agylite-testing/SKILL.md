---
name: agylite-testing
description: Verify a change locally and test-first — impacted tests, types, lint, build — with machine-readable evidence via `agylite verify`, plus the browser check for UI work.
disable-model-invocation: true
---

# Agylite Testing

1. **Plan:** `agylite verify --plan` (default: the working-tree changes; or `--paths <files…>`) lists the checks
   the change needs: the impacted tests by kind (unit, api, integration, idempotency, security, regression) plus
   the project's typecheck, lint and build.
2. **Missing tests first:** every changed behaviour needs a test that fails without the change (bug fixes: write
   the failing regression test before the fix).
3. **Run:** `agylite verify --task <T-id>` (or `agylite test` for tests only). Failed tests are rerun once;
   a pass on rerun is reported as flaky and still counts as FAILED. A missing tool is BLOCKED, not passed.
4. **Fix and rerun** from the `diagnosis` lines until PASSED; the evidence file
   (`.agylite/evidence/<time>.json`) and the plan status (`agylite plan set-status <T-id> VERIFIED --evidence <file>`)
   record the result.

A screenshot or a look at the page alone is never evidence; the browser check is a command with recorded results. The project's own
headless E2E script runs only with `--include-e2e`. UI work also runs the browser check: `agylite verify --browser [--url …]
[--flows .agylite/flows.yaml]` (automatic for style/markup changes; write the task's flows as plain steps). QA requests
go to gstack `/qa`. If only a human can judge something (look and feel), report it as NOT_TESTED.

Verification: tests, types, lint and build for every change; UI work also needs `agylite verify --browser`
(policy: `config/verification.yaml`). No MCP.

End your answer with the output of `agylite used` (what this work used).
