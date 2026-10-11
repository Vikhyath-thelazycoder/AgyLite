# Host adapters

One set of entry skills (`skills/agylite-*`, 11 skills) serves every host. Adapters only render packaging and report
status; they contain no routing or state logic.

| Host | Packaging | Install |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/`, `agents/`, `hooks/hooks.json` (SessionStart → `bin/agylite bootstrap --host claude-code`, nothing else) | `claude plugin marketplace add Vikhyath-thelazycoder/AgyLite` then `claude plugin install agylite@agylite-marketplace` |
| Codex | `.codex-plugin/plugin.json` (`skills: ./skills/`), `.agents/plugins/marketplace.json` | `codex plugin marketplace add Vikhyath-thelazycoder/AgyLite` then `codex plugin add agylite@agylite-marketplace` (older CLIs: `codex plugin install`) |
| Cursor | user-level skills | `agylite adapters install --host cursor` → `~/.cursor/skills/agylite-*` |
| Antigravity | `.agents/skills/agylite/SKILL.md` (generated) + user-level skills | `agylite adapters install --host antigravity` → `~/.gemini/config/skills/agylite-*` |

```bash
agylite adapters render [--check]   # regenerate host files from the entry skills (CI uses --check)
agylite adapters status             # per host: FILES_PRESENT → INSTALLED → RUNTIME_VERIFIED
agylite adapters uninstall --host cursor
```

- `bin/agylite` finds the central install (`~/.agylite/core`), else `agylite` on PATH, else the plugin's own source;
  it never fails a session start and shows its path in the L0 bootstrap.
- RUNTIME_VERIFIED is reported only after the host actually ran `agylite bootstrap --host <name>`.
- User-level installs carry a `.agylite-managed` marker, never overwrite other skills and remove only their own.
- No adapter writes MCP configuration or enables browser tooling; every entry skill names `config/verification.yaml`.
