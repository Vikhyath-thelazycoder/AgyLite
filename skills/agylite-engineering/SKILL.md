---
name: agylite-engineering
description: Engineering work (features, fixes, refactors, migrations) through the Agylite lifecycle — route, understand, plan, implement, test, verify, reconcile — with only the routed engineering capabilities loaded.
---

# Agylite Engineering

The OS decides which engineering guidance applies; this skill only tells you how to follow it.

1. **Route:** `agylite route "<request>" --paths <files…>`. Load only what it selects:
   `agylite context <capability-id>…`.
2. **Follow `lifecycle`** from the route result (`config/lifecycle.yaml`), step by step, running each step's
   commands and meeting its `exit` before moving on:
   UNDERSTAND (`agylite codebase affected`, `agylite plan locate`) → PLAN (`agylite plan reconcile`) →
   IMPLEMENT → TEST → VERIFY (`agylite verify`) → RECONCILE (`agylite plan set-status … --evidence …`).
   Bug fixes start with a failing regression test; refactors keep tests green before and after.
3. **Substantial work** (several files or deliverables): write `GATES.md` first and use
   `agylite gates lint|check GATES.md` (Unlazy completion discipline).
4. **Done** means VERIFIED with recorded evidence — never "should work".

Rules: guidance order is the route's `capabilities` order (user requirements → project security → architecture
→ methodology → specialists → review → simplicity). Verify locally (tests, types, lint, build); never by browser
or screenshot. Simplicity review only when the user asks for it.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
