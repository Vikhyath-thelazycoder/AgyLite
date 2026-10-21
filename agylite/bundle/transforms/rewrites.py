"""Targeted rewrites for ADAPT files whose instructions point at excluded mechanisms.

Every rewrite must match; a non-matching pattern means the upstream text changed (rewrite drift)
and the build fails instead of shipping un-adapted instructions.
"""
import re


class RewriteDrift(ValueError):
    pass


BUNDLE = "$AGYLITE_BUNDLE"  # expanded to the active bundle path by the context engine (P9)


def _section(heading):
    """A whole `## heading` section up to (not including) the next `## ` heading."""
    return re.compile(r"^## " + re.escape(heading) + r"\n.*?(?=^## )", re.M | re.S)


APPLLAMA_VERIFY = """## Verification (Agylite local test-first, D-035)

Verify with deterministic local checks, never with simulator screenshots or screen recordings in the model's
context (config/verification.yaml):

- **Navigation semantics** → router tests (`expo-router/testing-library` `renderRouter`, `toHavePathname`): after
  every one-way door, `router.back()` must not re-enter the old route; deep links resolve with a real stack.
- **Native controls, states, a11y** → React Native Testing Library: loading/empty/error states render, roles and
  labels are present, tap targets ≥ 44 pt (style assertions), rapid double taps submit once.
- **Theme and tokens** → unit tests over the theme module: one accent, one grey family, radii from the stated
  scale, both light and dark token sets complete.
- **Motion** → worklet/unit tests where testable (thresholds use distance OR velocity; Reduce Motion selects the
  cross-fade variant); frame-rate claims need a measured number from a profiler run, recorded as evidence.
- **Static** → `tsc --noEmit`, lint (incl. a11y lint rules), `expo export`/build succeeds.

Anything that only a human can judge on a device (feel, optical alignment) is reported as NOT_TESTED with the
reason, never as passed.

"""

APPLLAMA_DONE = """## Definition of done, per screen

- [ ] Navigation answered: what this screen *is* (push / modal / sheet / overlay / replace), what back does from it
      on iOS and Android, and — behind a one-way door — a router test proving back cannot re-enter the old state
- [ ] Semantic colors: light + dark token sets complete (unit test)
- [ ] Safe areas via `react-native-safe-area-context` insets (no hard-coded notch numbers; lint/grep check)
- [ ] Long-content, empty, loading and error states designed and rendered in component tests
- [ ] Motion: purpose named per animation; Reduce Motion variant tested; frame-rate claims measured, not eyeballed
- [ ] All tap targets ≥ 44 pt; contrast passes in both themes (a11y assertions)
- [ ] List surfaces virtualized; no controlled-input jank on typing surfaces
- [ ] Typecheck, lint and build pass; results recorded as verification evidence

"""

# MP3 §1.3 — Matt Pocock's skills: only the mechanics change. In Agylite the tracker is the project's living plan
# (`agylite plan`), a "Skill tool" call is `agylite skill load pocock/<name>` (Plan B: the whole skill, IMPLEMENTATION_PLAN
# §2.1, which overrides MP3's `context --file`), and `disable-model-invocation` is dropped (the router decides).
POCOCK_TRACKER = ("In Agylite the tracker is the project's living plan. Write the spec to `docs/specs/<slug>.md` and add "
                  "work with `agylite plan add-task <phase> \"<title>\" --depends <task-id> --acceptance \"<criterion>\"` "
                  "(one task per ticket; `--depends` for each blocking edge). If the user names an external tracker "
                  "(GitHub, Linear), ask before publishing anything there.")
POCOCK_NOT_BUNDLED = {"research": "agylite skills get pocock/research"}   # research domain arrives in MP5


def _pocock_load(name):
    return POCOCK_NOT_BUNDLED.get(name, f"agylite skill load pocock/{name}")


def _pocock_call(m):
    """`Call/calls/calling the Skill tool with "x"` → `Run/runs/running `agylite skill load pocock/x``."""
    verb = {"": "un", "s": "uns", "ing": "unning"}[m.group(2) or ""]
    return f"{'R' if m.group(1) == 'C' else 'r'}{verb} `{_pocock_load(m.group(3))}`"


def _pocock_twice(m):
    verb = {"": "un", "s": "uns", "ing": "unning"}[m.group(2) or ""]
    return (f"{'R' if m.group(1) == 'C' else 'r'}{verb} `{_pocock_load(m.group(3))}` and "
            f"`{_pocock_load(m.group(4))}`")


