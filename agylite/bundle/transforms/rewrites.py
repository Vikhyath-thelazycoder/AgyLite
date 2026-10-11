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
