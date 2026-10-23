---
name: agylite-diagrams
description: Architecture, sequence, workflow, data-flow, lifecycle, ERD, class, tree, timeline and waterfall diagrams of a system or this codebase as checked standalone HTML with Archify (`agylite diagram`). Explainer pages only when asked.
---

# Agylite Diagrams

1. **Route:** `agylite route "<request>"` → `engineering/diagrams`; load Archify's skill (`agylite skill load archify/archify`).
2. **This codebase:** first `agylite codebase update`, then `agylite codebase query|path|explain` for evidence, then
   follow Archify's `references/repository-authoring.md`. Every node must cite files.
3. **Author** the candidate in `.archify/<type>-<slug>-<timestamp>/` (suggest adding `.archify/` to `.gitignore`;
   never edit `.gitignore` without asking). Unsure of the type: `agylite diagram guide "<scenario>"`.
4. **Done** when `agylite diagram finalize <type> <candidate.json> <output.html> --json` exits 0: validate, deliver,
   strict check and the headless Chrome browser-check. The browser-check runs whenever Chrome is present; without
   Chrome it is reported as skipped and `agylite verify --diagram <output.html>` records it as BLOCKED, never passed.
   Its receipts are the evidence.

Explainer pages are made only when the user asks for one. Agylite manages Archify updates.

Verification policy: tests and browser (`config/verification.yaml`, D-049); for diagrams that is Archify's own
browser-check of the rendered page (`diagram_verification`); no MCP.

End your answer with the output of `agylite used` (what this work used).
