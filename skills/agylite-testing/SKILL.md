---
name: agylite-testing
description: Verify a change locally and test-first — impacted tests, types, lint, build — with machine-readable evidence via `agylite verify`; never by browser or screenshot.
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

Never verify by opening a browser, using Chrome DevTools or taking or reading screenshots. The project's own
headless E2E script runs only with `--include-e2e`. If only a human can judge something (look and feel), report
it as NOT_TESTED, or record a browser exception with `agylite verify exception --reason "…"` (the user operates
the browser; nothing is captured).

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
