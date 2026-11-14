---
name: agylite-codebase
description: Understand an existing codebase before changing it (the files a change affects, the tests that cover it, and answers with file:line) from the project's code graph via `agylite codebase` — use when asked how code works, what a change will touch, or before editing a project you have not read.
disable-model-invocation: true
---

# Agylite Codebase

Produces a narrow, cited picture of the code: which files and tests a change reaches, and answers that point to
`file:line`. It never reads or pastes the whole repository, and it never calls a file unaffected when it does
not know.

## Use when · Not for

- Use when: `agylite route` selects a `codebase/*` capability or returns an `impact` step; someone asks how
  something works, where it lives or what a change will touch.
- Not for: a new project with no code (start from requirements) · drawing the architecture → `agylite-diagrams` ·
  making the change → `agylite-engineering`.

## Steps

1. **Impact of a change** (from the project directory):

   ```bash
   agylite codebase affected                       # files changed in the working tree (git status)
   agylite codebase affected --paths src/payments  # or the files and directories the task will touch
   ```

   Expect: `files` (at most `limit`, default 12), the `tests` that cover them, `omitted` (how many the limit
   dropped) and `unknown` (what could not be resolved). Read only the listed files and run the listed tests first.
   Move on when: you can name the files you will read and the tests you will run.

2. **Questions about the code.** These return scoped subgraphs with `file:line`, not file dumps:

   ```bash
   agylite codebase query "how are webhooks verified"
   agylite codebase explain PaymentService
   agylite codebase path WebhookHandler charge
   ```

   `query` finds where something is done, `explain` describes one symbol and its neighbours, `path` shows how one
   symbol reaches another. Move on when: each claim you will make has a `file:line` you opened.

3. **Open the lines.** The graph tells you where to look; the answer comes from the code. Read the cited lines
   before you state what they do.

4. **A stale graph.** `agylite codebase update` rebuilds it after large changes (`affected --update` does the same
   first).

## Output

```markdown
<The answer in one or two sentences.>

How it works
1. `path/file.py:42` — <what happens here>
2. `path/other.py:17` — <what happens next>

Affected by the change: <files>
Tests that cover it: <tests>, or "None found"
Unknown: <what the analysis could not resolve>, or "None"
Analysis: <code graph | limited structural analysis (say why)>
```

For a plain impact question, the last four lines are enough. Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every statement about what the code does cites a `file:line` that you opened and read.
- Nothing is described from a file or function name alone.
- Each `unknown` entry is reported as UNKNOWN, never as "not affected".
- When `omitted` is above zero, the answer says so and the scope was narrowed, not ignored.
- When the result carried a `notice`, the answer says that limited structural analysis was used.
- The answer is about the question asked. It is not a tour of the repository.
- "Tests that cover it: None found" is stated when that is the case; it is a finding, not something to hide.

## Stop and ask

- The question is too wide to answer from 12 files: ask which part matters, or propose the split.
- Installing the graph runtime: `agylite runtime install graphify` needs the network, so ask first.

## When something fails

| What you see | What to do |
|---|---|
| The result has a `notice` ("graph-based analysis unavailable; limited structural analysis used") | Say so in the answer. Only Python and relative JS/TS imports were followed. `agylite runtime status` shows why. |
| `omitted` is large | Ask for a narrower path, or run `affected` per directory. Do not read everything. |
| `query` returns nothing | Try the words the code uses (a class or function name), then `explain` on a known symbol. Say when nothing was found. |
| The graph looks out of date | `agylite codebase update`. |
| The project is new and has no code | There is no codebase step. Start from the requirements. |

## Rules

- The graph lives in the OS data directory, never in the project.
- Do not run `graphify` directly, and never use `graphify hook`, `install`, `watch`, `serve` or `extract`: the OS
  blocks them (no git hooks, no background process, no MCP, no LLM extraction).

## References (read only when needed)

- `references/examples.md` — a good and a weak answer to the same "how does it work" question, with notes.

End your answer with the output of `agylite used` (what this work used).
