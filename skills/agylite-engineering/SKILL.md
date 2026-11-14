---
name: agylite-engineering
description: Engineering work (features, fixes, refactors, migrations) through the Agylite lifecycle — route, understand, plan, implement, test, verify, reconcile — with only the routed engineering capabilities loaded.
disable-model-invocation: true
---

# Agylite Engineering

If the prompt arrived with an `Agylite route:` line, the route is already done: skip the route step and use the
capabilities that line lists.

The OS decides which engineering guidance applies; this skill only tells you how to follow it.

1. **Route:** `agylite route "<request>" --paths <files…>`. Load only what it selects:
   `agylite context --request "<the user's request>" <capability-id>…`.
2. **Follow `lifecycle`** from the route result (`config/lifecycle.yaml`), step by step, running each step's
   commands and meeting its `exit` before moving on:
   UNDERSTAND (`agylite codebase affected`, `agylite plan locate`) → PLAN (`agylite plan reconcile`) →
   IMPLEMENT → TEST → VERIFY (`agylite verify`) → RECONCILE (`agylite plan set-status … --evidence …`).
   Bug fixes start with a failing regression test; refactors keep tests green before and after.
3. **Substantial work** (several files or deliverables): write `GATES.md` first and use
   `agylite gates lint|check GATES.md` (Unlazy completion discipline).
4. **Done** means VERIFIED with recorded evidence — never "should work".

Rules: guidance order is the route's `capabilities` order (user requirements → project security → architecture
→ methodology → specialists → review → simplicity). A screenshot
alone is never evidence. Simplicity review only when the user asks for it.

Verification: tests, types, lint and build for every change; UI work also needs `agylite verify --browser`
(policy: `config/verification.yaml`). No MCP.

End your answer with the output of `agylite used` (what this work used).
