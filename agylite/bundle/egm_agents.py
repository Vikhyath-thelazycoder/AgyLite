"""Render EGM's Goldfish reviewers into Agylite's plugin `agents/` (Step 4b, doc 24 §4, plan 4b.2 A).

Claude Code registers a plugin's `agents/*.md` as subagent types (`agylite:<name>`). EGM ships two layers: Claude
adapters (`.claude-plugin/agents/*.md`: read-only tools, `omitClaudeMd`) that point at canonical personas
(`agents/*.md`) through `${CLAUDE_PLUGIN_ROOT}`. Agylite has no such root, so each rendered file is the adapter's
frontmatter and rules with the canonical persona inlined below them. File name = the persona's `name:`.

`python -m agylite.bundle.egm_agents` rewrites the files from the staged, pinned upstream; a test compares them.
"""
import re
import sys
from pathlib import Path

import yaml

from ..paths import repo_root

SKIP = {"bootstrap_orchestrator.md"}   # README bootstrap is route_excluded (ECC onboarding + Graphify own it)
ROOT_NOTE = "the EGM root (`files/egm/` in the Agylite bundle; the Elephant passes absolute paths)"


def _split(text: str):
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(m.group(1)), text[m.end():]) if m else ({}, text)


def render(staging: Path, pin: str) -> dict:
    """{agents/<name>.md: text} for every EGM reviewer adapter except the bootstrap orchestrator."""
    out = {}
    for adapter in sorted((staging / ".claude-plugin" / "agents").glob("*.md")):
        if adapter.name in SKIP:
            continue
        meta, rules = _split(adapter.read_text(encoding="utf-8"))
        persona_meta, persona = _split((staging / "agents" / adapter.name).read_text(encoding="utf-8"))
        name = meta["name"]
        head = {"name": name, "description": persona_meta.get("description") or meta["description"],
                "tools": ", ".join(meta.get("tools") or []), "model": meta.get("model", "inherit")}
        if meta.get("omitClaudeMd"):
            head["omitClaudeMd"] = True
        rules = re.sub(r"Read `\$\{CLAUDE_PLUGIN_ROOT\}/agents/[\w.]+` before (\w+)\.",
                       r"Your canonical persona follows below (EGM `agents/" + adapter.name + r"`, inlined by Agylite); "
                       r"read it before \1.", rules)
        rules = rules.replace("`${CLAUDE_PLUGIN_ROOT}`", ROOT_NOTE).replace("${CLAUDE_PLUGIN_ROOT}", ROOT_NOTE)
        rules = rules.replace("`egm:egm-", "`agylite:egm-")
        front = "".join(f"{k}: {'true' if v is True else v}\n" for k, v in head.items())
        out[f"agents/{name}.md"] = (
            f"---\n{front}license: Apache-2.0\n---\n\n"
            f"<!-- Rendered from google/elephant-goldfish-model@{pin[:7]} (Apache-2.0, Copyright 2026 Google LLC) by "
            f"agylite/bundle/egm_agents.py; do not edit by hand. -->\n\n"
            f"{rules.strip()}\n\n---\n\n{persona.strip()}\n")
    return out


def main() -> int:
    from .provenance import load_pins
    root = repo_root()
    files = render(root / ".staging" / "upstream" / "egm", load_pins()["egm"]["head"])
    for rel, text in files.items():
        (root / rel).write_text(text, encoding="utf-8")
    print(f"{len(files)} EGM agents written to agents/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
