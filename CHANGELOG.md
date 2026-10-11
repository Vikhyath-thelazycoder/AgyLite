# Changelog

All notable changes to Agylite (formerly Vikhyath AI Engineering OS) are documented in this file.

## [2.1.2] - 2026-10-11

Fixes from the first hands-on trial (`docs/TRY_AGYLITE.md`).

### Fixed
- Routing: a new product no longer always pulls in design and security — design joins only with an interface, security
  only with users, accounts, payments or network exposure; a request that just describes the product ("a small
  Python CLI todo app …") is recognised; "build X with unit tests" is a feature, not a testing change; the bare tag
  "done" no longer selects release verification.
- Plan: a task's status rolls up into its phase (first task started → phase IN_PROGRESS; all tasks done → phase
  VERIFIED/COMPLETED with the evidence; a reopened task reopens the phase); state follows the current phase and keeps
  the last task-level verification (`verification.last_task`); `agylite verify` ties a run to the single active task.
- Events: CLI events carry the session id of the host's last bootstrap; new `TASK_READY_FOR_VERIFICATION` and
  `TASK_VERIFIED` events (no longer reported as verification runs); the dashboard shows task and phase changes.
- BLOCKING requirement questions are recorded and must be answered (`agylite project answer`) before a task starts.
- New projects start with an empty P1 instead of a template CI/authentication task.
- `.agylite/` state files are never counted as changed code by `agylite verify`/`codebase affected`.

## [2.1.1] - 2026-10-11

### Changed
- First checked upstream update: ECC (672 commits), Beacon (211), Graphify (195), Ponytail (62), gstack (43), Open Design,
  Taste, UI/UX Pro Max, Brag, Addy, Agency. Bundle 2,648 files.

### Fixed
- Batch updates build with earlier updated upstreams' new trees; inventories no longer download every file; license
  metadata always fetched; stale capability cards no longer block an update; Beacon tool-result text matches upstream;
  three new gstack placeholders replaced; bundled-file counts in tests derived from the extraction summary.

## [2.1.0] - 2026-10-11

### Added
- Automatic upstream tracking: `agylite update --check`, `--latest [--due] [--track]`, `--promote`,
  `--schedule install|remove`; per-upstream policy in `config/upstreams.yaml`; incremental blobless mirrors (only new
  commits are fetched); GitHub Action with a daily check and a weekly/monthly pull request of checked updates.

## [2.0.0] - 2026-10-11

Renamed to **Agylite** and rebuilt as a working local OS (milestones M0–M7, decisions D-001…D-046).

### Added
- `agylite` core and CLI with a curated, pinned, provenance-tracked bundle of 15 upstreams (~2,580 files), built locally.
- 63-capability registry; deterministic router (22/22 spec scenarios, p95 0.34 ms); budgeted L0–L3 context engine with
  a session cache; per-project state, one living plan, decisions and lifecycle; structural multi-project isolation.
- Codebase intelligence (Graphify runtime, `codebase affected` with related tests, structural fallback); Unlazy gates;
  design engine and design-token checks; local test-first verification (`verify`, evidence JSON); BeyondSEO runtime with
  evidence labels and a live-site authorization gate; Brag media workflow.
- Redacted event log and Beacon risk rules; Agent Office dashboard; explicit `update`/`rollback`/`gc`.
- Host adapters for Claude Code, Codex, Cursor and Antigravity from one entry-skill set; measured benchmarks.

### Changed
- Verification is local and test-first; browser, Chrome DevTools and screenshot verification are disabled.
- `workflows/` replaced by `config/lifecycle.yaml`; entry skills and agents rewritten (frontmatter on agents).
- Names: plugin `agylite@agylite-marketplace`, CLI `agylite` (`vikhyath` kept as an alias), home `~/.agylite`,
  project state `.agylite/` (pre-rename locations still used when present).

### Removed
- "Zero vendoring" and "runtime tested" claims; repo-first routing ("route to ECC").

## [1.0.1] - 2026-09-02

### Added
- Root-level portable `plugin.json` adhering to the Agent Plugins 1.0.0 specification (`https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`)
- Codex marketplace metadata in `.agents/plugins/marketplace.json` exposing root plugin source (`./`)
- Claude Code marketplace metadata in `.claude-plugin/marketplace.json` exposing root plugin source (`./`)
- GitHub Actions CI workflow in `.github/workflows/ci.yml` running unit tests, diagnostics, validation, and architecture audits on PRs and pushes
- Support for `--online` verification flag in `./scripts/validate` for remote GitHub commit SHA verification
- Expanded unit test suite (20 unit tests across manifests, routing, security, integration schemas, and community health files)
- Open-source governance files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- GitHub issue templates for bug reports, feature requests, and capability proposals
- Pull request template with strict NO-MCP and NO-vendor checklists
- Comprehensive 18-section public README with exact native host commands, troubleshooting, and verification workflows

### Changed
- Updated `.claude-plugin/plugin.json` to minimal valid schema, removing non-standard relative skills path
- Updated installation documentation across README, CLAUDE.md, and integration files to current marketplace-based flows for Codex and Claude Code
- Enforced strict 40-character hexadecimal commit SHA format checking for all 9 capability registries
- Removed unverified/stale tag entries from `config/capabilities.yaml` and `integrations/ecc.yaml`
- Clarified benchmark claims to distinguish between verified measurements and architecture-level estimates
- Clarified routing model terminology from dynamic execution claims to intelligent capability instruction and routing

## [1.0.0] - 2026-09-02

### Added
- Initial release of Vikhyath AI Engineering OS
- Capability registry with 9 external capabilities (ECC, Graphify, Unlazy, Addy, Agency, gstack, OpenDesign, Ponytail, Karpathy)
- Progressive activation routing system
- Codex plugin manifest (`.codex-plugin/plugin.json`)
- Claude Code plugin manifest (`.claude-plugin/plugin.json`)
- Antigravity skill adapter (`.agents/skills/vikhyath-os/`)
- 5 core skills: routing, engineering, production, security, review
- 3 agent definitions: engineering-architect, security-reviewer, production-reviewer
- 5 workflow definitions: feature, bugfix, refactor, security-review, release
- 9 integration metadata files with pinned commit SHAs
- Routing configuration with task classification rules
- Priority and conflict resolution configuration (8-level hierarchy)
- Diagnostics, validation, and benchmark scripts
- MIT license
