---
name: agylite-production
description: Release readiness — plan completion, verification evidence, changelog and rollback — through engineering/release and testing/release-verification.
---

# Agylite Production

1. **Route:** `agylite route "prepare the release" --paths <files…>` → `engineering/release`,
   `testing/release-verification`; load with `agylite context --request "<the user's request>" <id>…`.
2. **Plan completion:** every task the release claims is VERIFIED with evidence (`agylite plan show <phase>`);
   PARTIAL or unverified items block the release unless the user accepts the risk
   (`agylite decide add --kind process --topic "risk acceptance" …`).
3. **Verify:** `agylite verify` on the release candidate — tests, types, lint, build, security checks — with the
   evidence file recorded.
4. **Ship notes:** changelog from the commit list; migration and rollback steps written before deploying.

No deploy step is taken without the user's explicit go-ahead. No browser or screenshot verification.

Verification policy: tests and browser (`config/verification.yaml`, D-049) — UI work also needs `agylite verify --browser`; no MCP.

End your answer with the output of `agylite used` (what this work used).
