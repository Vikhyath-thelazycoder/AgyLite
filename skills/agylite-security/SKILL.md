---
name: agylite-security
description: Security-sensitive changes (auth, secrets, payments and webhooks, input handling, OWASP), each fix proven by a negative test that fails without it — use when a change touches authentication, authorization, secrets, payments, webhooks or untrusted input, or when asked to fix or check a security defect.
disable-model-invocation: true
---

# Agylite Security

Produces a security change or a list of defects in which every item has a concrete attack, the line it works on,
and a negative test that proves the fix. It reports no theoretical risk without a scenario, and no real secret
ever appears in its output.

## Use when · Not for

- Use when: a change touches login, sessions, permissions, secrets, payments, webhooks, file uploads or any input
  that comes from outside; or a security defect is to be found or fixed.
- Not for: an ordinary code change → `agylite-engineering` · a general pre-merge review → `agylite-review` (it calls
  the security reviewer when the route says so) · a release decision → `agylite-production`.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>" --paths <files…>`; security work selects `engineering/security` and
  `testing/security`. Load them: `agylite context --request "<the user's request>" <id>…`.
- **Order.** Project security rules outrank every methodology. Read the recorded ones first:
  `agylite decide list --kind security`.

## Steps

1. **Map the surface.** `agylite codebase affected --paths <files…>`. Expect: the changed files and what reaches
   them. List every entry point (route, handler, job, webhook) and where untrusted input enters.
   Move on when: each entry point has a line saying who may call it and what input it trusts.
2. **Check each entry point** for: authentication and authorization on every path (not only the main one);
   signature, timestamp and replay protection on webhooks; secrets kept out of code, logs and error messages;
   injection (SQL, shell, template, path) and unsafe deserialisation; dependency advisories.
   Move on when: each item is marked safe (with the line that makes it safe) or is a finding.
3. **Write the negative test first.** For each finding, a test that performs the attack: a forged or expired
   signature is rejected, access without permission is denied, an injection input is neutralised, a secret is not
   in the log. Expect: the test fails without the fix. Move on when: it has been seen failing.
4. **Fix** at the shared place (the loader, the middleware, the validator), not at one caller.
5. **Verify.** `agylite verify` (tests, plus the dependency audit and secret scan where the project has them;
   policy: `config/verification.yaml`). Move on when: every selected check is PASSED.
6. **Record** a new security rule as a decision: `agylite decide add --kind security --topic … --decision …
   --reason …`.

Severity:

- **Critical** — reachable without an account, or exposes or changes other users' data or money.
- **High** — needs an ordinary account, or leaks a secret or a credential.
- **Medium** — needs unusual conditions or gives limited impact (one user's own data, a denial of one feature).
- **Low** — hardening: nothing is exploitable today.

## Output

```markdown
## Security: <the change> — <n> findings (<n> fixed, <n> open)

1. **<Critical | High | Medium | Low>** `path/file.py:42` — <the defect>
   - Attack: <who sends what> → <what they get>
   - Fix: <the change and where>
   - Negative test: `<test name>` — failed before the fix, passes after
   - Status: <fixed | open, and why>

Checked and safe: <entry point — the line that makes it safe>
Evidence: `agylite verify` → <counts per check> (<evidence file>)
Not checked: <what you could not inspect, and why>
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every finding has an attack a real caller can perform, with the request or input. "Could be vulnerable" is not
  a finding.
- Every fix has a negative test that was seen failing without it.
- You followed the input to where it is used; a finding does not rest on a function's name or on the diff alone.
- "Checked and safe" names the line that makes each entry point safe. An empty list means you did not check.
- No real secret, token, key or customer data in the answer, the tests, the logs or the evidence. Use made-up values.
- The fix is in the shared code path, so a second caller cannot skip it.
- Severity follows the definitions above, not how alarming the word sounds.

## Stop and ask

- You find a real secret in the code or the history: say where, not what, and ask before rotating or rewriting.
- The fix would lock out existing users, change a public interface or need a data migration.
- A defect is exploitable in production now: report it first, before the full review is finished.

## When something fails

| What you see | What to do |
|---|---|
| No dependency audit or secret scan in the project | Say that they did not run. Do not report them as passed. |
| The negative test passes without the fix | The test does not perform the attack, or the defect is not real. Find out which. |
| You cannot reach an entry point's code | List it under "Not checked" with the reason. |
| A recorded decision contradicts the fix | Name the decision; propose superseding it (`--supersedes`), do not ignore it. |
| A check is BLOCKED | Report it as BLOCKED with the missing tool. |

## References (read only when needed)

- `references/examples.md` — a good and a weak finding for the same webhook defect, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
