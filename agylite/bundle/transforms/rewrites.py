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
POCOCK_NOT_BUNDLED = {}   # skills named by a bundled skill but not bundled themselves (none since MP5 bundled research)


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


# MP5 §2.2 — youtube-agent-skill: the creator's voice file is host-neutral (~/.agylite/youtube/voice.md), the stdlib
# tools run through `agylite youtube <tool>`, `/yt-x` slash commands are `agylite skill load ytagent/yt-x`, and
# transcripts and channel lists come from the research domain. The skills' method and gates stay verbatim.
YT_VOICE = (re.compile(r"Read `~/\.claude/youtube/voice\.md` if it exists\."),
            "Read `~/.agylite/youtube/voice.md` if it exists (`agylite youtube voice init` creates it from the template). "
            "If it is still the unfilled template, ask for it, or proceed and mark the output **generic voice**.")
YT_TOOL = (re.compile(r"python3 (hookscore|title|deadair|chapters|retention|swipe)\.py"), r"agylite youtube \1")
YT_REL = (re.compile(r"`\.\./yt-(?:script|package)/(hookscore|title)\.py`"), r"`agylite youtube \1`")
YT_BARE = (re.compile(r"`(hookscore|title|chapters)\.py`"), r"`agylite youtube \1`")
YT_SLASH = (re.compile(r"`/(yt-[a-z]+)`"), r"`agylite skill load ytagent/\1`")
YT_WHISPER = (re.compile(r"No transcript yet\? Ask for one, or produce one first - `whisper`, `faster-whisper`, or the "
                         r"caption\ntrack YouTube generates on an unlisted upload all work\."),
              "No transcript yet? Ask for one, or take the caption track YouTube generates (also on an unlisted\n"
              "upload): `agylite research video <url> --subs`. Agylite does not transcribe audio.")
YT_COLLECT = (re.compile(r"Collect them however the user prefers - `yt-dlp --flat-playlist -J`\nagainst a channel URL is "
                         r"the fastest, the public page works, a manual list works\."),
              "Collect them however the user prefers - `agylite research channel <channel-url> --n 30 --swipe\n"
              "collected.json` (once per channel; it appends) is the fastest, the public page works, a manual list works.")

# MP5 §3.2 — Archify: commands run through `agylite diagram` (the bundled bin/archify.mjs from the working directory),
# explainer pages only on request (never proactive or always-on, never a mode offer), and Agylite owns updates (the
# wrapper disables Archify's update check). The authoring method, schemas, quality profiles and repair contract stay.
ARCHIFY = [
    (re.compile(r"node bin/archify\.mjs"), "agylite diagram"),
    (re.compile(r" Replace `bin/archify\.mjs` in every command with the installed package's absolute path, or its path "
                r"relative to your working directory; CLI input and output paths resolve from that directory\."),
     " Run Archify as `agylite diagram <command> …` (Agylite runs the bundled `bin/archify.mjs` from your working "
     "directory); CLI input and output paths resolve from that directory."),
    (re.compile(r", or proactively when the user's rules opt in with an \[archify explainer: \.\.\.\] line\. Not for"),
     ". Not for"),
    (re.compile(r" A page made on request ends its reply with the one-line mode offer under Output\."), ""),
    (re.compile(r"^- A rules line in context changes this\. `\[archify explainer: proactive\]`.*\n", re.M),
     "- Explainer pages are made only when the user asks for one: never unasked, and never offer a mode.\n"),
    (re.compile(r"^- In every mode a page needs", re.M), "- A page needs"),
    (re.compile(r"\n`finalize` includes a bounded update check in its delivery receipt; see Update awareness\.\n"), ""),
    (re.compile(r"^`finalize` and standalone `deliver` include `update` in their receipts\..*\n", re.M),
     "Agylite manages Archify updates; ignore update notices in receipts.\n"),
    (re.compile(r" Keep the required update notice under Update awareness\."), ""),
    (re.compile(r"\n\nAfter an explainer made on request, when no `\[archify explainer: \.\.\.\]` line is in context, "
                r"end the reply with one optional line offering the proactive mode.*\Z", re.S), "\n"),
]

