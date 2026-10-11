# Contributing to Agylite

Thank you for your interest in contributing to **Agylite**! This project is a thin, portable orchestration layer that selectively routes AI coding tasks to specialized engineering capabilities from proven external repositories.

Before submitting contributions, please read this guide and our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Architecture Principles & Guardrails (Non-Negotiable)

The architecture of Agylite is locked to ensure stability, portability, and context efficiency:

1. **Thin Orchestration Layer**: Agylite routes tasks; it is not a monolithic framework, giant prompt, or always-on daemon.
2. **No upstream code in this repository**: Never vendor, submodule, or commit third-party files here. Selected upstream files are fetched at their pinned commits and built into the local bundle at install time (`scripts/install`, D-023). To change what is bundled, edit `tools/audit/extraction-rules.yaml`, run `python tools/audit/extraction_matrix.py` (0 open closure gaps required) and regenerate notices with `python -m agylite.bundle.notices`.
3. **Progressive Capability Activation**: Only capabilities relevant to the immediate task are activated. Never load all capabilities simultaneously.
4. **Strict NO MCP**: No Model Context Protocol (MCP) servers, configs (`.mcp.json`), adapters, or dependencies are allowed.
5. **Deterministic Conflict Hierarchy**: Conflicting guidance is resolved using the 8-level priority hierarchy defined in `config/priorities.yaml`.
6. **Cryptographic Pinning**: All external capability references must be pinned to immutable 40-character hexadecimal Git commit SHAs.

---

## Getting Started

### Prerequisites

- **Git**
- **Python 3.9+**
- **PyYAML** (`pip install pyyaml`)
- A supported agent host: Codex, Antigravity, or Claude Code

### Setup

```bash
git clone https://github.com/Vikhyath-thelazycoder/AgyLite.git
cd agylite
pip install pyyaml
```

---

## Development & Validation Workflow

We provide a comprehensive validation and diagnostic suite. **All checks must pass before any pull request will be accepted.**

```bash
# 1. Run Python unit tests
python3 -m unittest discover -s tests -p "test_*.py"

# 2. Run structural & integrity diagnostics
chmod +x scripts/doctor scripts/validate scripts/benchmark
./scripts/doctor

# 3. Run validation suite (offline)
./scripts/validate

# 4. Run remote GitHub commit SHA verification (online)
./scripts/validate --online

# 5. Run context and capability benchmark
./scripts/benchmark
```

### What Each Tool Checks

| Tool | Purpose |
|---|---|
| `python3 -m unittest` | Executes unit tests covering manifests, routing rules, security constraints, and integration schemas. |
| `./scripts/doctor` | Verifies repository structure, manifest schemas (Agent Plugins 1.0.0), marketplace configs, version consistency, and absence of MCP / vendor directories. |
| `./scripts/validate` | Tests routing rule integrity, capability registry format, 40-character commit SHAs, and security guardrails. |
| `./scripts/validate --online` | Queries the GitHub API to confirm every pinned commit SHA exists in its remote repository. |
| `./scripts/benchmark` | Generates capability coverage matrix and context efficiency estimates. |

---

## Proposing New Capability Integrations

To propose integrating a new external capability:

1. Open an issue using the [Capability Proposal Template](.github/ISSUE_TEMPLATE/capability_proposal.md).
2. Ensure the capability meets these criteria:
   - **Proven Track Record**: Public, high-quality open-source repository with active maintenance.
   - **Non-Redundant Role**: Fills a distinct engineering role not already covered by an existing capability.
   - **Zero MCP Requirement**: The tool must not require MCP runtime configuration or servers.
   - **Permissive License**: MIT, Apache-2.0, or compatible open-source license.
   - **Pinned Commit SHA**: Must point to an exact 40-character hexadecimal Git commit SHA.
3. If approved, add:
   - Extraction rules for the upstream in `tools/audit/extraction-rules.yaml` (each rule names its capability)
   - A capability card when the work needs a new capability: `capabilities/<domain>/<subdomain>/card.yaml`, then `agylite registry cards`
   - Updated routing signals in: `config/routing.yaml`
   - Unit tests validating the new metadata.

---

## Repository Structure

```text
agylite/                        # the OS: routing, context, project, isolation, bundle, registry, verify, codebase,
│                               # design, seo, runtimes, events, dashboard, update, adapters, diagnostics, cli.py
bin/agylite                     # host launcher (central install → PATH → plugin source); bin/vikhyath alias
capabilities/<domain>/<name>/   # card.yaml (authored) + CARD.md (generated)
config/                         # routing, priorities, budgets, lifecycle, verification, design, dashboard
skills/agylite-*/               # entry skills shared by every host
agents/                         # reviewer personas (frontmatter)
hooks/hooks.json                # Claude Code: SessionStart bootstrap only
.claude-plugin/ .codex-plugin/ .agents/   # generated host packaging (`agylite adapters render`)
tools/audit/                    # extraction rules, matrix and scanners
docs/architecture/              # how it works · docs/migration/ · docs/benchmarks/ · docs/plan/ · docs/audit/
tests/                          # unittest suite (python -m unittest discover -s tests)
scripts/                        # install, doctor, validate, benchmark wrappers
```

---

## Pull Request Guidelines

1. Fork the repository and create a descriptive branch from `main` (e.g., `feat/add-routing-signal`, `fix/manifest-schema`).
2. Make minimal, surgical changes adhering to existing design patterns.
3. Run `python -m unittest discover -s tests`, `agylite doctor`, `agylite validate` and `agylite adapters render --check`; all must pass.
4. Add no MCP configuration, no always-on hooks and no browser-based verification; upstream content enters only through `tools/audit/extraction-rules.yaml` and the bundle build.
5. Fill out the [Pull Request Template](.github/pull_request_template.md) completely.
6. Submit your PR against `main`. All CI checks must pass.

---

## License

By contributing to Agylite, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
