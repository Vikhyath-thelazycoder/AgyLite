---
name: research-code
description: GitHub repositories, code and issues through the gh CLI (agylite research github), read-only; compare libraries by their repos, not by blog posts.
---

<!-- Agylite-authored (MP5 §1.4). Derived from Agent-Reach (Panniantong/Agent-Reach, MIT, "Agent Eyes")
skill/references/dev.md. -->

# Code research (GitHub)

## Commands

```bash
agylite research github "<query>"                    # repositories, sorted by stars
agylite research github "<query>" --type code        # code search
agylite research github "<query>" --type issues      # issues and pull requests
agylite research github "<query>" --n 20
```

They need the `gh` CLI, signed in by the user (`gh auth login`). If `gh` is missing, `agylite research doctor` says
so: tell the user, and read repositories through the web instead (`agylite research read https://github.com/<o>/<r>`).

## Method

- To compare libraries, read each one's README, latest release and open-issue count from its repo; prefer the
  project's own docs over third-party lists.
- For a specific file, read it raw: `agylite research read https://raw.githubusercontent.com/<o>/<r>/<ref>/<path> --direct`.
- Read-only: never open issues, comment, star or fork.

## Output

Cite each repo, file or issue by URL (with the commit or tag when it matters). Findings go to
`docs/research/<slug>.md` with a source list.
