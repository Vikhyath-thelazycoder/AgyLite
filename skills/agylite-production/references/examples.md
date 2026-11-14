# Production: a good and a weak release verdict

Both are for the same release: version 1.4.0 of a booking app, with three plan tasks and one database migration.

## Weak

> The release looks ready to go! All features are implemented and tests are passing. I've put together a changelog
> with the new features and various improvements. You can deploy whenever you're ready, and revert if anything goes
> wrong.

Why it is weak:

- "looks ready" is not a verdict with reasons. No task, no check and no evidence file is named.
- "tests are passing" does not say which run, on which commit.
- "various improvements" in a changelog tells users nothing and may hide a change.
- "revert if anything goes wrong" ignores the migration: reverting the code does not undo a schema change.

## Good

> ## Release 1.4.0 — NOT READY
>
> Blockers:
> 1. T-6.3 "Cancel a booking by email link" is READY_FOR_VERIFICATION, not VERIFIED: it has no evidence file.
>    Unblock: `agylite verify --task T-6.3`, or accept the risk.
> 2. `agylite verify --all`: lint FAILED (2 errors in `booking/cancel.py`, unused import and an undefined name on
>    line 48). Unblock: fix both.
>
> Accepted risks: None
>
> Plan: 2 of 3 claimed tasks done (T-6.1 VERIFIED, T-6.2 VERIFIED, T-6.3 READY_FOR_VERIFICATION)
> Evidence: `agylite verify --all` → tests 431 passed, 0 failed; typecheck PASSED; lint FAILED; build PASSED
> (`.agylite/evidence/20261114T140210.json`, commit `9f2c1ab`)
>
> Changelog
> - Guests can cancel a booking from the link in their confirmation email.
> - The booking list loads the next page as you scroll.
> - Fixed: bookings that end at midnight no longer show on the following day.
>
> Migration: `python manage.py migrate booking 0012` (adds the nullable column `cancel_token`).
> Rollback: deploy 1.3.2, then `python manage.py migrate booking 0011`. The column is dropped; cancel links sent
> by 1.4.0 stop working.
> Config and secrets: new `CANCEL_LINK_SECRET` (set before deploy).

Why it is good:

- The verdict follows from two named blockers, each with what would unblock it.
- The undefined name on line 48 is a real defect that "tests are passing" would have hidden.
- The verify run names its commit and evidence file.
- The rollback covers the migration and says what users lose.
