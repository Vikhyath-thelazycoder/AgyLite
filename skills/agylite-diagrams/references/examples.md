# Diagrams: a good and a weak delivery

Both are for the same request: "Draw how a login request is handled in this codebase."

## Weak

> Here's the architecture diagram for the login flow! It shows the client, the load balancer, the API gateway, the
> auth service, the user database, a Redis cache for sessions and the JWT token service. I saved it as
> `login.html`. It gives a clear overview of how authentication works.

Why it is weak:

- The parts read like a textbook login system. Does this codebase have a load balancer, a gateway and Redis? No
  file is cited, so nobody can tell which nodes are real.
- It is an "architecture overview", but the question was about the path of one request. The type was not chosen
  for the question.
- No finalize result and no browser-check: the file may not even render.
- Nothing is listed as left out or unconfirmed, so the reader takes every box as fact.

## Good

> Diagram: `docs/diagrams/login-sequence.html` (sequence)
> Answers: what happens, in order, between the login form submit and the session cookie?
> Shows: 5 nodes, 8 edges; each node cites its files
> - Browser → `LoginView.post` (`accounts/views.py:34`)
> - `LoginView.post` → `RateLimiter.check` (`accounts/throttle.py:12`), 5 attempts per 15 minutes per IP
> - `LoginView.post` → `authenticate` (`accounts/backends.py:20`), which reads `User` by email and checks the
>   password hash
> - `LoginView.post` → `SessionStore.create` (`accounts/sessions.py:41`), a row in the `sessions` table
> - response with `Set-Cookie: sid` (`accounts/views.py:58`)
>
> Left out on purpose: the password-reset branch and the admin login (other questions; each would be its own
> diagram).
> Checks: finalize exit 0 (validate, strict check, browser-check passed)
> Not confirmed: whether a proxy in front of the app also limits requests. Nothing in this repository configures
> one, so it is not drawn.
>
> *(output of `agylite used`)*

Why it is good:

- A sequence diagram, because the question is about order.
- Every node is a name from the code with its file and line. There is no Redis and no gateway, because the code
  has none: sessions are a database table.
- The finalize result is stated.
- What was left out and what could not be confirmed are both named.
