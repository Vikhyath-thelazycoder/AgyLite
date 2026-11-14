# Open-source agent frameworks compared with Agylite

Date: 2026-11-15. Question from the owner: how do the popular open-source frameworks on GitHub run, word their
instructions, route requests and load skills, and what is Agylite missing compared with them?

## Answer

Six frameworks were cloned and read on 2026-11-15: Superpowers, BMAD Method, Spec Kit, OpenSpec, Get Shit Done and
Agent OS. Agylite is ahead of all six in three places: routing is deterministic and tested, the skill text arrives with
the prompt, and results are measured against the original skills with costs. It is behind in what happens around a
single task: none of the six stops after one routed change. They carry a project from idea to shipped work, say what
comes next, size the process to the change, survive a session ending, and let users add their own rules. Fifteen gaps
are listed below, ranked; the first six matter most for the owner's goal ("say what to build and it does everything").

Nothing was changed in Agylite by this research. The owner approved all proposals (A–L) on 2026-11-15; the build order
is the "Gap programme" in `docs/plan/IMPLEMENTATION_PLAN.md`.

## What was read

| Project | Stars (GitHub API, 2026-11-15) | Commit read | Licence |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 317,574 | `22f0b46` (2026-11-03) | MIT |
| [github/spec-kit](https://github.com/github/spec-kit) | 149,789 | `2ee2b1e` (2026-11-12) | MIT |
| [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | 74,861 | `ea635dd` (2026-11-13) | MIT |
| [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | 64,136 | `bdcaab2` (2026-05-31) | MIT |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | 55,367 | `e435a22` (2026-11-12) | MIT per its README |
| [buildermethods/agent-os](https://github.com/buildermethods/agent-os) | 5,605 | `e892e61` (2026-10-07) | MIT |

The Get Shit Done repository says it has moved to `open-gsd/gsd-core`; the copy read here is the old home and may be
behind.

## How each one works

- **Superpowers.** One `SessionStart` hook puts the whole `using-superpowers` skill (3,192 bytes) into every session
  (`hooks/hooks.json`, `hooks/session-start`). That skill tells the agent to invoke a skill "BEFORE any response or
  action" if there is "even a 1% chance" it applies. There is no router: the model picks from 15 skills by their
  descriptions, which state only when to use them ("Use when executing implementation plans…"). The skills chain:
  brainstorming → writing-plans → subagent-driven-development or executing-plans → requesting-code-review →
  verification-before-completion → finishing-a-development-branch.
- **BMAD Method.** One entry skill, `bmad-build`, "Implements a story, feature, or bug fix end to end: plan, code,
  review, verify". It takes a route (`oneshot` or `full`) and a review level (`none`, `quick`, `thorough`), and its
  description tells the agent to skip "obvious, low-risk mechanical maintenance". A second skill, `bmad`, answers
  "what to do next": it reads the active initiative and its tickets, then recommends only installed skills
  (`skills/core-tools/bmad/references/help.md`). v7 installs with `npx skills add`.
- **Spec Kit.** Slash commands in a fixed order: constitution → specify → clarify → plan → tasks → analyze →
  implement → converge (`templates/commands/`). Each command names its next steps in a `handoffs:` block in its
  frontmatter. Bug fixing and idea assessment are separate entry points. Teams change it through extensions, presets,
  bundles, catalogs and project-local overrides (README, "Capabilities").
- **OpenSpec.** Three steps per change: propose (writes `proposal.md`, `specs/`, `design.md`, `tasks.md` in a change
  folder), apply, archive. Archiving merges the change's requirements into the project's living specs (README).
- **Get Shit Done.** About 65 commands and 33 agents. `/new-project` asks deep questions, writes `PROJECT.md`,
  requirements and a roadmap; `/autonomous` runs "all remaining phases autonomously — discuss→plan→execute per
  phase"; `/progress` is the "unified situational command"; `/pause-work` and `/resume-work` hand work across
  sessions. Its hooks watch context usage, guard planning files and scan read content for prompt injection (`hooks/`).
- **Agent OS.** Five commands. It extracts conventions from the codebase into written standards
  (`discover-standards`), injects the relevant ones into the task (`inject-standards`), and shapes a spec.

## Findings: what Agylite is missing

How Agylite was checked: the CLI's command list, `config/lifecycle.yaml`, `config/routing.yaml`, `hooks/hooks.json`,
and a search of `agylite/`, `config/`, `skills/`, `agents/`, `hooks/` and `capabilities/` for each mechanism.

### Most important for the owner's goal

1. **No path from idea to shipped product.** BMAD's `bmad-build` covers plan, code, review and verify in one entry;
   GSD's `/new-project` ends in a roadmap that `/autonomous` then executes; Spec Kit commands hand off to each other.
   Agylite's lifecycle (`UNDERSTAND … RECONCILE`) is per change, and a new-product request routes once. This is
   Step 7 in the plan.
2. **No "what next".** BMAD's `bmad` reads the project's state and recommends the next skill; GSD has `/progress`;
   Spec Kit has `handoffs`. Agylite has `plan index`, `plan show` and `plan locate`, but no command or hook line that
   says what the next step of the project is.
3. **The process is not sized to the change.** BMAD has `oneshot` / `full` and three review levels and tells the
   agent to skip trivial maintenance; GSD has `/quick` and `/fast`; Spec Kit ships a `lean` preset. In Agylite every
   change type has at least three lifecycle steps and no small-change path was found.
4. **Work does not survive the end of a session.** GSD has `/pause-work`, `/resume-work`, a `STATE.md` shown at
   session start and a hook that warns the agent when the context is nearly full. Agylite's session start shows the
   project and phase, but there is no pause or resume command and no context warning; its hooks are `SessionStart`
   and `UserPromptSubmit` only. In this repository the owner keeps a "RESUME HERE" block by hand for the same reason.
5. **No unattended run with stop conditions.** BMAD has `bmad-build-auto` ("without human interaction… report
   status") with `HALT: <reason>`; GSD's `/autonomous` has a "Handle Blocker" step. Agylite has none.
6. **Questions and small talk are routed as work.** Already Step 5c. BMAD separates "help and conversation" from
   actions inside its `bmad` skill.

### Quality and safety

7. **Skills are tested on one host.** Superpowers has test folders for Claude Code, Codex, Antigravity, OpenCode, Pi,
   Kimi, Hermes and Devin, and real-session scenarios that check a skill triggers (`docs/testing.md`). Agylite's paid
   suites run Claude Code only; its 14 entry skills load on Cursor, Codex and Antigravity, where nothing is measured.
8. **No runtime check of content the agent reads.** GSD scans `Read` results and writes to planning files for prompt
   injection. Agylite scans upstream files when the bundle is built; nothing runs at read time, and
   `agylite research read` brings web pages into the session.
9. **No learning loop.** BMAD's `bmad-project-context` "records observed agent mistakes as pitfalls" in the AGENTS.md
   block and `bmad-retrospective` reviews a finished epic against its evidence; GSD has `/extract-learnings`;
   Superpowers has `diagnosing-superpowers` for "a session went wrong". Agylite records decisions, events and what a
   session used, but has no retrospective, pitfalls file or session diagnosis.
10. **No implementer subagents.** Superpowers dispatches one fresh subagent per task, reviews it, and runs a fix loop,
    choosing "the least powerful model that can handle each role"; GSD has executor and verifier agents. All 12
    Agylite agents are reviewers; implementation stays in the main session.

### Reach and customisation

11. **Users cannot add their own rules without editing Agylite.** Spec Kit has extensions, presets and project-local
    overrides; BMAD has `bmad-customize` and modules. No project-local skill or routing-rule folder was found in
    Agylite.
12. **Project conventions are not learned from the code.** Agent OS discovers standards from the codebase and injects
    the relevant ones; Spec Kit has a constitution. Agylite has the code graph (structure) and decisions, not
    conventions.
13. **Install and platforms.** BMAD v7 and others install with `npx skills add`
    ([vercel-labs/skills](https://github.com/vercel-labs/skills), 39,357 stars). Superpowers ships a Windows launcher
    (`hooks/run-hook.cmd`, a PowerShell command in `hooks.json`). Agylite installs as a Claude Code plugin plus a
    `curl … | bash` script.

### Wording

14. **Three wording habits Agylite's own files do not have.** Superpowers tells the agent to announce "Using [skill]
    to [purpose]" and to "create a todo per item" of a checklist, and lists the excuses an agent makes with the answer
    to each ("This is just a simple question" → "Questions are tasks."). Agylite's standard has "Use when / Not for",
    steps, a quality bar, "Stop and ask" and "When something fails", but no announce line, no todo rule and no
    excuses table. Upstream skills that Agylite carries whole keep their own.
15. **Idea check before building.** Spec Kit's assessment ends in "go, needs-clarification, or kill". Agylite has the
    grilling and idea-refine skills but routes "I have an idea for an app, help me figure out what to build" to
    implementation (probe of 2026-11-15, now in Step 6).

## Where Agylite is ahead

- Routing is a deterministic command with scenario tests; the other five with skills leave the choice to the model.
  An independent test measured 55% skill activation with no hook and 100% with a structured `UserPromptSubmit` hook
  on Sonnet 4.5 (22 prompts, two runs)
  ([Scott Spence, 2026-02-08](https://scottspence.com/posts/measuring-claude-code-skill-activation-with-sandboxed-evals)).
  Agylite's hook goes further and sends the skill text itself.
- Upstream skills are pinned, hashed, licence-recorded and updated only after review. None of the six does this for
  third-party content; Spec Kit says of its catalogs "Catalog listings are not audits or endorsements".
- Every bundled skill is measured against no skill and against the original, with cost per session.

## Proposals for approval

| # | Proposal | Size | Covers gaps |
|---|---|---|---|
| A | `agylite next`: read the plan and state, print the next step and why; the hook adds it after RECONCILE | small | 2 |
| B | A small-change path: one-file, low-risk edits get UNDERSTAND → IMPLEMENT → VERIFY only | small | 3 |
| C | `agylite handoff` and resume: write the done / left / next block at pause, show it at session start | small | 4 |
| D | Announce line and one-todo-per-step rule in the prompt hook and the entry-skill standard | small | 14 |
| E | Session diagnosis from the event log (`agylite diagnose`) and a project pitfalls file | medium | 9 |
| F | Injection check on `agylite research read` output and on files written to the plan | medium | 8 |
| G | Project-local skills and routing rules (a folder in the project, checked by `validate`) | medium | 11 |
| H | Conventions file from the codebase, injected with the route | medium | 12 |
| I | A free skill-trigger check on one more host (Codex or Cursor) | medium | 7 |
| J | Product pipeline with stages, sizing and an unattended mode with stop conditions (Step 7) | large | 1, 5 |
| K | Implementer subagents per task with a review and fix loop | large | 10 |
| L | Windows launcher and an `npx skills` package of the entry skills | medium | 13 |

Recommended order: A, B, C, D first (small, and they change every session), then E and F, then J built on A to C.
G, H, I, K and L after Step 6.

## Where sources disagree

- **Questions.** Superpowers says "Questions are tasks. Check for skills." BMAD keeps conversation apart from actions
  and tells the agent not to volunteer its build skill for trivial edits. Agylite's own sessions (2026-11-15) show the
  cost of the first rule with a router: a question pulled in a 20 KB security skill. BMAD's rule fits Agylite better.
- **How much process.** Spec Kit and GSD lead with full phase sequences; OpenSpec calls itself "fluid not rigid…
  iterative not waterfall" and BMAD "right-sized". No source measures which gives better results.

## Unverified

- Whether these mechanisms improve results. None of the six repositories was run; the report describes what their
  files say, not how well they work.
- Star counts in blog posts differ from the GitHub API figures above; only the API figures are used.
- Agylite on Windows: the search found only a lock helper that mentions it. Whether install and hooks work there was
  not tested.
- Project-local overrides in Agylite: none found by search; a full read of `agylite/cli.py` was not done.
- The current state of Get Shit Done after its move to `open-gsd/gsd-core`.

## Sources

- obra/superpowers — https://github.com/obra/superpowers (`skills/using-superpowers/SKILL.md`, `hooks/hooks.json`,
  `hooks/session-start`, `skills/subagent-driven-development/SKILL.md`, `docs/testing.md`)
- bmad-code-org/BMAD-METHOD — https://github.com/bmad-code-org/BMAD-METHOD (`README.md`,
  `skills/method/bmad-build/SKILL.md`, `skills/method/bmad-build-auto/SKILL.md`, `skills/core-tools/bmad/SKILL.md`,
  `skills/core-tools/bmad/references/help.md`, `skills/method/bmad-project-context/SKILL.md`)
- github/spec-kit — https://github.com/github/spec-kit (`README.md`, `templates/commands/`)
- Fission-AI/OpenSpec — https://github.com/Fission-AI/OpenSpec (`README.md`)
- gsd-build/get-shit-done — https://github.com/gsd-build/get-shit-done (`commands/gsd/`, `agents/`, `hooks/`,
  `get-shit-done/workflows/new-project.md`, `get-shit-done/workflows/autonomous.md`)
- buildermethods/agent-os — https://github.com/buildermethods/agent-os (`README.md`, `commands/agent-os/`)
- vercel-labs/skills — https://github.com/vercel-labs/skills (star count only)
- Scott Spence, "Measuring Claude Code Skill Activation With Sandboxed Evals" —
  https://scottspence.com/posts/measuring-claude-code-skill-activation-with-sandboxed-evals
