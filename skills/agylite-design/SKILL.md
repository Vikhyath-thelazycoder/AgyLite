---
name: agylite-design
description: UI/UX and visual design built in code (inspiration sites to an approved DESIGN.md, Taste v2.1 directions, design systems, typography, motion, native mobile), verified with Taste lint and inspect and the design-token check — use when asked to design, redesign, restyle or polish an interface, or to build a UI from inspiration sites.
disable-model-invocation: true
---

# Agylite Design

Produces a built interface that follows one chosen direction and passes Taste inspect and lint with 0 FAIL. It
takes systems from inspiration, never identity, and writes no UI code before the owner has approved DESIGN.md or
picked a direction.

## Use when · Not for

- Use when: a new UI, a redesign, "this looks generic", a design system, typography, motion or a landing page.
- Not for: the behaviour behind the UI → `agylite-engineering` · a diagram → `agylite-diagrams` · a launch video →
  `agylite-media` · the page's SEO → `agylite-seo`. Design requests do not activate engineering or SEO capabilities
  unless the route selects them.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>" --paths <files…>`, then `agylite context --request "<the user's request>" <id>…`.
  Taste's skill loads whole: `agylite skill load taste/design-taste-frontend`.
- **Recorded decisions:** `agylite decide list --kind design`. Keep to them.
- **When sources disagree, this order wins:** (1) the owner's explicit instruction; (2) the project's existing
  design system (`DESIGN.md`, `design-system/`, tokens in code); (3) the DESIGN.md extracted from inspiration;
  (4) Taste v2.1 house rules (its tells, the House rules and Laws of the craft); (5) UI/UX Pro Max
  (`agylite design search|system`); (6) Open Design reference systems, as examples, never imposed.

## Steps

### A. With inspiration URLs (the route has `design/inspiration-extract`)

1. **Extract.** `agylite design extract <url> [<url> [<url>]]`. Expect: DESIGN.md and MERGE_NOTES.md. Show the
   summary, then **stop: the owner reviews DESIGN.md.** Record the approval:
   `agylite project answer design-md-approved "<who, when>"` and `agylite decide add --kind design --topic DESIGN.md
   --decision "DESIGN.md approved" --reason "<who, when>"`. Move on when: the approval is recorded. No UI code
   before that.
2. **Directions.** `agylite design taste draw --sector <s> --brief "<one line>" --keep palette,type --options 3`.
   DESIGN.md fixes palette and type; Taste deals composition, hero, sections and the idea. Move on when: the owner
   has picked one (`--direction <id>`).
3. **Build** in the project's stack, following Taste's "Build it, still" and house rules. Use
   `agylite design search "<product type>"` for UX rules and stack guidance. Tokens come from DESIGN.md only.
4. **Inspect loop.** `agylite design taste inspect <local url or file>`. Fix every FAIL, then go through the juror
   rubric (`files/taste/skills/taste-skill/references/critique.md`) and look again. Move on when: 0 FAIL.
5. **Done** when `agylite verify [--inspect <url or file>]` passes: the project's tests, types, lint and build
   **and** `agylite design check`, `agylite design taste lint`, `agylite design taste inspect` with 0 FAIL.

### B. Without inspiration

`agylite design taste draw --sector <s> --brief "<one line>" --options 3` → the owner picks → steps A3 to A5. With
an existing design system, add `--keep palette,type` (precedence 2).

### Inspiration, not cloning

Take systems: tokens, scale, spacing rhythm, radii, motion curves, component anatomy, layout patterns. Take never
identity: logos, wordmarks, brand illustrations, product screenshots, copy or slogans, trademarked names, the brand
colour as primary identity (extract shifts it at least 20° in hue and says so in MERGE_NOTES.md). A commercial font
becomes the nearest open-licensed font, recorded. Only an explicit owner instruction for internal work overrides
this, recorded with `agylite decide add`.

## Output

```markdown
Direction: <id and name> — <one line: audience, tone, why this one>
Sources: <DESIGN.md approved by <who, when> | existing design system | none>
Built: <screens or sections>; states: <hover, focus, disabled, empty, loading, error>; widths: 1440 / 768 / 390
Checks: inspect <n> FAIL, <n> WARN · lint <result> · design check <result> · `agylite verify` <result> (<evidence file>)
Deviations: <a rule broken on purpose, why, the decision that records it>, or "None"
Not done: <what is missing>, or "None"
```

## Quality bar

- Inspect and lint ran after the last edit, and the counts in the answer are from that run.
- Every colour, type size, spacing value and radius is a token from DESIGN.md or the design system. No one-off values.
- Every interactive element has hover, focus and disabled states; every data view has empty, loading and error states.
- Real content: no lorem ipsum, no grey placeholder boxes, no invented customer logos, quotes or numbers.
- It holds at 1440, 768 and 390 px with no horizontal scroll.
- Nothing of an inspiration site's identity is in the result.
- A screenshot is shown only together with passing checks, never instead of them.

## Stop and ask

- DESIGN.md approval (step A1) and the choice of direction (step A2). Do not pick for the owner.
- An inspect FAIL you think is wrong: ask before allowing the rule, and record the decision.

## When something fails

| What you see | What to do |
|---|---|
| `extract` fails for one URL | Go on with the others and say which failed. With none left, use path B. |
| The extract or browser runtime is missing | `agylite runtime status`; `agylite runtime install designlang` (or `browser`) when the owner agrees. |
| `draw` rejects `--sector` | It prints the valid sectors. Pick the closest; `other` only when nothing fits. |
| `inspect` cannot open the page | Report the check as BLOCKED, not as passed. |
| The direction conflicts with the existing design system | The existing system wins (precedence 2): draw again with `--keep palette,type`. |

## References (read only when needed)

- `references/examples.md` — a good and a weak final answer for the same landing page, with notes.

Verification policy: `config/verification.yaml` (design work adds Taste lint and inspect). No MCP, no `--smart`, no
API keys to designlang, no mockup tool. End your answer with the output of `agylite used` (what this work used).
