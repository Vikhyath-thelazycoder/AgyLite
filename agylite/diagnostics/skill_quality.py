"""Free quality check for Agylite's own entry skills and agents (docs/plan/SKILL_QUALITY_PLAN.md, Phase 0).

The standard is in CONTRIBUTING.md ("Writing entry skills and agents"). `problems(root)` returns one line per defect;
`agylite validate` prints them. Upstream skills and the rendered EGM agents are not checked: Agylite does not own them.
"""
import re
from pathlib import Path

# True since the rewrite finished (2026-11-14): any problem fails `agylite validate` and the tests.
STRICT = True

MAX_SKILL_BYTES = 6500
SKILL_SECTIONS = ("## Use when", "## Steps", "## Output", "## Quality bar", "## When something fails")
AGENT_SECTIONS = ("## Method", "## Output", "## Do not report")
OWN_AGENTS = ("engineering-architect", "security-reviewer", "production-reviewer")
HOST_FILES = ("CLAUDE.md", "AGENTS.md", ".agents/skills/agylite/SKILL.md")

# Plan sections, spec paragraphs and decision numbers mean nothing to an agent that reads the skill.
INTERNAL_REF = re.compile(r"\bMP\d\b|§|\bD-\d{3}\b")
# Sentences that forbid browser verification; wrong while config/verification.yaml says tests-and-browser.
NO_BROWSER = re.compile(r"(?i)\b(?:no|never)\b[^.]{0,40}\bbrowser\b[^.]{0,30}(?:verif|screenshot|devtools)"
                        r"|\bnever verify by[^.]{0,20}\bbrowser")
CODE = re.compile(r"```.*?```|`[^`\n]+`", re.S)
COMMAND = re.compile(r"\bagylite((?: +[a-z][a-z|-]*)+)")
# A skill's own references/ folder; a longer path (files/<upstream>/…/references/x.md) is an upstream's file.
REFERENCE = re.compile(r"(?<![\w/])references/[\w./-]+\.md\b")
CONFIG = re.compile(r"\bconfig/[\w-]+\.yaml\b")


def _frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line) if m else {}


def _subcommands(parser):
    import argparse
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    return {}


def _unknown_commands(text, parser):
    """`agylite a b c` inside code: every word is checked while the parser has subcommands at that depth."""
    bad = set()
    for span in CODE.findall(text):
        for m in COMMAND.finditer(span):
            node, path = parser, "agylite"
            for word in m.group(1).split():
                choices = _subcommands(node)
                if not choices:
                    break
                names = word.split("|")
                bad.update(f"{path} {n}" for n in names if n not in choices)
                if names[0] not in choices:
                    break
                node, path = choices[names[0]], f"{path} {names[0]}"
    return sorted(bad)


def _common(text, flat, root, mode):
    out = [f"internal reference `{m}`" for m in sorted(set(INTERNAL_REF.findall(text)))]
    if mode == "tests-and-browser":
        out += [f"forbids browser verification, but the policy is tests-and-browser: “{m.group(0).strip()}”"
                for m in NO_BROWSER.finditer(flat)]
    out += [f"names a missing file {c}" for c in sorted(set(CONFIG.findall(text))) if not (root / c).is_file()]
    return out


def file_problems(path: Path, root: Path, kind: str, parser=None, mode="tests-and-browser") -> list:
    """kind: skill | agent | host. Host files get the contradiction check only."""
    text = path.read_text(encoding="utf-8")
    flat = " ".join(text.split())
    out = []
    if kind == "host":
        return [p for p in _common(text, flat, root, mode) if p.startswith("forbids")]
    fm = _frontmatter(text)
    if "use when" not in fm.get("description", "").lower():
        out.append("description does not say when to use it (“use when …”)")
    out += [f"section missing: {s}" for s in (SKILL_SECTIONS if kind == "skill" else AGENT_SECTIONS) if s not in text]
    if kind == "skill" and len(text.encode("utf-8")) > MAX_SKILL_BYTES:
        out.append(f"{len(text.encode('utf-8'))} bytes, over the {MAX_SKILL_BYTES} limit: move detail to references/")
    if kind == "skill":
        out += [f"names a missing file {r}" for r in sorted(set(REFERENCE.findall(text)))
                if not (path.parent / r).is_file()]
    if kind == "agent" and "incomplete review" not in flat.lower():
        out.append("no rule for an incomplete review (a required file cannot be read)")
    out += _common(text, flat, root, mode)
    if parser is not None:
        out += [f"unknown command `{c}`" for c in _unknown_commands(text, parser)]
    return out


def problems(root: Path) -> list:
    """Every defect in Agylite's own skills, agents and host copies, as `<path>: <problem>` lines."""
    import yaml
    from ..cli import build_parser
    parser = build_parser()
    try:
        mode = yaml.safe_load((root / "config/verification.yaml").read_text(encoding="utf-8")).get("mode")
    except (OSError, yaml.YAMLError, AttributeError):
        mode = None
    targets = [(p, "skill") for p in sorted(root.glob("skills/agylite-*/SKILL.md"))]
    targets += [(root / "agents" / f"{a}.md", "agent") for a in OWN_AGENTS]
    targets += [(root / h, "host") for h in HOST_FILES]
    return [f"{p.relative_to(root)}: {problem}" for p, kind in targets if p.is_file()
            for problem in file_problems(p, root, kind, parser, mode)]


if __name__ == "__main__":
    from ..paths import repo_root
    found = problems(repo_root())
    print("\n".join(found) or "no problems")
    raise SystemExit(1 if found and STRICT else 0)