# D-049 (IMPLEMENTATION_PLAN §2.2): Addy's devtools skill drives Chrome through the `chrome-devtools` command line of the
# pinned chrome-devtools-mcp package (no MCP server is ever configured) and AgyLite's own `agylite verify --browser`.
# Usage statistics are switched off. The Security Boundaries section (untrusted page content) stays verbatim.
CDT = "npx -y -p chrome-devtools-mcp@1.12.0 chrome-devtools"
ADDY_DEVTOOLS_SETUP = f"""## Setting Up Chrome DevTools (Agylite: command line, no MCP server)

Agylite drives Chrome from the command line; it never configures an MCP server.

- **The check that decides "done" for UI work:** `agylite verify --browser [--url <url>] [--flows .agylite/flows.yaml]`
  (pinned Playwright + Chromium, a throwaway context per run; `agylite runtime install browser` once). It takes
  screenshots at 1440, 768 and 390 px, collects console errors and failed requests, checks horizontal overflow at
  390 px, runs the task's flows and writes evidence to `.agylite/evidence/browser/<run-id>/`.
- **Interactive DevTools for debugging:** the `chrome-devtools` command line of the same package Addy's MCP setup used,
  pinned, with its own isolated temporary profile and usage statistics off:

```bash
{CDT} start --isolated --headless --usageStatistics=false
{CDT} new_page http://localhost:3000
{CDT} list_console_messages <pageId>
{CDT} stop
```

Never pass `--autoConnect` or `--browserUrl` to your own browser profile; see Profile Isolation below.

### Available Tools

| Tool | Command (`{CDT} …`) | When to Use |
|------|-------------|-------------|
| **Screenshot** | `take_screenshot <pageId>` (or `agylite verify --browser`) | Visual verification, before/after comparisons |
| **DOM Inspection** | `take_snapshot <pageId>` | Verify component rendering, check structure |
| **Console Logs** | `list_console_messages <pageId>`, `get_console_message <pageId> <id>` | Diagnose errors, verify logging |
| **Network Monitor** | `list_network_requests <pageId>`, `get_network_request <pageId> <id>` | Verify API calls, check payloads |
| **Performance Trace** | `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`, `lighthouse_audit` | Profile load time, identify bottlenecks |
| **Element Styles** | `get_css_styles <pageId> <uid>` | Debug CSS issues, verify styling |
| **Accessibility Tree** | `take_snapshot <pageId>` (the snapshot is the accessibility tree) | Verify screen reader experience |
| **JavaScript Execution** | `evaluate_script` | Read-only state inspection and debugging (see Security Boundaries) |

"""
ADDY_DEVTOOLS = [
    (re.compile(r" Requires the chrome-devtools MCP server to be configured\."),
     " Agylite runs it from the command line (`agylite verify --browser` and the chrome-devtools CLI), never as an MCP "
     "server."),
    (_section("Setting Up Chrome DevTools MCP"), ADDY_DEVTOOLS_SETUP),
]

# (repo, path) -> [(pattern, replacement)]
REWRITES = {
    ("addy", "skills/browser-testing-with-devtools/SKILL.md"): ADDY_DEVTOOLS,
    ("ytagent", "skills/yt-script/SKILL.md"): [YT_TOOL, YT_VOICE, YT_BARE],
    ("ytagent", "skills/yt-package/SKILL.md"): [YT_TOOL, YT_VOICE, YT_BARE],
    ("ytagent", "skills/yt-edit/SKILL.md"): [YT_TOOL, YT_WHISPER],
    ("ytagent", "skills/yt-chapters/SKILL.md"): [YT_TOOL, YT_BARE],
    ("ytagent", "skills/yt-retention/SKILL.md"): [YT_TOOL, YT_SLASH],
    ("ytagent", "skills/yt-viral/SKILL.md"): [YT_TOOL, YT_COLLECT],
    ("ytagent", "skills/yt-audit/SKILL.md"): [YT_VOICE, YT_REL, YT_SLASH],
    ("ytagent", "skills/yt-shorts/SKILL.md"): [YT_REL],
    ("ytagent", "skills/yt-plan/SKILL.md"): [YT_VOICE, YT_SLASH],
    ("ytagent", "skills/yt-comment/SKILL.md"): [YT_VOICE],
    ("ytagent", "templates/voice.md"): [(re.compile(r"Copy this to `~/\.claude/youtube/voice\.md`"),
                                         "`agylite youtube voice init` copies this to `~/.agylite/youtube/voice.md`; fill it in")],
    ("ytagent", "skills/yt-seo/SKILL.md"): [YT_VOICE, YT_SLASH],
    ("archify", "archify/SKILL.md"): ARCHIFY,
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
    # D-049 (browser on; supersedes the D-035 rewrite that replaced this step with "never open a browser"): gstack
    # review's exploratory QA reads gstack /qa's sections, which are not bundled — `/qa` runs from gstack's own install
    # (`agylite runtime install gstack`). Only the anchor line changes; it names no home path, which the domain
    # transform would map into the bundle, so upstream's wording below it stays verbatim
    # (Phase 9: the old multi-line pattern drifted when upstream numbered the step and reworded its last line).
    ("gstack", "review/SKILL.md"): [
        (re.compile(r"^(\d+\. )?From the installed /review SKILL\.md's directory, choose one path:$", re.M),
         r"\1From the directory of gstack's own installed /review skill (set up by `agylite runtime install gstack`; "
         r"this bundled copy has no QA sections), choose one path:"),
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
    # MP3 §2.3: ponytail-review leads engineering/review; Ponytail's slash command does not exist in Agylite (the router
    # and `agylite skill load ponytail/ponytail-review` invoke it). The review method itself is unchanged.
    ("ponytail", "skills/ponytail-review/SKILL.md"): [
        (re.compile(r'"is this over-engineered", /ponytail-review\.'), '"is this over-engineered".'),
    ],
    # MP4 §1.3: Taste v2.1's scripts run through the `agylite design taste` runtime (bundle paths, TASTE_SKILL_TMP,
    # the draw memory under ~/.agylite); "done" names agylite verify. Taste's look-and-fix loop and juror rubric stay.
    ("taste", "skills/taste-skill/SKILL.md"): [
        (re.compile(r"node <skill>/scripts/(draw|lint|inspect|scenes|assets)\.mjs"), r"agylite design taste \1"),
        (re.compile(r"4\. \*\*You look at what you made\.\*\* Screenshots at three widths, a juror's rubric, fix, look again\."),
         "4. **You look at what you made.** Run `agylite design taste inspect`, look at the screenshots, and fix every "
         "FAIL; then a juror's rubric, fix, look again. The task is complete only when `agylite verify` passes: tests, "
         "types, lint incl. `agylite design taste lint`, build, and `agylite design taste inspect` with 0 FAIL."),
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
