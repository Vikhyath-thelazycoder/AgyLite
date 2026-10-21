---
name: agylite-design
description: UI/UX and visual design work — direction, design systems, typography, motion, native mobile — through the routed design capabilities, the UI/UX Pro Max engine and local design-token checks.
---

# Agylite Design

1. **Route:** `agylite route "<request>" --paths <files…>` and load only what it selects with
   `agylite context --request "<the user's request>" <id>…` (mobile/native requests load the merged native-mobile rules in `design/frontend`).
2. **Decisions first:** `agylite decide list --kind design`; keep to recorded brand and system decisions, and
   record new ones with `agylite decide add --kind design …`.
3. **Engine** (read-only unless persisted):
   `agylite design search "<query>" --domain style|color|typography|ux …`,
   `agylite design system "<product + tone>" [--persist]` (writes `design-system/` in this project only).
4. **Verify locally:** `agylite design check` (accent hues, grey families, radii, fonts against
   `config/design.yaml`) plus the project's component/a11y tests. Never verify by screenshot or browser; report
   look-and-feel judgements as NOT_TESTED for the user to confirm.

Design requests do not activate engineering or SEO capabilities unless the route selects them.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
