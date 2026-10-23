"""Render gstack `.tmpl` skills without gstack's runtime (docs/audit/07, D-015).

gstack generates SKILL.md from templates with TypeScript resolvers; the generated files carry a heavy
runtime preamble (telemetry, onboarding, update checks). The renderer:
  * drops runtime-only placeholders (PREAMBLE, GBRAIN_*, ASIDE_*, BROWSE_*, OUTSIDE_*, LEARNINGS_*, …),
  * turns {{SECTION:id}} into a lazy "read this section when …" pointer and {{SECTION_INDEX:skill}}
    into a table from the skill's section manifest (progressive disclosure),
  * keeps methodology placeholders by recovering their expansion from upstream's own generated files:
    template literals are anchors in the generated text; text between anchors is the expansion.
    Expansions are shared across skills, so a placeholder adjacent to another in one skill is
    resolved from a skill where it stands alone, or by peeling known neighbours off the group.
Anything still unresolved is reported, never silently dropped.
"""
import json
import re
from pathlib import Path

TOKEN = re.compile(r"\{\{([A-Z_]+)(?::([A-Za-z0-9_-]+))?\}\}")
DROP_PREFIXES = ("PREAMBLE", "GBRAIN", "BRAIN_", "ASIDE", "BROWSE", "OUTSIDE", "LEARNINGS", "CODEX", "SLUG",
                 "REVIEW_DASHBOARD", "PLAN_FILE_REVIEW_REPORT", "MODEL_OVERLAY", "QUESTION_TUNING", "REDACT",
                 "TASKS_SECTION_EMIT", "AUTOPLAN", "EXIT_PLAN_MODE", "THIRD_PARTY", "SETUP_COMMAND", "NATIVE_LABEL",
                 "DESIGN_SETUP", "BENEFITS_FROM", "INVOKE_SKILL")


def split_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[: end + 4], text[end + 4:]
    return "", text


def dropped(name):
    return name.startswith(DROP_PREFIXES)


MIN_ANCHOR = 24  # shorter literals (e.g. "---", "|") match too easily and mis-align expansions


def align(tmpl_body, gen_body):
    """Return ({(index, name, arg): expansion} for isolated placeholders, [(tokens, text, weak_literals)] for groups).

    A template literal is used as an anchor only when it is strong: at least MIN_ANCHOR characters and
    occurring exactly once in the rest of the generated text. Weak literals are folded into the group.
    """
    parts = TOKEN.split(tmpl_body)
    literals, tokens = parts[0::3], list(zip(parts[1::3], parts[2::3]))
    isolated, groups, pending, weak = {}, [], [], []
    pos = 0
    first = literals[0].strip()
    if first:
        start = gen_body.find(first)
        if start < 0:
            return isolated, groups
        pos = start + len(first)
    for k, tok in enumerate(tokens):
        pending.append((k,) + tok)
        anchor = literals[k + 1].strip()
        last = k == len(tokens) - 1
        strong = len(anchor) >= MIN_ANCHOR and gen_body.count(anchor, pos) == 1
        if not strong and not last:
            if anchor:
                weak.append(anchor)
            continue
        if anchor and not strong:  # last token with an unreliable anchor: do not guess
            break
        end = gen_body.find(anchor, pos) if anchor else len(gen_body)
        text = gen_body[pos:end]
        if len(pending) == 1:
            isolated[pending[0]] = text
        else:
            groups.append((pending, text, weak))
        pos, pending, weak = end + len(anchor), [], []
    return isolated, groups


def _strip_literals(text, literals):
    for lit in literals:
        stripped = text.strip()
        if stripped.startswith(lit):
            text = stripped[len(lit):]
        elif stripped.endswith(lit):
            text = stripped[: -len(lit)]
    return text