POCOCK_SKILL_CALL = (re.compile(r"\b([Cc])all(s|ing)? the Skill tool with [\"`]([\w-]+)[\"`]"), _pocock_call)
POCOCK_SKILL_TWICE = (re.compile(r"\b([Cc])all(s|ing)? the Skill tool twice, for \"([\w-]+)\" and \"([\w-]+)\""),
                      _pocock_twice)
POCOCK_NO_AUTO = (re.compile(r"^disable-model-invocation: true\n", re.M), "")
POCOCK_SETUP = (re.compile(r"The issue tracker (?:and triage label vocabulary )?should have been provided to you\. "
                           r"If not, tell the user to run `/setup-matt-pocock-skills`\."), POCOCK_TRACKER)
POCOCK_TICKETS_PUBLISH = (
    re.compile(r"^### 5\. Publish the tickets to the configured tracker\n.*?(?=^Work the \*\*frontier\*\*)", re.M | re.S),
    "### 5. Publish the tickets to the plan\n\n"
    "Publish the approved tickets as tasks in the project's living plan, in dependency order (blockers first), so each "
    "ticket's blocking edges can reference real task ids: one `agylite plan add-task <phase> \"<NN>: <ticket title>\" "
    "--depends <task-id> --acceptance \"<criterion>\"` per ticket, one `--depends` per blocking edge (none when it can "
    "start immediately). Write each ticket's body with the per-ticket template below into `docs/specs/<slug>.md`, one "
    "`## <NN>: <title>` section per ticket: one ticket per task, never a single combined task. If the user names an "
    "external tracker (GitHub, Linear), ask before publishing anything there.\n\n")
WAYFINDER_MAP = (
    re.compile(r"The map is a single issue on this repo's issue tracker, labelled `wayfinder:map`, the canonical "
               r"artifact\. Its tickets are child issues of the map\."),
    "In Agylite the map is a section `## Wayfinder map: <destination>` in the project's living plan, the canonical "
    "artifact. Its tickets are plan tasks (`agylite plan add-task <phase> \"[<type>] <title>\" --depends <task-id>`), "
    "the Agylite form of the map's child issues.")
WAYFINDER_TRACKER = (
    re.compile(r"The issue tracker should have been provided to you\. If not, tell the user to run "
               r"`/setup-matt-pocock-skills`\. Consult the tracker doc's \"Wayfinding operations\" section for how "
               r"_this_ repo expresses them\. If no tracker has been provided, default to the local-markdown tracker\."),
    "In Agylite they live in the project's living plan: the map is the `## Wayfinder map: <destination>` section, "
    "each ticket is a plan task, blocking is the task's Depends column (one `--depends` per blocking edge), closing "
    "a ticket is `agylite plan set-status <task> VERIFIED --evidence <file>`, and the frontier is the PLANNED tasks "
    "whose blockers are all done (`agylite plan show <phase>`). If the user names an external tracker (GitHub, "
    "Linear), ask before publishing anything there.")
WAYFINDER_LABEL = (
    re.compile(r"Each ticket carries a `wayfinder:<type>` label, one of"),
    "Each ticket's title starts with its type in brackets, the Agylite form of the `wayfinder:<type>` label (e.g. "
    "`[grilling] Decide the auth model`), one of")
WAYFINDER_NOTES = (re.compile(r"call the Skill tool for whichever skills the `## Notes` block names"),
                   "load whichever skills the `## Notes` block names (`agylite skill load <upstream>/<name>`)")


