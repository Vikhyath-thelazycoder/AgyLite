# Security Policy

## Supported Versions

We release patches and security fixes for the current major/minor version series.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

---

## Security Model

Agylite is designed with a defense-in-depth security model suited for developer tooling:

### 1. Thin Orchestration (No Daemons, No Background Listeners)
The project contains only static declarative manifests, routing configurations, skills, and validation scripts. There are:
- **No background daemons** or long-running daemon processes.
- **No open network ports** or listening socket servers.
- **No automatic arbitrary code execution** outside the host agent's explicit execution model.

### 2. Cryptographic Dependency Pinning
External capabilities are never referenced via mutable branches (e.g., `main`, `master`) or unverified floating tags. Every upstream bundled into the capability registry is pinned (`docs/audit/evidence/upstream-staging-snapshot.yaml`, carried into every provenance record and registry entry) to a full **40-character hexadecimal Git commit SHA**. This protects against upstream tampering, unexpected breaking changes, and supply-chain supply poisoning.

### 3. Strict NO MCP Guarantee
Model Context Protocol (MCP) servers run external processes with system-level access. Agylite strictly prohibits MCP:
- No `mcpServers` manifests.
- No `.mcp.json` files.
- No MCP dependencies or proxy bridges.
This eliminates MCP-specific attack vectors (such as unauthorized tool invocation, arbitrary command execution, or local socket hijacking).

### 4. Zero Credential Storage
The repository strictly prohibits storing secrets, tokens, API keys, private keys, or environment files. All authentication is handled natively by the user's host environment (Codex, Antigravity, Claude Code).

### 5. Sandboxed Host Execution
Capability activations provide instructional routing guidance to the hosting environment. All file modifications and command executions adhere entirely to the hosting agent's security boundaries and user permission prompts.

---

## Reporting a Vulnerability

If you discover a potential security vulnerability in Agylite:

1. **Do NOT disclose it publicly** in an open issue or discussion.
2. Please submit a **Private Security Advisory** on GitHub via the [Advisories tab](https://github.com/Vikhyath-thelazycoder/AgyLite/security/advisories/new).
3. If GitHub Advisories are unavailable, contact the project maintainer directly via GitHub profile: [Vikhyath-thelazycoder](https://github.com/Vikhyath-thelazycoder).

### What to Include in Your Report
- Detailed description of the vulnerability.
- Steps to reproduce or proof-of-concept.
- Affected components or manifests.
- Potential impact.

### Response Timeline
- **Initial Acknowledgement**: Within 48 hours.
- **Assessment & Triage**: Within 5 business days.
- **Remediation & Advisory Release**: Coordinated with the reporter before public disclosure.
