# DESIGN.md format

A project's `DESIGN.md` is the design system its UI is built from. `agylite design extract` writes it from 1-3
inspiration sites (MP4 §2), and the owner approves it before any UI code is written.

AgyLite follows **designlang's** format, because designlang generates the file:

- YAML front matter: `site`, `url`, `generator`, and `tokens` (colors, typography, spacing, radii, shadows). AgyLite
  adds `sources` (URL, extraction date, designlang version), `mode: inspiration` and, when needed,
  `design_check_overrides` (limits `agylite design check` reads; the first use is recorded as a design decision).
- Eight top-level (`#`) sections: Overview, Colors, Typography, Layout, Elevation and Depth, Shapes, Components,
  Do's and Don'ts (designlang `src/formatters/design-md.js`, `formatDesignMd`).

Open Design's reference systems (`files/opendesign/design-systems/*/DESIGN.md`, 152 bundled, e.g. `apple`) use a
different layout: no front matter, a `#` title, then nine numbered `##` sections — Visual Theme & Atmosphere, Color
Palette & Roles, Typography Rules, Component Stylings, Layout Principles, Depth & Elevation, Do's and Don'ts,
Responsive Behavior, Agent Prompt Guide. The topics overlap; Open Design adds atmosphere, responsive behaviour and an
agent prompt guide, and has no machine-readable tokens. They stay reference examples (precedence 6) and are never
converted or imposed.