# (repo, path) -> [(pattern, replacement)]
REWRITES = {
    # P13 (D-027/D-035/D-038): no MCP and no browser automation as a data source; parse artifacts the user provides.
    ("addy", "agents/web-performance-auditor.md"): [
        (re.compile(r", `npx -p chrome-devtools-mcp chrome-devtools lighthouse_audit --output-format=json` "
                    r"\(Chrome DevTools MCP CLI, no install required\)"), ""),
        (re.compile(r"Defer interpretation to Chrome DevTools MCP \(`performance_analyze_insight`\); without MCP, "
                    r"summarize"), "Summarize"),
        (re.compile(r"^- \*\*Live capture via Chrome DevTools MCP server\*\*:.*\n- \*\*Chrome DevTools MCP CLI\*\*.*\n",
                    re.M), ""),
        (re.compile(r"^\| Live trace, LCP attribution.*\n\| Manual terminal capture.*\n", re.M),
         "| Live trace / attribution | A trace or report the user captured and provides | Not captured by the OS "
         "(browser automation is disabled, config/verification.yaml) |\n"),
    ],
    ("graphify", "graphify/skills/claude/references/exports.md"): [
        (re.compile(r", `--mcp`\)"), ")"),
        (re.compile(r"^### Step 7d - MCP server.*?(?=^### )", re.M | re.S), ""),
    ],
    ("unlazy", "SKILL.md"): [
        (re.compile(r"node <skill-dir>/scripts/install-hooks\.mjs"),
         "agylite runtime unlazy-hook --enable   # Agylite registers the Stop hook centrally, never in the project"),
    ],
    ("beyondseo", "SKILL.md"): [
        (re.compile(r"For an installation request, follow \[the host-specific guide\]\(docs/agent-installation\.md\), "
                    r"including Cursor, Lovable workspace imports and agents managing Vercel projects\."),
         "Installation and host registration are handled by Agylite (`agylite runtime install seo`)."),
        (re.compile(r"For Lovable execution, read \[the Lovable host guide\]\(docs/lovable\.md\)[^\n]*\n\n?"), ""),
    ],
    ("ecc", "rules/README.md"): [
        (re.compile(r"(?:^\./install\.sh [^\n]*\n)+", re.M),
         "# Agylite activates these rule packs for the detected stack; no install step is needed.\n"),
    ],
    # D-035: gstack review embeds browser exploratory QA in its critical pass; point it at local verification instead.
    ("gstack", "review/SKILL.md"): [
        (re.compile(r"From the installed /review SKILL\.md's directory, choose one path:\n.*?"
                    r"(?:Resolve QA's `sections/\.\.\.` and `templates/\.\.\.` paths from that installed QA SKILL\.md "
                    r"directory|QA's `sections/\.\.\.` and `templates/\.\.\.` paths resolve from installed QA SKILL\.md), "
                    r"not the caller or product directory\.\n", re.S),   # second form: upstream wording since 5cb5e1c
         "Exploratory browser QA is disabled by the Agylite verification policy (D-035, config/verification.yaml). "
         "Verify the changed area with the project's own tests, types, lint and build (`testing/local-verification`) "
         "and record the results as evidence; never open a browser or inspect screenshots.\n"),
    ],
    # D-034: keep the native-mobile rules no other bundled source has; drop what needs the Appllama MCP/credits,
    # what Taste/ECC already own canonically, and the simulator screenshot/recording loop (D-035).
    ("appllama", "skills/appllama-app-design-skill/SKILL.md"): [
        (re.compile(r"^description: .*$", re.M),
         "description: Native-feeling Expo / React Native screens — Apple HIG fidelity, semantic colors, native "
         "controls, navigation semantics (push vs replace, modal vs sheet vs overlay, one-way doors where back must "
         "not exist) and purposeful Reanimated motion. Use for mobile UI design and implementation."),
        (_section("The Prime Directive: study before you draw"),
         "## Study patterns, not pixels\n\nWhere reference screens of shipping apps are available, extract the "
         "pattern (layout skeleton, hierarchy, control choices, CTA placement), then design your own screen in the "
         "product's voice. Never copy a screen 1:1.\n\n"),
        (re.compile(r"6\. \*\*Study the grammar, not just the pixels\.\*\* Walking a winning flow on\n   Appllama, "
                    r"note what each step \*is\* — push, modal, sheet — and copy that\n   consistency\."),
         "6. **Study the grammar, not just the pixels.** For every flow, note what each step *is* —\n"
         "   push, modal, sheet — and keep that consistent across the app."),
        (_section("Anti-slop laws"),
         "## Anti-slop\n\nCanonical anti-slop rules live in `design/visual-quality` (Taste + OpenDesign). Apply them; "
         "the mobile additions are SF/Material Symbols over emoji in chrome and one label per intent.\n\n"),
        (re.compile(r"- The bar: 60 fps through the hero flow, .*?fresh eyes\.\n", re.S),
         "- The bar: 60 fps through the hero flow, measured on a **release build on\n  the slowest device you "
         "support** — Expo Go and dev builds hide exactly\n  the jank you're hunting. A frame-rate claim needs a "
         "profiler number recorded as evidence.\n"),
        (_section("State architecture"),
         "## State architecture\n\nServer/client/ephemeral state separation is canonical in `engineering/stack-packs` "
         "(ECC react-native-patterns). Mobile addition: uncontrolled `TextInput`s on high-frequency typing "
         "surfaces.\n\n"),
        (re.compile(r"- Cold-start TTI and bundle discipline live in\n  \[references/performance\.md\]"
                    r"\(references/performance\.md\) — apply the\n  measure → optimize → re-measure loop, never blind "
                    r"memoization\.\n"),
         "- Cold-start TTI and bundle discipline: `engineering/stack-packs` (ECC rules/react-native/performance.md);\n"
         "  measure → optimize → re-measure, never blind memoization.\n"),
        (_section("Image & illustration assets"), ""),
        (re.compile(r"^## The simulator loop \(non-negotiable\)\n.*?(?=^## Definition of done)", re.M | re.S),
         APPLLAMA_VERIFY),
        (_section("Definition of done, per screen"), APPLLAMA_DONE),
        (re.compile(r"^## References\n.*\Z", re.M | re.S),
         "## References\n\n| File | Load when |\n|---|---|\n"
         "| [references/native-controls.md](references/native-controls.md) | Choosing/wiring iOS+Android native "
         "controls, menus, pickers, sheets |\n"
         "| [references/motion.md](references/motion.md) | Any Reanimated work: gestures, transitions, springs, layout "
         "animations |\n"),
    ],
    ("pocock", "skills/productivity/grill-me/SKILL.md"): [POCOCK_NO_AUTO, POCOCK_SKILL_CALL],
    ("pocock", "skills/engineering/grill-with-docs/SKILL.md"): [POCOCK_NO_AUTO, POCOCK_SKILL_TWICE],
    ("pocock", "skills/engineering/to-spec/SKILL.md"): [
        POCOCK_NO_AUTO, POCOCK_SETUP,
        (re.compile(r"and publish it to the project issue tracker:"), "and save it in the project's living plan:"),
        (re.compile(r"then publish it to the project issue tracker\. Apply the `ready-for-agent` triage label - no need "
                    r"for additional triage\."), "then save it as above; no labels."),
    ],
    ("pocock", "skills/engineering/to-tickets/SKILL.md"): [
        POCOCK_NO_AUTO, POCOCK_SETUP, POCOCK_TICKETS_PUBLISH,
        (re.compile(r"published to the configured tracker \(edges as text in one file per ticket locally, or native "
                    r"blocking links on a real tracker\)"),
         "published as tasks in the project's living plan (one `--depends` per blocking edge)"),
    ],
    ("pocock", "skills/engineering/wayfinder/SKILL.md"): [
        POCOCK_NO_AUTO, WAYFINDER_MAP, WAYFINDER_TRACKER, WAYFINDER_LABEL, WAYFINDER_NOTES, POCOCK_SKILL_TWICE,
        POCOCK_SKILL_CALL,
    ],
    ("pocock", "skills/engineering/improve-codebase-architecture/SKILL.md"): [POCOCK_NO_AUTO, POCOCK_SKILL_CALL],
    ("pocock", "skills/engineering/implement/SKILL.md"): [
        POCOCK_NO_AUTO, POCOCK_SKILL_CALL,
        (re.compile(r"fetch it from the issue tracker and state its title"),
         "read it from the project's living plan (`agylite plan show <phase>`; a ticket is a task `T-…`) and state its "
         "title"),
    ],
    ("pocock", "skills/engineering/implement-spec/SKILL.md"): [POCOCK_NO_AUTO, POCOCK_SETUP, POCOCK_SKILL_CALL],
    ("pocock", "skills/engineering/tdd/SKILL.md"): [POCOCK_SKILL_CALL],
    ("pocock", "skills/engineering/code-review/SKILL.md"): [POCOCK_SETUP],
    ("pocock", "skills/productivity/handoff/SKILL.md"): [
        POCOCK_NO_AUTO,
        (re.compile(r"naming which skills the next agent should call the Skill tool for\."),
         "naming which skills the next agent should load (`agylite skill load <upstream>/<name>`)."),
    ],
    ("uiuxpromax", ".claude/skills/ui-ux-pro-max/SKILL.md"): [
        (re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/\.claude/skills/ui-ux-pro-max/scripts/"),
         f"{BUNDLE}/files/uiuxpromax/src/ui-ux-pro-max/scripts/"),
    ],
}


def applies(repo, path):
    return (repo, path) in REWRITES


def apply(repo, path, text):
    for pattern, replacement in REWRITES[(repo, path)]:
        text, count = pattern.subn(replacement, text)
        if count == 0:
            raise RewriteDrift(f"{repo}:{path}: pattern no longer matches upstream text: {pattern.pattern[:60]}")
    return text
