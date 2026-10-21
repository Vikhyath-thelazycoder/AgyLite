---
name: agylite-design
description: UI/UX and visual design work — inspiration sites to an approved DESIGN.md, Taste v2.1 directions, design systems, typography, motion, native mobile — built in code and verified with Taste lint/inspect and the design-token check.
---

# Agylite Design

**Route first:** `agylite route "<request>" --paths <files…>`, then load what it selects with
`agylite context --request "<the user's request>" <id>…` (Taste's skill loads whole: `agylite skill load
taste/design-taste-frontend`). Keep to recorded design decisions: `agylite decide list --kind design`.

**When sources disagree, this order wins:** (1) the owner's explicit instruction; (2) the project's existing design
system (`DESIGN.md`, `design-system/`, tokens in code); (3) the DESIGN.md extracted from inspiration; (4) Taste v2.1
house rules (`references/tells.md`, the House rules and Laws of the craft); (5) UI/UX Pro Max
(`agylite design search|system`); (6) Open Design reference systems — examples, never imposed.

## A. With inspiration URLs (the route has `design/inspiration-extract`)

1. `agylite design extract <url> [<url> [<url>]]` → show the summary → **stop: the owner reviews DESIGN.md.** Record the
   approval (`agylite project answer design-md-approved "<who, when>"` and `agylite decide add --kind design --topic
   DESIGN.md --decision "DESIGN.md approved" --reason "<who, when>"`). No UI code before that.
2. `agylite design taste draw --sector <s> --brief "<one line>" --keep palette,type --options 3`: DESIGN.md fixes
   palette and type; Taste deals composition, hero, sections and the idea. The owner picks; `--direction <id>`.
3. Build in the project's stack: Taste's "Build it, still" and house rules; `agylite design search "<product type>"`
   for UX rules and stack guidance; tokens from DESIGN.md only.
4. Loop: `agylite design taste inspect <local url or file>` → fix every FAIL, then the juror rubric
   (`references/critique.md`), look again.
5. Done: `agylite verify [--inspect <url or file>]` passes — the project's tests, types, lint and build **and**
   `agylite design check`, `agylite design taste lint`, `agylite design taste inspect` with 0 FAIL.

**Inspiration, not cloning:** take systems (tokens, scale, spacing rhythm, radii, motion curves, component anatomy,
layout patterns); never identity (logos, wordmarks, brand illustrations, product screenshots, copy or slogans,
trademarked names, the brand colour as primary identity — extract shifts it ≥ 20° in hue and says so in
MERGE_NOTES.md). Commercial fonts → the nearest open-licensed font, recorded. Only an explicit owner instruction for
internal work overrides this, recorded with `agylite decide add`.

## B. Without inspiration

`agylite design taste draw … --options 3` → the owner picks → steps A3–A5. With an existing design system, use
`--keep palette,type` (precedence 2).

Verification policy: `config/verification.yaml` (design work adds Taste lint and inspect, MP4). Screenshots count
together with passing tests and build, never instead of them. No MCP, no `--smart`, no API keys to
designlang, no mockup tool. Design requests do not activate engineering or SEO capabilities unless the route selects
them.

End your answer with the output of `agylite used` (what this work used).
