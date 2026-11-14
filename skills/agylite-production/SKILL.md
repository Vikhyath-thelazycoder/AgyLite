---
name: agylite-production
description: Release readiness — plan completion, verification evidence, changelog and rollback — through engineering/release and testing/release-verification.
disable-model-invocation: true
---

# Agylite Production

If the prompt arrived with an `Agylite route:` line, the route is already done: skip the route step and use the
capabilities that line lists.

1. **Route:** `agylite route "prepare the release" --paths <files…>` → `engineering/release`,
   `testing/release-verification`; load with `agylite context --request "<the user's request>" <id>…`.
2. **Plan completion:** every task the release claims is VERIFIED with evidence (`agylite plan show <phase>`);
   PARTIAL or unverified items block the release unless the user accepts the risk
   (`agylite decide add --kind process --topic "risk acceptance" …`).
3. **Verify:** `agylite verify` on the release candidate — tests, types, lint, build, security checks — with the
   evidence file recorded.
4. **Ship notes:** changelog from the commit list; migration and rollback steps written before deploying.

No deploy step is taken without the user's explicit go-ahead.

Verification: tests, types, lint and build for every change; UI work also needs `agylite verify --browser`
(policy: `config/verification.yaml`). No MCP.

End your answer with the output of `agylite used` (what this work used).
