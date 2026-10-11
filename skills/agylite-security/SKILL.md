---
name: agylite-security
description: Security-sensitive changes (auth, secrets, payments/webhooks, input handling, OWASP) — route to engineering/security and testing/security and prove fixes with negative tests run locally.
---

# Agylite Security

1. **Route:** `agylite route "<request>" --paths <files…>`; security work selects `engineering/security` (project
   security outranks every methodology) and `testing/security`. Load them with `agylite context <id>…`.
2. **Understand the surface:** `agylite codebase affected --paths <files…>`; check recorded security decisions
   with `agylite decide list --kind security`.
3. **Fix with negative tests** (lifecycle rule for SECURITY_CHANGE): forged/expired signatures rejected,
   unauthorised access denied, injection inputs neutralised, secrets never logged. Each test must fail without the fix.
4. **Verify locally:** `agylite verify` (tests + dependency audit + secret scan where available); record the
   evidence. Record new security rules as decisions: `agylite decide add --kind security …`.

Never paste real secrets into prompts, logs or evidence. No browser or screenshot verification.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
