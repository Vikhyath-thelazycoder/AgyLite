---
name: agylite-routing
description: Route a task to the minimum Agylite capabilities with the deterministic `agylite route` command, then load only their context.
---

# Agylite Routing

Routing is done by the OS core, not by reading this file. Do not pick capabilities by hand and do not load every skill.

## Steps

1. **Route.** Run, from the project directory:

   ```bash
   agylite route "<the user's request>" --brief          # one line
   agylite route "<the user's request>"                  # full JSON
   ```

   Add `--paths <files…>` when the request touches known files, `--new` / `--existing` when the project stage is
   known, and `--capability <id>` only when the user explicitly names a capability.

2. **Load context for the routed capabilities only** (levels L1 → L2; L3 only when needed):

   ```bash
   agylite context <capability-id>…
   ```

3. **Follow the result.**
   - `capabilities` are listed in guidance order (`config/priorities.yaml`: user requirements → project security →
     project architecture → methodology → specialists → review → simplicity). On conflicting advice, the earlier one wins.
   - `dependencies` are internal capabilities the selected ones need; use them through those capabilities.
   - `fallbacks` apply only when the primary capability cannot decide.
   - `impact` (existing projects): run its `command` first and work from the files and tests it returns
     (`agylite-codebase` skill); never read the whole repository.
   - `verification_mode` is always `local-test-first` (`config/verification.yaml`): verify with tests, types, lint,
     build and recorded evidence. Never open Chrome, use DevTools, or take or inspect screenshots to verify.
   - `browser`: `disabled` → no browser at all; `exception-requested` → the user explicitly asked to see the page: run
     local verification, give them the URL to open themselves, and record the exception with its reason.
   - `pipeline` gives the domain order for multi-domain work (e.g. SEO audit → engineering → testing).
   - `confidence: low` (BM25 fallback): confirm the intent with the user before acting.
   - `unmatched: true`: tell the user in one line that no Agylite capability covers this request, then do the work
     with general principles (`fallback_guidance`). Do not invent a capability.

## Rules

- Simplicity review (Ponytail-derived) runs only when the user asks for it.
- New projects start with requirements; existing projects start with codebase understanding (spec §19.2).
- Never activate SEO, media or design capabilities the route did not select.

End your answer with the output of `agylite used` (what this work used).
