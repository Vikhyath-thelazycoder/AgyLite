---
name: agylite-routing
description: Route a task to the minimum Agylite capabilities with the deterministic `agylite route` command, then load only their context — use when a request arrives without an `Agylite route:` line, or when you need to know which Agylite capability or skill covers a task.
---

# Agylite Routing

Produces the short list of capabilities a task needs, with their context loaded and nothing else. Routing is done
by the OS core, not by reading this file: do not pick capabilities by hand and do not load every skill.

## Use when · Not for

- Use when: the prompt has no `Agylite route:` line (a host without the prompt hook, or the hook is off), or the
  task changed and needs a new route.
- Not for: a prompt that already carries `Agylite route: …`. Claude Code's prompt hook prints that line and the
  load command. Load the listed context before the first edit, also on small tasks, and do not route again.

## Steps

1. **Route.** From the project directory:

   ```bash
   agylite route "<the user's request>" --brief          # one line
   agylite route "<the user's request>"                  # full JSON
   ```

   Add `--paths <files…>` when the request touches known files, `--new` or `--existing` when the project stage is
   known, and `--capability <id>` only when the user names a capability. Expect: `change_type`, `capabilities`,
   `lifecycle`, `confidence`. Move on when: you have the capability ids.

2. **Load context for the routed capabilities only:**

   ```bash
   agylite context --route "<the user's request>"                      # routes and loads in one call (preferred)
   agylite context --request "<the user's request>" <capability-id>…   # ids from an earlier route
   ```

   Always pass the request: it ranks each capability's sections. Move on when: the context is loaded and you have
   read it.

3. **Follow the result**, field by field:

   | Field | What to do |
   |---|---|
   | `capabilities` | They are in guidance order (`config/priorities.yaml`: user requirements → project security → project architecture → methodology → specialists → review → simplicity). On conflicting advice, the earlier one wins. |
   | `dependencies` | Internal capabilities the selected ones need. Use them through those capabilities. |
   | `fallbacks` | Use only when the primary capability cannot decide. |
   | `impact` | Existing projects: run its `command` first and work from the files and tests it returns (`agylite-codebase`). |
   | `lifecycle` | The steps for this change type, in order. Meet each step's `exit` before the next. |
   | `verification_mode` | `tests-and-browser` (`config/verification.yaml`): tests, types, lint, build and recorded evidence; UI work also needs the browser check. |
   | `browser` | `required` → done only when `agylite verify --browser` passes too (screenshots at 1440/768/390, console, network, overflow, flows; you may read the screenshots). `not-needed` → tests only. |
   | `pipeline` | The domain order for multi-domain work (for example SEO audit → engineering → testing). |
   | `review_merge` | Set when several reviewers join a review; see `agylite-review`. |

## Output

Before the work starts, one line to the user:

```text
Route: <change_type> · <capability ids> · confidence <high | low>
```

Then do the work with the routed capabilities. The final answer ends with the output of `agylite used`.

## Quality bar

Check each line before you go on:

- The capabilities came from `agylite route`, not from your own reading of the capability list.
- Only the routed capabilities are loaded. No SEO, media or design capability the route did not select.
- The request text was passed to `agylite context`.
- With `confidence: low`, the user confirmed the intent before the first edit.
- With `unmatched: true`, the user was told in one line; no capability was invented.
- The route was not run a second time for a prompt that already carried it.

## Stop and ask

- `confidence: low` (only a tag or the fallback search matched, no rule did): say what you understood and ask whether it is right.
- The route selects a domain the user clearly did not mean (for example design for a backend bug): say so and ask,
  or route again with `--paths`.

## When something fails

| What you see | What to do |
|---|---|
| `agylite` is not on PATH | Use the `cli:` path from the session bootstrap; `agylite doctor` shows what is wrong. |
| `unmatched: true` | Tell the user in one line that no Agylite capability covers this, then work from `fallback_guidance`. |
| The route looks wrong | Add `--paths`, or `--new` / `--existing`, and route again. Report a repeatable wrong route to the owner. |
| No session bootstrap was shown | `agylite bootstrap --host <your host>` prints the project state and the capability index. |
| A rare need has no routed skill | `agylite skills search "<words>"` searches every bundled skill. |

## Rules

- Simplicity review runs only when the user asks for it.
- New projects start with requirements; existing projects start with codebase understanding.

## References (read only when needed)

- `references/examples.md` — three routes and how to act on each (high confidence, low confidence, unmatched).

End your answer with the output of `agylite used` (what this work used).
