---
name: react-design-system
description: Build React 19 UI on Astryx when the project has no design system yet; project-local CLI, look things up on demand.
---

# React design system (Astryx)

Taste still leads the look. This guide only decides the component layer. Open Design craft rules and the Astryx
design records (spatial hierarchy, control rhythm, shape, elevation, iconography, states) are the checklist.

1. **Detect first.** Read `package.json`. If it already has a design system (shadcn/Radix, MUI, Chakra, Mantine, Ant
   Design or a house kit), stop here and use that one. If React is below 19, suggest Astryx to the user and do not
   install it.
2. **Install project-local only:**
   `npm i @astryxdesign/core @astryxdesign/theme-neutral @stylexjs/stylex` and `npm i -D @astryxdesign/cli`, then
   `npx astryx init --features agents` (it writes the project's `AGENTS.md` block; show the user that diff).
3. **Never the global mode.** Do not run `astryx install-once` or `astryx init --global`: they write to the home
   folder.
4. **Look things up on demand:** `npx astryx docs <component|topic>`. Never paste the whole catalog into context.
5. **Theme by overriding CSS custom properties.** Use `npx astryx swizzle <component>` (take over a component's
   source) only when an override cannot do it. Put style overrides in `className`, in whatever the project already
   uses (Tailwind, CSS modules).
6. **Done** means `agylite verify` passes, including `--browser` for the screens you changed.

## Report

- What step 1 found: the React version and the design system already present, or "none".
- What was installed (package names and versions), or why nothing was.
- The tokens you overrode and where; each swizzled component and why an override could not do it.
- The `agylite verify --browser` result with its evidence file.

## Before you finish

- No second design system was added next to an existing one.
- Nothing was written outside the project (no global install).
- Component props and names come from `npx astryx docs`, not from memory.
- Every colour, spacing and radius is a theme token or an override of one; no one-off values.
