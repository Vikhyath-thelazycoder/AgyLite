# Testing: a good and a weak verification report

Both are for the same change: a new "remember me" checkbox on the login form that keeps the session for 30 days.

## Weak

> I ran the tests and everything passes. I also checked the login page and the checkbox looks good and works as
> expected. The change is verified.

Why it is weak:

- "everything passes" has no command, no counts and no evidence file.
- "looks good and works as expected" is a look at the page. Nothing was recorded, so nothing can be checked.
- It does not say whether a test for the 30-day session exists. Passing old tests say nothing about new behaviour.
- The browser check for UI work is not mentioned, so the reader cannot tell whether it ran.

## Good

> Verification: BLOCKED
>
> | Check | Result | Counts | Note |
> |---|---|---|---|
> | tests | PASSED | 148 passed, 0 failed | impacted tests: `tests/auth/` |
> | typecheck | PASSED | | |
> | lint | PASSED | | |
> | build | PASSED | | |
> | browser | BLOCKED | | browser runtime not installed |
>
> Evidence: `.agylite/evidence/20261114T113040.json`
>
> Tests added:
> - `test_remember_me_sets_30_day_expiry` — with the box ticked, the session cookie expires 30 days from login.
>   Failed before the change (expiry was the browser session).
> - `test_without_remember_me_expiry_unchanged` — without the box, the cookie is still a session cookie.
>
> Not covered: the checkbox in a real browser (label click, keyboard, 390 px width). The browser check needs
> `agylite runtime install browser` (a Chromium download). Shall I install it?
>
> *(output of `agylite used`)*

Why it is good:

- The overall result is BLOCKED, not PASSED, because one selected check did not run.
- Every row has a result from a command, and the evidence file is named.
- The new tests say what they prove, and the first one was seen failing.
- What is still unverified is stated, with the one step that would close it.
