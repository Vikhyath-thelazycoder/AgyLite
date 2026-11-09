# 24 — New upstreams: Astryx, Caldo, Elephant-Goldfish Model (staging audit and owner plan)

Date: 2026-11-10 · Decision: D-052 · Status: **staged and audited; nothing bundled yet.** Bundled in **Step 4b**, after
the Step 3 fixes and together with doc 23's Step 4, so the paid-run bundle stays frozen and the parity fixes measure
what they were written against. Owner 2026-11-10: "audit it and clarify what it should be in the core things or the
subparts … we'll do it at that time, step by step."

The rule from D-051 still applies: **one owner per job.** Every job has exactly one skill that loads for it.
Anything else that does the same job becomes REFERENCE: it stays searchable and loadable on an explicit
`agylite skill load`, but no route loads it.

## 1. Pins, licenses and scan

| Key | Repo | Pin | Files | License | Scan (scan_upstream.py) |
|---|---|---|---|---|---|
| `astryx` | meta/astryx | `da3dbdc` (2026-11-09, beta) | 10,377 (648 MB checkout, `--depth 1`) | MIT | Flags come from CI, Playwright tests, the docsite and the component source, none of which is extracted. Kept files (`docs/design/*.md`) are clean. The CLI's `install-once` / global mode writes to the home folder and `init` writes `AGENTS.md` (see §2.4) |
| `caldo` | caldoai/skills | `f3cf477` (2026-11-05, 3 commits) | 4 | MIT | clean: no indicators at all |
| `egm` | google/elephant-goldfish-model | `b7d9e27` (2026-11-09, 176 commits) | 301 (14 skill files, 10 agents) | Apache-2.0 | Every flag is in `tests/`, `site/` (the website's analytics), `.github/`, `scripts/pack_plugin.py` or `adapters/opencode/install.py`, and none of these is extracted. Kept skills and agents are prompt-only |

Evidence: `docs/audit/evidence/candidates/` (pins in `upstream-candidates.yaml`, per-file hashes, scan JSON).

## 2. Design: one combined system (Taste + UI UX Pro Max + Open Design + Astryx)

Owner requirement 2026-11-10: the four design upstreams must work together. Each one leads on what it is best at,
so a design request gets the best part of each, not four overlapping playbooks.

### 2.1 What each upstream owns (after Step 4b)

| Job | Owner | Bundled as | Change |
|---|---|---|---|
| Aesthetic direction, composition, page structure, anti-slop, polish | **Taste** | `design/design-direction`, `design/visual-quality` | none |
| Landing pages and hero sections: section order, CTA placement, style, color and font matching (queried databases) | **UI UX Pro Max** | `design/design-system` (engine), `design/frontend` (`ui-styling`) | **routing fix**: "hero section / landing page" also routes `design/design-system`, so `landing.csv` (32 hero patterns) is queried. Today only Taste loads |
| What a landing page says and why (conversion strategy) | Elaya Part A (doc 23) | `design/landing-conversion` | none (doc 23) |
| Craft rules: typography, color, accessibility, RTL, UX laws, forms, motion discipline, required states, DESIGN.md format | **Open Design** | `design/typography`, `accessibility`, `ux`, `motion`, `visual-quality` | none |
| **React implementation on a design system**: components, theming, dark mode, templates | **Astryx** (new) | new `design/react-design-system` | new (§2.2) |
| **Testable layout principles** missing from all three: spatial hierarchy, control rhythm, concentric shape, elevation, iconography, template composition, per-state visuals | **Astryx** (new) | references inside the existing capabilities | new (§2.3) |

How they combine on two typical requests:
- *"Design a landing page with a strong hero"*: Taste leads the look and structure, UI UX Pro Max supplies the
  hero pattern and the palette and font pairing, Elaya supplies the conversion copy, and Open Design's craft rules
  are the checklist.
- *"Build a settings page in our React app"*: Taste leads the direction. If the project has no design system, Astryx
  supplies the components and theme. Open Design and Astryx principles are the checklist.

### 2.2 `design/react-design-system` (Astryx as the React baseline)

- **When it loads**: the project uses React (≥ 19), the request needs components, theming or a design system, and
  the project has **no other design system**. If `package.json` already has shadcn/Radix, MUI, Chakra, Mantine or
  Ant, the project keeps its own system and Astryx does not load. Astryx needs React 19+, so on an older React
  it is only suggested, never installed.
- **What it does**: a short house skill (≈ 2 KB) that drives Astryx's own CLI, which already writes
  agent-ready context:
  `npm i @astryxdesign/core @astryxdesign/theme-neutral @stylexjs/stylex` +
  `npx @astryxdesign/cli init --features agents` (project-local only), then `astryx docs <topic>` for components.
  Theme by overriding CSS custom properties, never by wrapping components. Take a component's source over with
  `swizzle` only when an override cannot do it.
- **Runtime**: npm, the same pattern as designlang (`track: releases`). Agylite bundles no Astryx source. The
  package docs are the source of truth and update themselves.
- **Never**: the CLI's global/`install-once` mode (it writes to the home folder: §2.4).
- **Why not more**: the 150+ components are TypeScript/StyleX source, and copying them into the bundle would add
  hundreds of MB and go out of date. The CLI path gives the same component knowledge, versioned with the user's
  installed package.

### 2.3 Astryx design records (`docs/design/`, 16 files, 130 KB): per-file verdict

The records are framework-neutral, testable rules (`DR1 … MUST/SHOULD`), not React code. Checked against Taste
`SKILL.md`, Open Design `craft/` and UI UX Pro Max data:

| Record | Authority | Verdict | Capability | Why |
|---|---|---|---|---|
| spatial-hierarchy (4.1 KB) | draft | **NEW, keep** | design/visual-quality | proximity, grouping tiers, space before borders; Taste has only general spacing advice |
| control-rhythm (4.0 KB) | draft | **NEW, keep** | design/visual-quality | alignment and density of mixed controls; nothing bundled |
| shape-relationships (3.9 KB) | draft | **NEW, keep** | design/visual-quality | concentric radius for nested surfaces; no match anywhere (Taste, Open Design craft, UI UX Pro Max data) |
| elevation-hierarchy (4.0 KB) | draft | **NEW, keep** | design/visual-quality | perceived depth must match layer order; no match in Taste |
| iconography (20.7 KB) | draft | **NEW, keep** | design/visual-quality | icon meaning, size and fill roles; Open Design has no icon craft file. UI UX Pro Max `icons.csv` is a catalog, not rules |
| template-composition (7.2 KB) | draft | **NEW, keep** | design/frontend | page and block hierarchy, component fidelity |
| user-states (8.7 KB) | current | **NEW, keep** | design/ux | how each person-driven state looks. Open Design `state-coverage` keeps owning *which* states must exist |
| system-states (6.9 KB) | draft | **NEW, keep** | design/ux | loading, status and disabled rules (no layout shift, meaning survives color). Same split as above |
| mobile-typography (4.4 KB) | current | **NEW, keep** | design/typography | Open Design typography has no mobile rules |
| typography-hierarchy | draft | DUPLICATE, REFERENCE | — | Open Design has three typography files |
| color-emphasis | draft | DUPLICATE, REFERENCE | — | Open Design `color.md` + UI UX Pro Max `colors.csv` |
| motion | draft | DUPLICATE, REFERENCE | — | Open Design animation-discipline + Emil Kowalski motion own motion |
| reduced-motion (12.7 KB) | current | **compare in Step 4b**, default REFERENCE | design/accessibility | Open Design's baseline covers reduced motion briefly; keep this one only if the side-by-side shows a real gap |
| bidirectionality (15.3 KB) | current | **compare in Step 4b**, default REFERENCE | — | same job as Open Design `rtl-and-bidi` (12.2 KB, bundled and measured); a swap needs a reason |
| ordered-collection-reordering | current | REFERENCE | — | niche (drag to reorder); searchable, not routed |
| agentic-states | draft (seed) | REFERENCE | — | the record says it "intentionally does not approve visual treatments" yet; revisit when it does |

Kept: 9 records, ≈ 64 KB. They are references inside their capabilities, so a route loads only the matching
capability's files, never all 64 KB. Each kept file keeps its Meta copyright line and Astryx's MIT LICENSE.
Frontmatter fields such as `owners` and `review_triggers` are internal Astryx workflow and are stripped (ADAPT).

### 2.4 Excluded from Astryx

`packages/**` (component source, CLI source), `apps/**`, `internal/**`, `.github/**`, `scripts/**`, `.changeset/**`,
`.claude/**` (contributor commands for the Astryx repo itself), `docs/specs|families|architecture|contributing/**`
(Astryx's own governance).

`internal/vibe-tests/` is REFERENCE for the Step 5 design suite: it is a design benchmark with an LLM design judge
and could inform the `design` suite's scorer. Agylite takes the ideas only, never the code, because the code
calls the Gemini API.

The global CLI mode (`install-once`, `init --global`) writes to the home folder, so the house skill forbids it.

## 3. Caldo: `untangle-codebase`

### What it is

One skill (9.6 KB, `disable-model-invocation: true`): a whole-codebase refactor run as a goal. It lists every
problem under three headings (hidden links, needless links, surplus) plus every special case, redesigns from first
principles, fixes everything, then has subagents re-check until nothing is left. It has two opt-in extras: drop
comments that restate code, and drop tests that cannot fail. It keeps a decision log.

### Overlap check

| Bundled today | Job | vs Caldo |
|---|---|---|
| Pocock `improve-codebase-architecture` (owner of `engineering/architecture`) + `codebase-design` | find a few **deepening opportunities** in hot spots, pick one, grill it | same vocabulary (Caldo cites "deep modules"), different scope: Pocock = targeted, one change; Caldo = whole codebase, end to end |
| Ponytail / Addy `code-simplification` (`engineering/simplicity`) | keep a change small; simplify recent code | change-level, not codebase-level |
| gstack `test-audit` | find low-value tests | Caldo's tests extra does the same job, but only inside its own flow |

**Routing today:** `agylite route "untangle this whole codebase so agents can work in it"` →
`engineering/ai-systems` + `codebase/repository-understanding`. That is wrong: the word "agents" pulls in AI
systems, and no refactoring skill loads.

**Verdict: keep, as a second entry point of `engineering/architecture` for one job: whole-codebase restructuring.**
- Routing rule with `skill:` (D-050 hint) on intents "untangle", "restructure / refactor the whole codebase",
  "make the codebase easier for agents", "reduce coupling across the codebase".
- Pocock stays primary for every other architecture request (targeted deepening).
- Bundled whole (COPY + LICENSE). One ADAPT line: the skill's "do not stop until nothing is left" runs under
  Agylite's lifecycle. The decision log goes in the plan, and every batch of fixes is verified
  (`agylite verify`) before the next one.
- gstack `test-audit` stays the owner of test audits outside a whole-codebase refactor.

## 4. Elephant-Goldfish Model (EGM)

### What it is, in plain words

EGM is a way of working, written as prompts. It has no engine code.
- **Elephant** = the session that holds the context. It talks with you and drafts a design document.
- **Goldfish** = fresh subagents that have **not** seen the conversation. They read only the document and the
  code it points to, so they catch what the conversation took for granted: unstated assumptions, undefined
  terms, steps the implementer would have to guess.
- The Elephant then goes through the findings with you. It defends the choices that were right and fixes the
  rest. You approve the spec before any code is written.

| EGM part | What it does |
|---|---|
| `egm-brainstorm` (15 KB) | questions + a quick Goldfish check → `concepts_brief.md` |
| `egm-draft` (17 KB) | writes the design doc section by section |
| `egm-review` (24 KB) | five Goldfish passes in fresh contexts: zoom-out (simplicity, YAGNI), comprehension (naive reader), design critic (scale, cost, risk), zoom-out again, implementation readiness (nothing left for the coder to decide) |
| `egm-review-loop` (10 KB) | the same review for any document (README, plan, spec) against chosen standards, in rounds |
| `egm-resolve` (8.5 KB) | the Elephant's side: triage findings, keep or fix, ask you at decision points |
| `egm-drift-report` (3.2 KB) | compares design docs or READMEs with the code and reports only the differences |
| `egm-bootstrap` (24 KB) | writes a README in every directory of a subtree |
| 10 agents + `resources/document_standards` | the reviewer personas and the standards they check |

### What Agylite has today vs what EGM adds

| Job | Agylite today | EGM adds? |
|---|---|---|
| Interview the user, write the spec | Pocock `grilling` + `to-spec` (`engineering/planning`) | no: `egm-brainstorm` and `egm-draft` do the same job → REFERENCE |
| **Independent review of a spec or plan before code** | nothing. gstack's adversarial pass reviews **code diffs**. The plan reviews (`plan-eng-review`, …) run in the same context that wrote the plan. `agylite route "review this design doc before we implement it"` loads implementation + **visual** design capabilities (the word "design") | **yes: main gain.** Fresh-context personas, then the Elephant resolves the findings |
| **Design doc vs code drift** | nothing. `agylite route "check whether our design docs drifted from the code"` → documentation + visual design-direction. gstack `document-release` updates docs after a release; it does not report spec drift | **yes**, a small one (3 KB) |
| Per-directory READMEs | ECC `codebase-onboarding`, Graphify code graph | duplicate → REFERENCE |
| Engine code to replace Agylite parts | — | **none.** EGM's Python is packaging, tests and an OpenCode installer |

### Verdict

- New capability **`engineering/spec-review`** (intent: review a design doc / spec / plan / RFC before
  implementing, fresh-eyes review, goldfish review). Whole skills loaded: `egm-review` (lead) + `egm-resolve`. All 9
  reviewer agents its five stages spawn are bundled as agent files: `zoom_out`, `inventive_catalyst` (TRIZ, stage 1),
  `comprehension`, `design_critic`, `structural`, `style`, `implementation_readiness`, `codebase_details`,
  `synthesizer`. So is `resources/document_standards/` (the standards each reviewer checks against).
  `egm-review-loop` is an entry point for non-spec documents.
- `egm-drift-report` → entry point of `engineering/documentation`, routing rule on "drift / design docs vs code".
- `egm-brainstorm`, `egm-draft`, `egm-bootstrap`, `bootstrap_orchestrator` → REFERENCE.
- **Lifecycle hook-in**: on `FEATURE` / `ARCHITECTURE_CHANGE` routes, the plan step suggests
  `engineering/spec-review` after `to-spec`. Agylite suggests it and never runs it on its own, because each review
  spawns 5+ subagents (cost). Bug fixes never get it (EGM's own rule).
- **Routing fix (applies regardless of EGM)**: "design doc / design document / spec" must not trigger visual
  `design/*` capabilities. Add a scenario test for each of the three misroutes above.
- **ADAPT** (paths only): EGM skills read `${CLAUDE_PLUGIN_ROOT}/docs/claude.md` and `resources/…`. These are
  rewritten to bundle paths. If the host has no subagent tool, they stop (EGM's own rule: "a review in the same
  context is not a Goldfish review"). LICENSE (Apache-2.0) is copied with the files.

## 5. Size and context budget

| Item | Loaded when | Size |
|---|---|---|
| `design/react-design-system` house skill | React + no design system | ≈ 2 KB |
| Astryx records | as references of their capability | 4–21 KB each, 64 KB total, never all at once |
| Caldo `untangle-codebase` | whole-codebase refactor only | 9.6 KB |
| EGM `egm-review` + `egm-resolve` | spec review only | ≈ 33 KB (the 9 agents, ≈ 43 KB, load in the subagents, not the main context) |

Nothing is added to the always-loaded L0 (`test_p25` ceiling unchanged).

## 6. Step 4b checklist (when the plan reaches it)

The full, detailed Step 4b instructions, including the multi-agent upgrade (synthesizer merge for every review,
resolve gate, re-check loop, drift check, host subagent flag), are in `docs/plan/IMPLEMENTATION_PLAN.md`, section
"Step 4b — Astryx, Caldo, EGM and the multi-agent review upgrade (detailed)". The list below is the short version.

1. Move the three pins from `candidates/` into `upstream-staging-snapshot.yaml`, `extraction-rules.yaml`,
   `config/upstreams.yaml` (tracking as proposed), `licenses.json`; regenerate hashes and notices.
2. Astryx: extraction rules per §2.3/§2.4; house skill + card `design/react-design-system`. Side-by-side read of
   `reduced-motion` and `bidirectionality` vs Open Design, then record the final verdict here.
3. Caldo: COPY + routing rule with `skill:` hint.
4. EGM: card `engineering/spec-review`, agents, path ADAPTs, drift-report entry point.
5. Routing: hero/landing → also `design/design-system`; "design doc / spec" ≠ visual design; one scenario test
   each for hero, React design system, untangle, spec review, drift.
6. Overlap test + `agylite validate` check (as in doc 23): every REFERENCE file above is never loaded by a route.
7. Normal tests green, bundle rebuilt, self-tests pass.

**Paid suites (owner 2026-11-10: dry run and cost estimate first, then ask):** joined to the Step 5 batch.
- `spec-review` suite: specs with planted gaps; three arms (no skill / EGM original / AgyLite); graded on gaps
  found and on false findings. EGM's own `test_scenarios.yaml` files are a starting point.
- Astryx is added to the planned combined `design` suite (Open Design + UI UX Pro Max) as React-app tasks.
- Caldo: free tests only (routing + rewrite). A paid suite for a whole-codebase refactor would cost too much to
  run for each session.
