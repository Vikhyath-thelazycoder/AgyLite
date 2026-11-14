# Engineering: a good and a weak final answer

Both answers are for the same request: "Orders with a 100% discount code crash at checkout. Fix it."

## Weak

> I've fixed the checkout crash! The issue was a division by zero in the discount calculation. I updated
> `pricing.py` to handle this edge case and added some tests. The checkout should now work correctly for all
> discount codes. Let me know if you'd like me to make any other improvements!

Why it is weak:

- "should now work" is a guess. No check is named, so the reader cannot tell whether anything ran.
- "added some tests" does not say which tests or what they prove.
- No file list, no evidence file, no plan status. Nothing can be checked without redoing the work.
- It does not say what was left out, so the reader assumes nothing was.
- The opening and the closing offer add no information.

## Good

> **What changed.** Checkout no longer crashes when a discount brings the order total to zero: the tax step now
> returns zero tax for a zero total instead of dividing by it.
>
> **Files**
> - `shop/pricing.py` — `tax_rate_for()` returns `Decimal("0")` when the subtotal is zero (line 88).
> - `tests/test_pricing.py` — two new tests (below).
>
> **Tests**
> - `test_full_discount_gives_zero_tax` — a 100% code on a 40.00 order gives tax 0.00 and total 0.00. It failed
>   with `ZeroDivisionError` before the change and passes after.
> - `test_partial_discount_tax_unchanged` — a 50% code still gives the same tax as before (guards the fix against
>   changing normal orders).
>
> **Evidence.** `agylite verify --task T-4.2` → tests 212 passed, 0 failed; typecheck PASSED; lint PASSED; build
> PASSED. Evidence: `.agylite/evidence/20261114T101502.json`. Plan: T-4.2 is VERIFIED.
>
> **Not done.** A negative total is still possible when two codes stack; that was not part of this request. Added as
> T-4.3 ("Reject discount combinations above 100%").
>
> *(output of `agylite used`)*

Why it is good:

- The first sentence says what a user of the shop will see, not what the code looks like.
- Each test states what it proves, and the regression test was seen failing first.
- The evidence is a command with counts and a file, so anyone can check it.
- The related problem it found is not fixed silently and not dropped: it is a task with an id.