def _peel(group_tokens, text, library, weak_literals=()):
    """Strip known expansions from both ends of a group; return {token: text} for what can be assigned."""
    toks = list(group_tokens)
    found = {}
    remaining = text
    changed = True
    while toks and changed:
        changed = False
        head, tail = toks[0], toks[-1]
        known_head = library.get(head[1:])
        if known_head is not None and remaining.lstrip().startswith(known_head.strip()):
            found[head] = known_head
            remaining = remaining.lstrip()[len(known_head.strip()):]
            toks.pop(0)
            changed = True
            continue
        known_tail = library.get(tail[1:])
        if known_tail is not None and remaining.rstrip().endswith(known_tail.strip()):
            found[tail] = known_tail
            remaining = remaining.rstrip()[: -len(known_tail.strip())]
            toks.pop()
            changed = True
        stripped = _strip_literals(remaining, weak_literals)
        if stripped != remaining:
            remaining, changed = stripped, True
    if len(toks) == 1:
        found[toks[0]] = remaining
    return found


class Renderer:
    def __init__(self, repo_root: Path, inventory, bundled=None):
        """`bundled`: the bundled paths (`.tmpl` stripped). Only those templates teach expansions, so a full clone
        renders like the update's sparse fetch (Phase 9: an excluded design-review template taught
        DESIGN_OUTSIDE_VOICES its Codex text, which then replaced the OS-native fallback in plan-design-review)."""
        self.root = Path(repo_root)
        tracked = {p for p, _, _ in inventory} if inventory else None
        self.pairs = {}
        for tmpl in sorted(self.root.glob("**/*.tmpl")):
            rel = tmpl.relative_to(self.root).as_posix()
            gen = tmpl.with_suffix("")
            if bundled is not None and rel[: -len(".tmpl")] not in bundled:
                continue
            if gen.is_file() and (tracked is None or rel in tracked):
                self.pairs[rel] = (tmpl.read_text(encoding="utf-8"), gen.read_text(encoding="utf-8"))
        self.per_file, self.library = {}, {}
        groups = []
        for rel, (t, g) in self.pairs.items():
            isolated, grp = align(split_frontmatter(t)[1], split_frontmatter(g)[1])
            self.per_file[rel] = {k: v for k, v in isolated.items()}
            for (k, name, arg), text in isolated.items():
                self.library.setdefault((name, arg), text)
            groups += [(rel, toks, text, weak) for toks, text, weak in grp]
        progress = True
        while progress:
            progress = False
            for rel, toks, text, weak in groups:
                for tok, val in _peel(toks, text, self.library, weak).items():
                    if tok not in self.per_file[rel]:
                        self.per_file[rel][tok] = val
                        self.library.setdefault(tok[1:], val)
                        progress = True

    def _manifest(self, skill):
        path = self.root / skill / "sections" / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"sections": []}

    def _section_pointer(self, skill, sid):
        entry = next((s for s in self._manifest(skill)["sections"] if s["id"] == sid), None)
        if entry is None:
            return None
        return f"> **Section: {entry['title']}.** Read `sections/{entry['file']}` when {entry['trigger']}."

    def _section_index(self, skill):
        rows = [f"| `sections/{s['file']}` | {s['title']} | {s['trigger']} |" for s in self._manifest(skill)["sections"]]
        if not rows:
            return ""
        return "\n".join(["| Section file | Covers | Read when |", "|---|---|---|", *rows])

    def render(self, rel_path, tmpl_text):
        """Render one template; return (text, [unresolved placeholder names])."""
        skill = rel_path.split("/", 1)[0]
        known = self.per_file.get(rel_path, {})
        frontmatter, body = split_frontmatter(tmpl_text)
        unresolved = []
        index = -1

        def substitute(m):
            nonlocal index
            index += 1
            name, arg = m.group(1), m.group(2)
            if dropped(name):
                return ""
            if name == "SECTION":
                pointer = self._section_pointer(skill, arg)
                if pointer is not None:
                    return pointer
            elif name == "SECTION_INDEX":
                return self._section_index(arg or skill)
            text = known.get((index, name, arg))
            if text is None:
                text = self.library.get((name, arg))
            if text is None:
                unresolved.append(name)
                return f"<!-- agylite: gstack placeholder {name} not recovered -->"
            return text.strip("\n")

        rendered = TOKEN.sub(substitute, body)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip("\n") + "\n"
        return frontmatter + "\n" + rendered, unresolved
