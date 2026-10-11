"""Bundle content checks.

HARD (build fails): MCP configuration (spec §2.1): an `.mcp.json`/`mcp*.json` file, or a JSON/YAML/TOML
file declaring `mcpServers`. The only exception is test data for Graphify's MCP-file parser (D-021).
SOFT (recorded as adaptation debt in BUILD.json, cleared by the domain phases): MCP tool mentions and
gstack runtime paths left inside ADAPT text.
"""
import re

CONFIG_EXT = (".json", ".jsonc", ".yaml", ".yml", ".toml")
MCP_FILE = re.compile(r"(^|/)(\.?mcp[^/]*|[^/]*\.mcp)\.json$", re.I)  # .mcp.json, mcp*.json, *.mcp.json
MCP_MENTION = re.compile(r"mcp__|mcpServers|chrome-devtools-mcp|@modelcontextprotocol|\.mcp\.json")
GSTACK_RUNTIME = re.compile(r"\.claude/skills/gstack|gstack-skill-start|gstack-telemetry|gstack-update-check")
D021_ALLOWED = {("graphify", "tests/fixtures/sample.mcp.json")}
# D-038: files that treat MCP configuration as data to audit or detect (never configure or run MCP).
MCP_AS_DATA = {"files/ecc/skills/workspace-surface-audit/SKILL.md",
               "files/beacon/rules/context-exfiltration/secret-read-then-mcp-tool-handoff.rule.yaml",
               "files/beacon/rules/sensitive-edit/agent-control-surface-modified.rule.yaml",
               "files/beacon/rules/prompt-injection/indirect-injection-in-tool-result.rule.yaml",
               "files/beacon/rules/prompt-injection/mcp-poisoned-tool-description.rule.yaml"}


def hard_violations(repo, source_path, dest, data: bytes):
    if (repo, source_path) in D021_ALLOWED:
        return []
    found = []
    if MCP_FILE.search(dest):
        found.append(f"{dest}: MCP configuration file")
    elif dest.lower().endswith(CONFIG_EXT) and b"mcpServers" in data:
        found.append(f"{dest}: declares mcpServers")
    return found


def soft_debts(dest, decision, data: bytes):
    if decision != "ADAPT":
        return []
    # Lines the domain transform already marked as removed (D-038) are resolved, not debt.
    text = "\n".join(line for line in data.decode("utf-8", errors="ignore").splitlines()
                     if "[agylite] removed" not in line and "not part of Agylite" not in line)
    debts = []
    if MCP_MENTION.search(text) and dest not in MCP_AS_DATA:
        debts.append(("mcp_mentions", dest))
    if GSTACK_RUNTIME.search(text):
        debts.append(("gstack_runtime_paths", dest))
    return debts
