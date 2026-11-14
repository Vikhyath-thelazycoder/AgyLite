# Security: a good and a weak finding

Both are about the same defect: a payment webhook handler checks the signature header, but compares it with `==`
and never checks the timestamp.

## Weak

> The webhook handler has potential security vulnerabilities. Signature verification should follow best practices,
> and replay attacks should be considered. I recommend hardening the endpoint and adding security tests.

Why it is weak:

- No line, no attack, no severity. The author learns nothing they can act on.
- "should follow best practices" does not say which practice is broken.
- "replay attacks should be considered" does not say whether one works here.
- "adding security tests" names no test.

## Good

> 1. **High** `payments/webhook.py:31` — the timestamp in the signed payload is never checked, so a captured
>    request stays valid for ever.
>    - Attack: someone who has seen one real `payment.succeeded` request (a proxy log, a leaked debug dump) sends
>      the same body and header again → the handler accepts it and credits the order a second time.
>    - Fix: reject when `abs(now - payload.timestamp) > 300` seconds, in `verify_signature()` so that every
>      handler gets it; store the event id and ignore one that was already processed.
>    - Negative test: `test_replayed_webhook_is_rejected` — sends a validly signed request with a timestamp ten
>      minutes old and expects 400 and no order change. Failed before the fix (200, order credited), passes after.
>    - Status: fixed
>
> 2. **Medium** `payments/webhook.py:27` — the signature is compared with `==`, which stops at the first
>    different byte.
>    - Attack: an attacker who can send many requests and measure response time can recover the expected
>      signature byte by byte. It needs many thousands of requests and a stable network path.
>    - Fix: `hmac.compare_digest(expected, received)`.
>    - Negative test: `test_signature_uses_constant_time_compare` — asserts that `verify_signature` calls
>      `hmac.compare_digest` (timing itself cannot be tested reliably). Failed before, passes after.
>    - Status: fixed
>
> Checked and safe: the signing secret comes from the environment (`settings.py:14`) and is not logged
> (`payments/webhook.py:40` logs the event id only).
> Not checked: the payment provider's dashboard settings (no access).

Why it is good:

- Each finding is one defect with its own line, attack, fix and test.
- The severities differ, and each follows from what the attacker needs and gets.
- The second test says honestly what it can and cannot prove.
- It lists what was checked and found safe, and what could not be checked.
