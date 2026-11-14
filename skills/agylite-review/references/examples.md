# Review: a good and a weak finding

Both are about the same defect: a new endpoint `GET /invoices/{id}` loads an invoice by id and returns it, without
checking that the invoice belongs to the caller's account.

## Weak

> **Security considerations.** The new endpoint might have some authorization issues. Consider adding proper access
> control checks to make sure users can only see their own data. It would also be good to add more tests around
> this.

Why it is weak:

- No `file:line`. The author has to find the problem again.
- "might have some issues" does not say what happens, to whom, or with which request.
- "Consider adding proper access control" is advice, not a fix. It does not say where the check goes.
- "more tests" names no test.
- It has no severity, so the author cannot tell whether it blocks the merge.

## Good

> ### Must fix
>
> 1. `api/invoices.py:57` — the invoice is loaded by id only; the caller's account is never compared.
>    - Goes wrong: a user of account A sends `GET /invoices/8841`, where 8841 belongs to account B → 200 with
>      account B's invoice, including the billing address and line items. Ids are sequential, so every invoice can
>      be read by counting up.
>    - Fix: load with `Invoice.get(id=invoice_id, account_id=request.account.id)` and return 404 when nothing is
>      found, as `api/orders.py:41` already does. 404, not 403, so the response does not confirm that the id exists.
>    - If skipped: any signed-in user can read every customer's invoices.
>
>    Missing test: `test_invoice_of_other_account_returns_404` in `tests/api/test_invoices.py` — create an invoice
>    for account B, request it as account A, assert 404 and that the body holds no invoice field.

Why it is good:

- The line is named, and the claim was checked against the code around it (there is no account filter in the
  loader or in a middleware; the reviewer read `api/orders.py` to see how the project does it elsewhere).
- The scenario is a real request with a real result. Anyone can reproduce it.
- The fix says what to write and why 404, using the pattern the project already has.
- The missing test is named with what it must assert.
- The severity follows from the scenario: data of other customers is exposed on an input that can really occur.
