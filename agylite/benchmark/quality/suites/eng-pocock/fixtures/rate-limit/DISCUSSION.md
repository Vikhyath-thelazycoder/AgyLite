# Discussion: rate limiting the invoice API (2026-10-16)

- Problem: one customer's script created 40,000 invoices in an hour and slowed the API for everyone.
- Decided: limit per API key, not per IP (customers sit behind shared NATs).
- Decided: 120 requests per minute per key, sliding window; `/health` is never limited.
- Decided: over the limit → HTTP 429 with a `Retry-After` header in whole seconds and a JSON error body
  `{"error": "rate_limited"}`.
- Decided: counts live in process memory for now (single instance); a shared store comes later if we scale out.
- Decided: limits are configurable per key later; for now one global default.
- Not now: per-endpoint limits, a dashboard, billing tiers, Redis.
- Testing: test through the HTTP interface with a fake clock; do not test the window data structure directly.
