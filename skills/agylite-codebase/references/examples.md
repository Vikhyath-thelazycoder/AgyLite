# Codebase: a good and a weak answer

Both answer the same question: "How does password reset work, and what would break if I changed the token length?"

## Weak

> The password reset feature is implemented in the auth module. When a user requests a reset, the system generates
> a secure token, stores it, and sends an email with a reset link. When the user clicks the link, the token is
> validated and the password is updated. Changing the token length should be safe, but you may want to check the
> related tests.

Why it is weak:

- No file and no line. It reads like a description of any password reset, and could have been written without
  opening the code.
- "should be safe" is a guess. It names nothing that depends on the length.
- "check the related tests" does not say which tests.
- It does not say what could not be determined.

## Good

> A reset token is 32 random bytes, hex-encoded to 64 characters, stored hashed, and valid for 30 minutes. Changing
> the length breaks one database column and one test.
>
> How it works
> 1. `auth/reset.py:22` — `request_reset()` calls `secrets.token_hex(32)` and stores its SHA-256 in
>    `PasswordReset.token_hash`.
> 2. `auth/reset.py:31` — the plain token goes into the email link through `mail/templates/reset.txt:4`.
> 3. `auth/reset.py:48` — `confirm_reset()` hashes the token from the link, looks it up, and rejects it when
>    `created_at` is older than `RESET_TTL` (`settings.py:61`, 30 minutes).
>
> Affected by the change: `auth/reset.py`, `auth/models.py`
> - `auth/models.py:15` — `token_hash` is `CharField(max_length=64)`. The hash is always 64 characters, so the
>   token length does not affect it.
> - `auth/urls.py:9` — the route pattern is `[0-9a-f]{64}`. A different token length will not match and every
>   reset link returns 404. **This is what breaks.**
>
> Tests that cover it: `tests/auth/test_reset.py` (5 tests); `test_reset_link_format` asserts 64 characters and
> will fail.
> Unknown: whether the mobile app parses the link (it is in another repository).
> Analysis: code graph

Why it is good:

- Each step cites the line where it happens, and the lines were read (the hash length and the URL pattern are
  details only the code gives).
- The question about the length gets a precise answer: the column is safe, the URL pattern is not.
- The failing test is named.
- What lies outside the analysed code is stated as unknown.
