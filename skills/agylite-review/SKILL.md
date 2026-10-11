---
name: agylite-review
description: Pre-merge code review of the current change — scope drift, correctness, security, tests — using the routed engineering/review capability and local evidence.
---

# Agylite Review

1. **Route:** `agylite route "review this change" --paths $(git diff --name-only origin/<base>)`, then
   `agylite context engineering/review` (plus any security/testing capability it selects).
2. **Scope:** compare the diff with its plan task (`agylite plan locate`); report scope creep and missing
   requirements first.
3. **Impact:** `agylite codebase affected` — review the changed files and what they reach, not the whole repo.
4. **Evidence:** `agylite verify --plan` shows the checks the change needs; findings about untested behaviour
   name the missing test.
5. **Report** findings by severity with `file:line`, each with a concrete failure scenario. Never approve on
   "looks fine": a passing `agylite verify` run is the minimum.

Simplicity review (Ponytail-derived) only when the user asks for it.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
