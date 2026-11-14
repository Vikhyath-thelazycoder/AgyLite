---
name: agylite-production
description: Release readiness (plan completion, verification evidence, changelog, migration and rollback) with a READY or NOT READY verdict and the exact blockers — use when asked to prepare, check or approve a release, or whether something is ready to ship.
disable-model-invocation: true
---

# Agylite Production

Produces a release decision: READY, READY WITH ACCEPTED RISKS or NOT READY, with every blocker named and the notes
a person needs to ship and to roll back. It takes no deploy step without the user's explicit go-ahead.

## Use when · Not for

- Use when: a release is being prepared, or someone asks whether a change is ready to ship.
- Not for: reviewing one change → `agylite-review` · running the checks on work in progress → `agylite-testing` ·
  finishing the work that blocks the release → `agylite-engineering`.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "prepare the release" --paths <files…>` → `engineering/release` and
  `testing/release-verification`; load them with `agylite context --request "<the user's request>" <id>…`.
- You need to know what the release contains: the plan phase or tasks it claims, and the commit range since the
  last release (`git log <last tag>..HEAD --oneline`).

## Steps

1. **Plan completion.** `agylite plan show <phase>` for each phase the release claims. Expect: every task with its
   status. A task is done only when it is VERIFIED or COMPLETED with an evidence file. Move on when: each claimed
   task is on one of two lists, done or blocker.
2. **Accepted risks.** A task that is not done blocks the release unless the user accepts the risk. Record each
   acceptance: `agylite decide add --kind process --topic "risk acceptance" --decision "<what ships unverified>"
   --reason "<who accepted, when, why>"`.
3. **Verify the release candidate.** `agylite verify --all` (the full suites: tests, types, lint, build, security
   checks; policy: `config/verification.yaml`), with `--browser` when the release changes UI. Expect: every check
   PASSED and a new evidence file. Evidence from an earlier commit does not count.
4. **Changelog.** Write it from the commit list, in terms of what changes for users. Every user-visible commit has
   a line; nothing is listed that is not in the range.
5. **Migration and rollback.** For every schema, data or config change: the steps to apply it, and the steps to
   undo it, written before anything is deployed. A change that cannot be undone is stated as such.
6. **Operate.** New config and secrets are documented (names, not values); the changed paths can be observed in
   the logs or monitoring the project has.

## Output

```markdown
## Release <version or name> — <READY | READY WITH ACCEPTED RISKS | NOT READY>

Blockers: <numbered: what, where, what would unblock it>, or "None"
Accepted risks: <what ships unverified — who accepted it, decision id>, or "None"

Plan: <n> of <n> claimed tasks done (list any that are not, with their status)
Evidence: `agylite verify --all` → <counts per check> (<evidence file>, commit <sha>)

Changelog
- <user-visible change>

Migration: <steps>, or "None"
Rollback: <steps>, or "Cannot be rolled back: <why and what to do instead>"
Config and secrets: <new names>, or "None"
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- The verdict follows from the lists: any blocker means NOT READY; an unverified item that ships needs a recorded
  acceptance.
- The verify run is on the commit that will ship, in this session, with counts and an evidence file.
- Every claimed task has a status you read from the plan, not from memory or from a commit message.
- Each changelog line matches a commit in the range; no invented or "various improvements" lines.
- The rollback steps are concrete commands or actions. "Revert if needed" is not a rollback plan.
- No secret value appears anywhere in the notes.
- Nothing was deployed, tagged, published or pushed without the user's go-ahead.

## Stop and ask

- Before any deploy, tag, publish or push.
- When a task is not done and the user has not said whether to accept the risk or to wait.
- When a migration cannot be undone.

## When something fails

| What you see | What to do |
|---|---|
| No plan or no task ids | Say that plan completion could not be checked, and judge from the commit range and the verify run. It cannot be plain READY. |
| A check is FAILED or BLOCKED | It is a blocker. Name the check and give its output. |
| A task says VERIFIED but has no evidence file | Treat it as not done. |
| There is no previous tag | Ask for the commit the release starts from. |
| The changelog and the commits disagree | The commits win. Fix the changelog. |

## References (read only when needed)

- `references/examples.md` — a good and a weak release verdict, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
