# Migrating from v1.0.1 (Vikhyath AI Engineering OS) to v2 (Agylite)

v1 was a set of routing notes that assumed ECC, Graphify, gstack and others were installed as separate plugins. v2 is
a working local OS: one CLI, one bundle built from pinned upstream commits, one router, local verification.

## Install

```bash
git clone https://github.com/Vikhyath-thelazycoder/AgyLite.git
cd AgyLite
scripts/install                      # central install into ~/.agylite and the local bundle (network once)
export PATH="$HOME/.agylite/core/bin:$PATH"
agylite doctor
```

Then update the host plugin (`claude plugin update agylite@agylite-marketplace`, or reinstall). Run `agylite doctor`
to see separately installed upstream plugins; their selected content is already in the bundle, so removing them saves
their always-loaded descriptions (about 31,800 est. tokens per turn for ECC, Open Design and UI/UX Pro Max on the
development machine).

## Names

| v1 | v2 |
|---|---|
| plugin `vikhyath-ai-engineering-os@vikhyath-marketplace` | `agylite@agylite-marketplace` |
| CLI `vikhyath` | `agylite` (`vikhyath` still works) |
| `~/.vikhyath`, `VIKHYATH_HOME` | `~/.agylite`, `AGYLITE_HOME` (an existing `~/.vikhyath` or `VIKHYATH_HOME` is still used) |
| project `.vikhyath/` | `.agylite/` (an existing `.vikhyath/` is used while it is the only one) |
| skills `vikhyath-*` | `agylite-*` |

## Commands

| v1 | v2 |
|---|---|
| `scripts/doctor`, `scripts/validate`, `scripts/benchmark` | `agylite doctor`, `agylite validate`, `agylite benchmark [--compare]` (scripts remain as wrappers) |
| "Route to ECC/Graphify/…" by reading skills | `agylite route "<request>"` + `agylite context <ids>` |
| `workflows/*.md` | the route's `lifecycle` (`config/lifecycle.yaml`) |
| install Graphify, gstack, … separately | `agylite runtime install graphify|seo|brag`; everything else is in the bundle |
| — | `agylite verify`, `agylite codebase affected`, `agylite design check`, `agylite seo run`, `agylite media plan`, `agylite dashboard`, `agylite update|rollback|gc`, `agylite adapters …` |

## Behaviour changes

- Verification is local and test-first; browser, Chrome DevTools and screenshot verification are disabled.
- Simplicity review runs only when asked for.
- "Runtime tested" host claims are replaced by measured status: FILES_PRESENT, INSTALLED, RUNTIME_VERIFIED.
