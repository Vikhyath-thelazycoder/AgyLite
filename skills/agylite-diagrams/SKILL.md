---
name: agylite-diagrams
description: Architecture, sequence, workflow, data-flow, lifecycle, ERD, class, tree, timeline and waterfall diagrams of a system or this codebase, as checked standalone HTML made with Archify (`agylite diagram`) — use when asked to draw, diagram, map or visualise a system, a flow or the code's structure.
disable-model-invocation: true
---

# Agylite Diagrams

Produces one standalone HTML diagram that has passed Archify's validation and its browser check. For a codebase,
every node comes from the code and cites its files. It draws nothing that it did not find, and it makes an
explainer page only when the user asks for one.

## Use when · Not for

- Use when: a diagram of a system, a request flow, a data model, a lifecycle or the code's structure is wanted.
- Not for: a written explanation of how code works → `agylite-codebase` · a UI or a page design →
  `agylite-design` · a video or a slide deck → `agylite-media`.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>"` → `engineering/diagrams`.
- **Load Archify's skill whole:** `agylite skill load archify/archify`. It defines the diagram types and the
  candidate format; this file only says how Agylite runs it.
- **One diagram answers one question.** Know the question (for example "what happens when a payment webhook
  arrives?") before you choose a type.

## Steps

1. **Choose the type.** When unsure: `agylite diagram guide "<scenario>"`. Expect: the type that fits and why.
   Move on when: you can say which question the diagram answers and why this type shows it.
2. **Collect evidence** (for this codebase): `agylite codebase update`, then `agylite codebase query|path|explain`
   for the parts the diagram shows. Follow Archify's repository authoring guide
   (`files/archify/archify/references/repository-authoring.md`). Expect: for every node and every edge, the file
   that proves it. Move on when: nothing in your list is there because "systems like this usually have one".
3. **Author** the candidate in `.archify/<type>-<slug>-<timestamp>/`. Suggest adding `.archify/` to `.gitignore`;
   never edit `.gitignore` without asking.
4. **Finalize.** `agylite diagram finalize <type> <candidate.json> <output.html> --json`. It validates, delivers,
   runs the strict check and the headless Chrome browser-check. Expect: exit 0 and the receipts. Fix what it
   reports and run it again. Move on when: it exits 0.
5. **Verify** (when the work is tracked): `agylite verify --diagram <output.html>` records the result. The
   browser-check runs whenever Chrome is present; without Chrome it is reported as skipped and recorded as
   BLOCKED, never as passed.

## Output

```markdown
Diagram: <path of the output HTML> (<type>)
Answers: <the question, in one line>
Shows: <n> nodes, <n> edges; each node cites its files
Left out on purpose: <parts not drawn, and why>, or "None"
Checks: finalize exit 0 (validate, strict check, browser-check <passed | skipped: Chrome not found>)
Not confirmed: <nodes or edges you could not prove from the code>, or "None"
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every node and every edge is backed by a file you read. Nothing was added from general knowledge of how such
  systems look.
- Names in the diagram are the names the code uses (services, classes, tables, queues), not invented labels.
- The diagram answers its one question. Parts that do not help to answer it are left out and listed.
- Each edge has a direction and says what passes along it (a call, an event, a row).
- `finalize` exited 0 on the file you deliver, after your last change to the candidate.
- A skipped browser-check is reported as skipped and BLOCKED, not as passed.
- No explainer page was made unless the user asked for one.

## Stop and ask

- The request can mean two different diagrams (for example the deploy layout or the request flow): ask which.
- Before editing `.gitignore`.
- The system is too large for one readable diagram: propose a split by question.

## When something fails

| What you see | What to do |
|---|---|
| `finalize` exits non-zero | Read its report, fix the candidate, run it again. Do not deliver the HTML of a failed run. |
| Chrome is not installed | The browser-check is skipped. Say so; the result is BLOCKED until it runs. |
| The code graph is unavailable (`notice`) | Say that limited analysis was used, and read the files yourself for each node. |
| A part cannot be proved from the code | Leave it out, or list it under "Not confirmed". Do not draw it as fact. |
| The type does not fit after all | `agylite diagram guide "<scenario>"` again; a wrong type is worse than a late diagram. |

## References (read only when needed)

- `references/examples.md` — a good and a weak delivery of the same diagram, with notes.

Agylite manages Archify updates. Verification policy: `config/verification.yaml`; for diagrams the check is
Archify's own browser-check of the rendered page (`diagram_verification`). No MCP.

End your answer with the output of `agylite used` (what this work used).
