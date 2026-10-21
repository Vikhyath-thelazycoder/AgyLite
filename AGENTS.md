# Agylite — agent instructions

Agylite is a local engineering OS for coding agents. Do not pick skills by hand and do not load every skill.
On Claude Code, Agylite's route arrives with your prompt (UserPromptSubmit hook). Load the listed context before the
first edit; do not skip it on small tasks. Hosts without that hook (Codex, Cursor, Antigravity) route every request
themselves with step 2:

1. `agylite bootstrap --host <your host>` at the start of a session (compact project state, plan pointer, capability index).
2. `agylite route "<request>" [--paths <files…>]` — the minimum capabilities, their lifecycle and impact step.
3. `agylite context --request "<request>" <capability-id>…` (or `agylite context --route "<request>"`) — load only what the route selected (L1 cards, L2 sections; L3 only on purpose).
4. Follow the route's `lifecycle`; start existing-project changes with `agylite codebase affected`.
5. Verify with `agylite verify` (local tests, types, lint, build) and record the evidence. Never verify with a browser,
   Chrome DevTools or screenshots (`config/verification.yaml`).
6. Record decisions with `agylite decide add` and progress with `agylite plan set-status`.

Rules: no MCP servers; guidance order is the route's capability order (`config/priorities.yaml`); Simplicity review
only when the user asks; never write into another project; live-website edits need `agylite seo authorize`.

Entry skills: `skills/agylite-*`. Architecture: `docs/architecture/`. If `agylite` is not on PATH, use `bin/agylite`.
