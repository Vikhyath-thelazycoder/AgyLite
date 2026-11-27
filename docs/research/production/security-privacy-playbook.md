<!-- Source A for the Production profiles step (docs/plan/IMPLEMENTATION_PLAN.md). Written by the owner, given to
the agent on 2026-11-27 and stored here unchanged. Gaps against other sources and the web: production-readiness-gaps.md. -->

# Production Playbook: Security, Privacy, Cost, Reliability and Launch

A reusable rulebook for web apps and mobile apps, written so an AI coding agent (or a person) can drop it into any project and know what to build, check and ask. It was distilled on 26 November 2026, and extended on 27 November 2026 (sessions, IDOR, bots, subscriptions, refunds and a quick checklist for quickly built apps), from a production plan for an Indian SaaS (Next.js on Cloudflare Workers, Supabase, Cashfree, Gemini, a render server), plus launch checklists collected along the way. Stack names appear only as examples; the rules are stack-neutral.

> **Not legal advice.** Laws and provider limits change. Before launch, check the current text and commencement dates of every law named here, and have the client's lawyer and accountant confirm anything marked *confirm*.

---

## 0. How an AI agent should use this file

1. **Read the whole file first.** Then read the project's own docs (plan, PRD, security notes, data model) and its code.
2. **Make a gap register.** For every rule below, record one row: `ID | Requirement | Status | Where (task or file) | Phase | Release blocker`. Status is one of: *Implemented and verified*, *Implemented but unverified*, *Partially implemented*, *Documented but not implemented*, *Missing*, *Not applicable (reason, recheck trigger)*. Template in section 9.
3. **Put each row into a phase** (section 1) and build it inside that phase's tasks. A phase gate does not pass while its blocker rows are open, unless accepted in writing (section 3.14).
4. **Never mark a row done without the code and the test that prove it.**
5. **Ask before deciding** anything marked *decision* (for example GDPR scope, refund rule, minimum age, session lengths). Log every decision with the date and who made it.
6. **Do not weaken a rule silently.** If a rule does not fit the stack, write why, and what would make it apply again.
7. **Testing tools run only against your own staging**, with a written scope, never against production traffic or anyone else's site.
8. **Update every project document,** not only the code: the plan or task list, the security notes, the gap register, the decisions log and the test plan. A rule that lives only in this playbook is not built.

**Starting prompt for a new project.** Give the agent this file and say: *"Read this playbook and the whole project. Make a gap register against every section, including the quick checklist in 3.15, the pentest coverage in 3.16 and the production A to Z in section 11. Ask me the questions in section 8 that the project has not answered. Then add every missing rule to the plan, in the right phase, with a test for each, and build the ones due in the current phase."*

---

## 1. When each rule is built (phase map)

| Phase | Build or check |
| --- | --- |
| Design and frontend (sample data only) | No real customer data anywhere; private recordings and secrets ignored by git; no SVG uploads; sign-up shows the 18+ box and a separate, unticked marketing box; delete-account, cancel and cookie screens exist; admin screens for the outside-services list, retention and spending caps |
| Prep (before money is spent) | Trademark search before buying the domain; licence audit (fonts, music, stock media, code); data processing agreements with every provider; GDPR scope decision; provider accounts owned by the client |
| Foundations | CI with secret scan, static analysis, dependency and image scans, licence check, web scanner baseline; security headers; health check; request IDs; logs with redaction; backups; spending caps recorded per provider; CORS allow-list |
| Accounts, data, billing | Auth and session rules; RLS and access tests; consent records; record of processing; payment webhooks; subscriptions and cancellation; rate limits on a shared store; abuse and free-plan farming controls |
| Core features | Upload safety; signed links; SSRF-safe fetcher; AI budget reserve before paid calls; content filter; prompt-injection rules; retry budgets; job queue with dead letters |
| Integrations (OAuth, posting) | OAuth state and PKCE, smallest scope, token encryption, platform policies (Google Limited Use, YouTube, made-for-kids) |
| Admin | Staff list by user ID, MFA, fresh MFA for dangerous actions, audit log that cannot be edited, bulk-export caps, safe CMS publishing |
| Hardening | Full security review; the 20-attack checklist again; authenticated web scan and staging scans; attack-bot tests; restore drill that keeps deleted accounts deleted; privacy law check; status page, security contact, support hours |
| Load test and launch | Measure-first load tests; user bots on staging; go or no-go review with every blocker closed or accepted |
| After launch | Monitoring, incident drills, monthly review of spend, consent, retention jobs and scan results |
| Mobile app (later) | MobSF scans, secure storage, deep-link checks, store privacy forms, in-app account deletion |

---

## 2. Principles

- **Two locks on data:** the API checks identity, ownership, plan and role on every request, and the database enforces row-level security as the second lock.
- **The server decides everything that costs money or grants access.** Never trust user IDs, plan, role, balance or price from the browser.
- **Fail closed** for payments, posting and paid AI calls when a switch, check or provider is unavailable.
- **Collect less.** What you never store, you cannot leak.
- **A spending alert is not a spending limit.** Every paid resource needs a hard stop you control.
- **Measure before you scale.** Find the bottleneck first.
- **Same words everywhere.** Billing, refund and privacy wording lives in one place and is reused on every page.
- **No customer disruption** from releases: no forced logouts, versioned job payloads, migrations that work with old and new code.

---

## 3. Security rules

### 3.1 Authentication and sessions

| Rule | Detail |
| --- | --- |
| One auth provider | Use one managed auth service (example: Supabase Auth) with verified email and password plus Google. Add providers only after reviewing them against the nOAuth row (3.10 #4) |
| Short access tokens (*decision*) | Access token 5 to 60 minutes (shorter is safer, longer means fewer renewal calls; the source project chose 15 minutes); refresh tokens rotate on every use with reuse detection (allow the provider's documented grace cases: a reuse inside the reuse interval or of the active token's parent returns the current token; any other reuse ends the session) |
| Verify every token on the server | Signature with asymmetric keys, a fixed algorithm list, `iss`, `aud`, `exp`, `nbf`, `kid` from a cached JWKS, small clock skew (about 30 s). Never decode without verifying |
| Revocation that works (*decision*) | A JWT stays valid until it expires. Decide and write down which APIs also check that the session still exists on every call. At least: payments, plan changes, account and security settings, OAuth connect and disconnect, data export, account deletion and every staff API. Either check it on every API too, or accept in writing that a token copied before sign-out keeps working on ordinary reads until it expires, and keep the token short enough for that to be acceptable |
| Session lengths (*decision*) | Separate from token expiry. Examples: customers 30 days idle with no total limit (source project) or 7 days idle and 30 days total; staff 30 minutes idle or 8 hours total |
| Idle means the person did something | Record `last_active_at` per session from requests the person started, at most once a minute (staff) or an hour (customers). Token refreshes and timer requests such as polling (mark them, for example `X-Background: 1`) never count, so a tab left open does not stay signed in forever. A scheduled job ends idle sessions |
| Staff limits enforced by the app | Auth providers usually set session timeouts for the whole project, so when customers and staff need different lengths, check staff idle and total time in the app on every staff call and end the session when either is passed |
| Back button and shared computers | Signed-in pages send `Cache-Control: private, no-store`, so after sign-out the back button and browser history show nothing; sign-out clears cookies and local storage and ends the session on the server |
| Session fixation | A new session ID after sign-in and after any privilege change |
| Session lifecycle | Sessions list; sign out this device or everywhere; end other sessions after a password or email change; new-device email; same response whether an email exists; relative return addresses only (no open redirect) |
| Cookies | `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict` for staff) |
| Staff | MFA on every staff account and every provider console; each MFA code works once, 5 tries then lock; fresh MFA for dangerous actions; staff role stored against the user ID after a verified sign-in, never matched on an email claim; no shared role passwords |
| Signing keys | Rotated with overlap; an emergency runbook revokes a leaked key |
| Auth emails | Sent through your own sender with SPF, DKIM and DMARC; never the provider's test sender in production |
| Emails and handles | Trim, NFKC-normalise and lowercase before compare or store; also compare by Unicode confusable skeleton (UTS #39) so lookalikes cannot collide with existing or staff accounts |
| Passwords | Leave hashing to the auth provider; never hash a username and password joined together (bcrypt ignores bytes after 72) |

### 3.2 Authorization

- API checks identity, ownership, plan and role on each request; the database's row-level security repeats ownership.
- Every view uses `security_invoker = true` (Postgres); `security definer` functions live in a schema the public API cannot reach.
- Turn off database features that bypass your API, such as an auto-generated public GraphQL endpoint, unless you use and protect them.
- Fields set by the server (`user_id`, plan, role, status, balance, price) are never read from the request body.
- Random, unguessable IDs; ownership checks; the same error for "not found" and "not yours".
- Staff roles are least privilege; support staff see account context without tokens, secrets or card data; workers use scoped service credentials.
- **Cross-account test matrix:** user A tries to read, change and delete user B's every object through the API, direct database calls, signed links and background jobs.
- **Logged-out public-key test:** sign out, take the public (anon) database key from the browser, and try to read and write every table, view and function. It must get nothing.

### 3.2a IDOR and tampering in the browser

An attacker signs in as themselves, then changes what the browser sends. Every one of these must fail with the same not-found reply and be logged:

| Tampering | Test |
| --- | --- |
| Change an ID in the address (`/video/123` to `/video/124`), the query string or the request body | Every object type, for read, change and delete |
| Copy another user's link, signed link, job ID, export link or invoice link | Works only for its owner; signed links expire (about 15 minutes) |
| Send another user's session ID, cookie or token from browser history, a shared computer or a log | Refused after sign-out (subject to the revocation decision in 3.1); never written to logs or addresses |
| Add `user_id`, `role`, `plan`, `price`, `status` or `balance` to a body (mass assignment) | Ignored; the server sets them |
| Guess IDs | IDs are random (UUID); no counting IDs in addresses |
| Path tricks in file names or keys (`../`, encoded slashes) | Storage keys are built on the server from IDs |
| Call the database directly with the public key | Gets nothing (3.2 public-key test) |
| Poll or subscribe to another user's job or channel | Refused |
| Staff role from a hidden field, local storage or a claim | Role read from the staff table on every call |

Run the matrix for two normal users, a staff user without the role, and a signed-out visitor. Add a row each time a new object type appears.

### 3.3 Secrets

- Secrets live in the platform's secret store, never in code, chat, logs, screenshots or browser bundles. Local development uses an ignored env file with test keys.
- Separate keys per environment; the database service key is server only.
- All provider accounts belong to the client; rotate every key at handover and after any suspected exposure.
- Secret scanning runs on every commit and the full history (tool: Gitleaks).
- No key ever reaches the frontend. If a feature needs a paid API, call it from the server behind limits and a spending cap.

### 3.4 API baseline

| Rule | Detail |
| --- | --- |
| Auth by default | Every API route needs a verified session unless it is on one reviewed public list (health, signed webhooks, public content, sign-in); a test walks every route signed out and expects `401`, and CI fails on a route in neither list. Never rely on hiding a button or page |
| Queries | Only the database client's query builder or SQL with bound parameters (`$1`); never join user input into SQL, filter strings (for example PostgREST `.or()` or `.filter()`) or `EXECUTE`; dynamic SQL in functions uses `format('%I', '%L')` |
| Input | Schemas, length caps, allowed characters where it matters; escape on output; allow-list cleaning for rich text |
| Schemas | Every route validates its body with a fixed schema that refuses unknown keys (and `__proto__`, `constructor`, `prototype`); request JSON is never deep-merged into objects |
| Size limits | A body size limit per route (for example 64 KB JSON unless the route needs more) |
| Methods | No change over GET; Origin check on every change request; CSRF token where cookies authenticate |
| CORS | Answer browsers only from your own listed addresses, never `*`; credentials only for those; webhooks and health checks accept no browser calls |
| Idempotency | Paid or state-changing POSTs require an `Idempotency-Key`; the client sends one per user intent; buttons disable while a request runs |
| Errors | Stable shape: `code`, `message`, `requestId`, optional `retryAfter`; no stack traces or provider details to clients |
| Lists | Cursor pagination with a maximum page size |
| Request IDs | Every response carries a request ID that follows the request into worker logs |
| Search | Wait for typing to stop (about 300 ms) and cancel the previous request |
| Health check | Returns status, version and a quick database check, no secrets or user data, rate-limited, never cached |
| No debug in production | `NODE_ENV=production`; no public source maps; error pages and API errors show a plain message and request ID, never a stack trace, SQL or provider message; debug flags, verbose logs and test switches off; live keys only in production and test keys never there; dev-only pages removed or behind the staff role |

### 3.5 Web protections

| Threat | Protection |
| --- | --- |
| Missing browser protections | On every response: strict `Content-Security-Policy` with `frame-ancestors 'none'` (hashes on cached pages, nonces on dynamic ones), `Strict-Transport-Security` with `includeSubDomains` once the domain is final, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, a `Permissions-Policy` that turns off camera, microphone and location until needed |
| HTTPS | Every `http://` request gets a 301 to `https://`; HSTS; `Secure` cookies; TLS 1.2 or later; no mixed content |
| Storage buckets | Private by default: public access and default public addresses (for example R2's `r2.dev`) off; only a site-media bucket is public, on its own domain; customer files only through owner-checked signed links; bucket CORS lists only your own addresses |
| Public forms | Every public form (sign-up, sign-in after failures, password reset, contact, waitlist, newsletter, free tools) has a CAPTCHA verified on the server (token used once, hostname and action checked), a hidden honeypot field and per-address and per-email limits, before any email is sent or row written |
| XSS | Framework escaping, strict CSP, sanitised rich text, structured content with raw HTML off |
| CSRF | SameSite cookies, Origin checks, tokens |
| SSRF (any feature that fetches a URL) | `http` and `https` only, DNS and redirect checks, private, loopback and cloud-metadata addresses blocked, size and time limits |
| Uploads | Allow-list types checked by file content, not name; no SVG or HTML; size, pixel and length limits; strip EXIF and GPS; signed upload into a holding area; re-encode on an isolated worker; serve from a separate domain with fixed content type, `nosniff` and download headers; customer files in a private bucket |
| File links | Short-lived (about 15 minutes) signed links issued only after an ownership check; storage keys built on the server from IDs, never from client paths |
| Webhooks | Verify the signature (HMAC over timestamp and raw body) in constant time; refuse old timestamps; store event IDs uniquely so replays do nothing; reconcile against the provider's API |
| Cache | Cache only finished public HTML, keyed on the headers that change it; signed-in pages and drafts are `private, no-store`; preview routes skip the cache and send `noindex` |
| Enumeration | Random IDs, consistent errors, rate limits |
| Dependencies | Lockfiles, automated alerts, reviewed upgrades, scans in CI |

### 3.6 Rate limits and abuse

- Enforce limits on the server in a shared store (for example one Durable Object or Redis key per counter), never per process and never only by disabling a button.
- Count the client address only from the header your edge sets (Cloudflare: `cf-connecting-ip`), never from `X-Forwarded-For`. Count per account and per email too.
- Starting limits to tune with load tests (admins can change them without a release):

| Endpoint | Starting limit |
| --- | --- |
| Sign-in and sign-up | 5 tries per 15 minutes per email, 20 per hour per address; a CAPTCHA (example: Turnstile) after 3 failures |
| Password reset and email codes | 3 per hour per email |
| Expensive generation | per minute and per day per account, plus plan limits |
| URL fetch features | 5 per minute per account |
| Background jobs | plan allowance plus a cap on active jobs per account |
| Other API calls | about 120 per minute per account, 300 per minute per address |
| Downloads | per account and per address per hour |
| Webhooks | signature check first, never a limit that could drop real payment events |

- A blocked request gets `429` with `Retry-After` and a plain message, and costs the user nothing.
- **Bot and fake accounts:** CAPTCHA on sign-up; email verified (or Google sign-in) before anything of value; known throwaway email domains refused for free value; sign-up velocity limits per address range and device; plus-addressing and dots normalised when checking repeats (`a.b+x@gmail.com` is `ab@gmail.com`); new accounts that share a device, address range or payment instrument flagged for review; banned accounts cannot sign up again with the same email, Google account or card; staff can suspend an account, which the API, database and workers all honour.
- **Credential stuffing and guessing:** limits per email and per address; CAPTCHA after a few failures; same reply and timing whether an email exists; turn on the auth provider's leaked-password check where offered; alert on spikes of failures.
- **Scraping:** limits per account and per address on lists and search; cursor pages with a maximum size; no bulk export without staff approval and caps.
- **Free-plan farming:** free credits only after verified sign-in; known throwaway email domains get none; limits per device and address range; repeat sign-ups flagged; free output watermarked; one trial per person checked against verified email, OAuth account, phone and payment instrument.
- **DDoS:** every public address behind an edge with always-on DDoS protection; origins never exposed; workers that only pull jobs accept no inbound traffic; an "under attack" runbook rehearsed on staging.
- **Good bots and bad bots:** let real users, search engines and chosen AI answer bots reach public pages; challenge or block the rest.

### 3.7 AI features

| Rule | Detail |
| --- | --- |
| Reserve before you spend | The server checks and reserves the user's allowance before any paid AI call; the model never decides billing, plans or limits |
| Hard AI spending cap | Count the cost of every call; at the daily or monthly cap set in admin, paid calls stop by themselves (kill switch), staff get an alert and jobs wait. Provider budgets usually only email, so they are a backup, not the stop |
| Content filter | On prompts and input text before generation and on output after; refused requests are logged and cost nothing; test it in every launch language and mixed scripts (for example Hinglish), because filters are weaker outside English |
| Prompt injection | Mark every outside text as untrusted; fixed output schema; no tools or secrets exposed to the model; validate output |
| System prompt | Holds no secrets, prices or staff details; a test tries to extract it |
| Hallucination | Features that summarise a source use only facts in that source and reject numbers, prices, phone numbers or addresses not found in it; idea-based scripts do not state statistics, quotes or named people as fact; the user sees the text before it is used; sensitive subjects (health, money, legal, news) carry a check-facts warning and never post automatically; a fixed test set scores invented claims on every prompt or model change |
| Free AI tools | Run in the browser with fixed patterns at launch, or sit behind CAPTCHA, per-address limits, a daily spend cap and the content filter |
| Faces and voices (if ever) | Recorded consent from the person, likeness check, no public figures, private storage, deletion on request |

### 3.8 Admin panel and CMS

| Risk | Protection |
| --- | --- |
| Admin takeover | MFA on every admin API, fresh MFA for dangerous actions, session limits, owner-only staff changes |
| Scripts in edited content | Structured content, allow-list cleaning, safe link schemes, media by ID only |
| Drafts leaking through the cache | Uncached preview route; HTML-only caching keyed on the right headers |
| A switch failing open | One real switch list; payments, posting and paid AI fail closed; workers check switches on each job |
| Private settings served publicly | Public allow-list for settings; keys are never shown or edited in the admin panel |
| Phishing through email templates | Logic-less escaped templates, own-domain links, fresh MFA to change them |
| Bulk data theft by a staff account | Daily export caps and alerts |
| Audit log tampering | No update or delete for any role, hash chain, daily locked copy |
| Bad publish surviving a restore | Purge and version bump on restore, short browser cache |

### 3.9 Workers, servers and infrastructure

- Servers: SSH keys only, root login off, no inbound ports (reach them through a tunnel), automatic security updates.
- Containers: pinned base image, non-root user, read-only root filesystem, per-job disk, CPU and memory limits, dropped capabilities, outbound traffic only to approved hosts; media tools (for example FFmpeg) limited to safe protocols with strict argument arrays; no payment, OAuth or email secrets on workers.
- Queues: leases, retries with backoff, dead-letter state, poison-job quarantine, a depth limit; only the current attempt may publish or settle a job.
- Changes go through pull request, review and CI; infrastructure kept as code (platform config, database migrations, DNS, WAF and cache rules).
- Backups: agree recovery time and acceptable data loss; point-in-time recovery where needed; media in immutable keys with a separately recoverable copy; restore drills in isolation that reapply deletion records before logins or jobs start.

### 3.10 The 20-attack checklist

Check each against the stack; mark *applies*, *handled* or *not applicable (recheck trigger)*, and test the ones that apply before launch.

| # | Attack | Protection |
| --- | --- | --- |
| 1 | HTTP/2 Rapid Reset | Serve only through an edge that absorbs it; never expose an origin |
| 2 | 52-character username (bcrypt 72-byte cut-off) | Never hash username and password joined; let the auth provider hash passwords |
| 3 | SAML bypass | No SAML unless needed; if added, use a maintained library and test signature wrapping |
| 4 | nOAuth email spoofing | Link identities only when the provider says the email is verified; staff by user ID, not email claim |
| 5 | GraphQL aliases (batched brute force) | Turn off unused GraphQL endpoints; if used, cost limits and per-operation rate limits |
| 6 | 2FA code replay | Each code works once; 5 tries then lock |
| 7 | ReDoS | No regex built from user input; cap input length before any regex; linear-time patterns |
| 8 | JWT algorithm confusion | Fixed algorithm list, asymmetric keys, always verify |
| 9 | Request smuggling | No chain of your own proxies in front of the app |
| 10 | Cache poisoning | Cache only public HTML keyed on the right headers; private pages `no-store` |
| 11 | Spoofed IP header | Client address only from the edge's own header; limits also per account and email |
| 12 | Views bypassing RLS | `security_invoker` views; RLS tests cover views and functions |
| 13 | `Math.random` tokens | `crypto.getRandomValues` or `crypto.randomUUID` for every token, ID and code; lint rule refuses `Math.random` outside visual effects |
| 14 | Timing attack | Constant-time comparison for every secret, signature and key hash |
| 15 | Padding oracle | Authenticated encryption only (AES-256-GCM), never CBC |
| 16 | Prototype pollution | Schemas drop unknown keys and refuse `__proto__`; no deep merge of request JSON |
| 17 | Template injection | Logic-less templates that escape everything; raw HTML off |
| 18 | XXE | Parse no XML, or turn off external entities and DTDs |
| 19 | WebSocket hijack | No sockets unless needed; if used, check Origin and the session on connect |
| 20 | Unicode lookalikes | NFKC plus confusable-skeleton comparison; staff emails plain ASCII |

### 3.11 Logging, monitoring and incidents

- Logs never hold tokens, cookies, keys or full personal content; a redaction test proves it.
- Alerts on repeated sign-in failures, token decrypt errors, unusual provider spend, permission denials, admin changes and balance mismatches.
- Emergency steps: pause the feature or provider with a switch, rotate exposed keys, end only affected sessions, preserve logs, fix and release, tell affected users and authorities as the law requires (section 4).
- Publish `/.well-known/security.txt` with a security contact; a status page for the main services; published support hours.
- **India:** CERT-In's directions of 28 April 2022 ask service providers and companies to report listed cyber incidents to CERT-In within 6 hours of noticing them, keep system logs for 180 days within India, and sync clocks to an Indian time source (*confirm* applicability and current text).

### 3.12 Testing and tools

**Test layers:** types, lint, unit, integration, end-to-end, RLS and cross-account tests, the public-key test, webhook replay, worker crash, SSRF, session expiry and revocation, OAuth `invalid_grant`, upload idempotency, JWT key-rotation drill.

**Free, open-source tools** (run beside your own security review, never instead of it):

| Tool | Repository | Use | When |
| --- | --- | --- | --- |
| Gitleaks | github.com/gitleaks/gitleaks | Keys and passwords in commits and history | CI, every commit |
| Semgrep CE | github.com/semgrep/semgrep | Static analysis for injection, missing checks, weak crypto | CI |
| Trivy | github.com/aquasecurity/trivy | Container image and dependency vulnerabilities, plus licences | CI |
| OWASP ZAP | github.com/zaproxy/zaproxy | Web app scanner: baseline (passive) in CI on staging; authenticated full (active) scan before launch | CI and pre-launch |
| Nuclei | github.com/projectdiscovery/nuclei | Templates for known holes and misconfigurations | Staging, pre-launch |
| Schemathesis | github.com/schemathesis/schemathesis | Unexpected inputs to every API route from the API description | Staging, pre-launch |
| MobSF | github.com/MobSF/Mobile-Security-Framework-MobSF | Static and dynamic scans of Android and iOS builds | Every app build before a store release |
| SafeLine WAF | github.com/chaitin/SafeLine | Self-hosted WAF reverse proxy | Only if you run a public origin without an edge WAF; skip it behind Cloudflare or a similar edge |

**Bot tests on your own staging:** fake sign-up bots, login guessing with test password lists, free-plan spam, scraping, mass uploads, replayed payment webhooks, a fixed list of jailbreak and prompt-injection prompts; user bots that walk every journey at human pace (sign up, make, pay, cancel, raise a ticket).

High and critical findings block merge or release.

### 3.13 Release security checks

- Secret, dependency, static and container scans pass.
- RLS and cross-account suites pass for every table, view and function; the public-key test reads and writes nothing.
- Every *applies* row of the 20-attack checklist has a passing test.
- The web scanner baseline is clean on staging; the authenticated full scan passes before launch.
- A dedicated security review for security-sensitive changes; a full review before launch and before each later phase.

### 3.14 Risk acceptance

A high or critical finding left open needs written acceptance from the owner and the client: the reason, a compensating control, an owner and an expiry date.

### 3.15 Quick checklist for quickly built apps

A short list to run against any app, especially one built fast or with AI help. Each line points to the full rule.

| Check | Rule |
| --- | --- |
| Row-level security on every table, view and function | 3.2 |
| Every API route checks auth (deny by default) | 3.4 |
| Never trust the frontend: price, plan, role, balance and ownership decided on the server | 2, 3.2 |
| Rate limits on a shared store, real client address | 3.6 |
| Input validated with schemas; output escaped | 3.4, 3.5 |
| Parameterized queries only | 3.4 |
| CORS locked to your own addresses | 3.4 |
| HTTPS forced, HSTS on | 3.5 |
| No IDOR: the tampering matrix passes | 3.2a |
| Debug mode off in production | 3.4 |
| CAPTCHA on every public form | 3.5 |
| Admin actions logged in a log nobody can change | 3.8 |
| Storage buckets private | 3.5 |
| Admin pages hidden (look missing without a staff session) and checked on the server | 3.1, 3.8 |
| Vulnerable packages updated; scans in CI | 3.5, 3.12 |
| Upload types checked by content | 3.5 |
| Security headers on every response | 3.5 |
| Webhook signatures verified | 3.5, 6.2 |
| JWT verified, sessions expire, revocation decided | 3.1 |
| Bot and fake accounts limited | 3.6 |
| Subscriptions move only on verified events; refund rule written once | 6.2 |

### 3.16 Penetration test coverage

Map every item to a rule and a test. A real pentest can still find logic flaws unique to the app, so this list replaces nothing; it makes sure the known classes are covered before the pentester arrives.

**OWASP Top 10 (2025)**

| Risk | Covered by |
| --- | --- |
| A01 Broken access control | 3.2, 3.2a, 3.8 |
| A02 Security misconfiguration | 3.4 (no debug), 3.5 (headers, buckets, HTTPS), 3.9 |
| A03 Software supply chain failures | 3.3, 3.12, and the supply chain rows below |
| A04 Cryptographic failures | HTTPS (3.5), AES-256-GCM for stored tokens, provider encryption at rest, `crypto` randomness (3.10 #13, #15) |
| A05 Injection | Parameterized queries (3.4), XSS (3.5), template injection (3.10 #17), command injection (argument arrays, 3.9) |
| A06 Insecure design | Threat model per feature before it is built; abuse cases in the gap register; fail closed (2) |
| A07 Authentication failures | 3.1, 3.6 |
| A08 Software or data integrity failures | Signed webhooks, CI checks, no deserialising untrusted data, signed or pinned dependencies |
| A09 Logging and alerting failures | 3.11 |
| A10 Mishandling of exceptional conditions | Fail closed (2); stable errors with no internals (3.4); retries with budgets (5) |

**OWASP API Security Top 10 (2023)**

| Risk | Covered by |
| --- | --- |
| API1 Broken object level authorization | 3.2a |
| API2 Broken authentication | 3.1 |
| API3 Broken object property level authorization | Mass assignment refused (3.2a); responses return only the fields each screen needs, never whole rows |
| API4 Unrestricted resource consumption | 3.6, 5 |
| API5 Broken function level authorization | Staff APIs check the role on every call (3.1, 3.8) |
| API6 Unrestricted access to sensitive business flows | Bots, trials, coupons and sign-ups limited (3.6, 6.2) |
| API7 Server-side request forgery | 3.5 |
| API8 Security misconfiguration | 3.4, 3.5 |
| API9 Improper inventory management | One list of every route and host; old API versions and preview hosts removed or `noindex` and locked; staging holds no production data |
| API10 Unsafe consumption of APIs | Responses from payment, AI, stock media and social APIs are validated with schemas and treated as untrusted |

**OWASP Top 10 for LLM applications (2025)**

| Risk | Covered by |
| --- | --- |
| LLM01 Prompt injection | 3.7 |
| LLM02 Sensitive information disclosure | No secrets or other users' data in prompts; output filtered |
| LLM03 Supply chain | Models and SDKs from official providers only, pinned versions |
| LLM04 Data and model poisoning | Outside text untrusted; no training on customer data without consent |
| LLM05 Improper output handling | Fixed output schema, validated, escaped before display |
| LLM06 Excessive agency | No tools, payments or publishing power for the model |
| LLM07 System prompt leakage | 3.7 system prompt row |
| LLM08 Vector and embedding weaknesses | If retrieval is added: per-user index filters, no cross-tenant results |
| LLM09 Misinformation | 3.7 hallucination row |
| LLM10 Unbounded consumption | Size limits, per-account limits, hard spend cap (3.7) |

**Common pentest findings not named elsewhere**

| Finding | Protection |
| --- | --- |
| Host header injection (poisoned reset links) | Build every link from a fixed site address setting, never the `Host` or `X-Forwarded-Host` header |
| Password reset flaws | Reset links single use, expire in about 1 hour, die when the password changes; same reply whether the email exists |
| Email change takeover | Confirm from both the old and the new address; notify the old address |
| Race conditions (double spend) | Allowance, coupons, trials, refunds and plan changes in one transaction or row lock; test with 20 parallel requests |
| Business logic abuse | Server checks quantities, prices, discounts and order of steps; no negative, zero or huge values; no stacked coupons |
| CSV formula injection | Export cells starting with `=`, `+`, `-`, `@`, tab or carriage return are escaped |
| Log injection | Structured JSON logs; user text cannot add lines |
| Email header injection | No line breaks in names or subjects that reach email headers |
| Clickjacking | `frame-ancestors 'none'` (3.5) |
| Reverse tabnabbing | Outside links use `rel="noopener noreferrer"` |
| Web cache deception (`/account/x.css`) | Private routes are `no-store` whatever the extension (3.5 cache row) |
| Exposed files | `.git`, `.env`, backups, source maps and config files never served |
| Subdomain takeover | No DNS record left pointing at a removed service; CAA records; DNSSEC |
| Supply chain | Lockfile installs (`npm ci`); CI actions pinned to commit SHAs with a read-only token; protected main branch; automated update pull requests (Dependabot or Renovate); new packages checked for age, maintainers and lookalike names (typosquatting, dependency confusion); third-party scripts only from hosts allowed by the CSP |
| Default or shared credentials | None anywhere; every staff account personal with MFA |
| Insecure deserialisation | Never deserialise untrusted data into objects or code; JSON only, schema-checked |
| HTTP parameter pollution | Schemas reject repeated parameters where one is expected |

---

## 4. Privacy and the law

### 4.1 India: Digital Personal Data Protection Act 2023 and DPDP Rules

*Confirm the current Rules and which obligations are in force on your launch date; the Rules phase obligations in over time.*

| Duty | What to build |
| --- | --- |
| Notice | Before or at consent, a clear, itemised notice: what personal data, for what purpose, how to withdraw consent, how to exercise rights and complain to the Data Protection Board. Offer it in English or, on request, in any language in the Eighth Schedule of the Constitution |
| Consent | Free, specific, informed, unambiguous and given by a clear action; one purpose per consent (no bundling); record the notice version and time; withdrawing must be as easy as giving, and processing stops after withdrawal |
| Legitimate uses | Some processing needs no consent (for example data the user gave voluntarily for a specific purpose, or a legal duty); record which basis each purpose uses |
| Purpose and minimisation | Collect only what the stated purpose needs; erase when the purpose is served or consent is withdrawn, unless law requires keeping it |
| Children (under 18) | Verifiable parental consent before processing; no tracking, behavioural monitoring or targeted advertising directed at children. Simplest path: an 18+ rule in the Terms and at sign-up (*decision*) |
| Rights | Users can get a summary of their data, correct, complete, update and erase it, use grievance redressal, and nominate someone to act for them |
| Grievance contact | A named contact (email and page), answered within the time the Rules set |
| Security safeguards | Reasonable safeguards (encryption, access control, logs, backups); penalties for failures are large (up to ₹250 crore) |
| Breach | Tell every affected user and the Data Protection Board without delay, with a detailed report to the Board within the time the Rules set (72 hours in the Rules as published; *confirm*) |
| Processors | A written contract with every processor; you stay responsible for what they do |
| Logs and retention | The Rules ask fiduciaries to keep certain logs for a minimum period (one year as published; *confirm*); define a retention period for every kind of data |
| Cross-border | Transfers are allowed except to countries the government restricts; check the list |
| Significant Data Fiduciary | If notified as one: Data Protection Officer in India, audits and impact assessments |

### 4.2 GDPR and UK GDPR (only if EU or UK users can sign up) — *decision*

Either limit sign-up to your home market, or comply:

- A lawful basis per purpose (consent, contract, legal obligation, legitimate interest, and so on), recorded in a record of processing (Article 30).
- Rights: access, rectification, erasure, restriction, portability, objection; answer within one month.
- Breach notice to the supervisory authority within 72 hours where required.
- Transfer terms (Standard Contractual Clauses or an adequacy decision) for data leaving the EU or UK.
- An EU or UK representative if you have no establishment there and target their residents.
- Cookie consent under ePrivacy rules: no non-essential cookies or trackers before consent.

### 4.3 Other Indian rules that touch apps

| Rule | What it means |
| --- | --- |
| CERT-In directions (2022) | 6-hour incident reporting, 180-day log retention in India, clock sync (section 3.11) |
| CCPA Guidelines for the Prevention and Regulation of Dark Patterns (2023) | Banned patterns include false urgency (fake countdowns, fake stock), basket sneaking, confirm shaming, forced action, subscription traps, interface interference, bait and switch, drip pricing, disguised ads, nagging, trick questions and SaaS billing tricks. Show the full price up front, make cancel easy, use real timers only |
| Consumer Protection (E-Commerce) Rules 2020 | Seller details, clear prices including taxes, refund and cancellation policy, grievance officer |
| RBI rules on recurring card and UPI payments (e-mandates) | Customer registers the mandate with authentication; pre-debit notification at least 24 hours before each charge; extra authentication above the current limit (₹15,000 for most categories; *confirm*); the customer can cancel the mandate any time |
| GST | Tax invoice for every payment with a continuous number series per financial year; correct CGST, SGST or IGST split; keep records for the period the law requires (about 6 years; *confirm with the accountant*) |
| IT Act 2000 and intermediary rules | Grievance officer and takedown handling if users publish content |

### 4.4 Consent, cookies and trackers

- No analytics, ad pixel or session replay (GA4, PostHog, Meta Pixel, Google Ads, Hotjar, and so on) loads before the user accepts; Reject is as easy as Accept; consent is stored with its version.
- Rejecting after accepting, or opening a page that must not be tracked (staff pages), stops collection at once without a reload (GA4: set `window['ga-disable-<ID>'] = true`, back to false only after a new Accept). If browser storage is blocked, keep the choice in memory for the page load, never default to Accept.
- Session replays mask all rendered text, not only inputs; no names, emails or phone numbers in analytics events; the analytics data region is named in the privacy policy.
- A cookie-free analytics option (for example Cloudflare Web Analytics) can run without consent where the law allows; *confirm*.
- Marketing emails (tips, offers, comeback emails) need their own consent, off by default; account, billing and security emails always send; every non-essential email has an unsubscribe link.

### 4.5 Pages and policies to publish

| Page | Must contain |
| --- | --- |
| Privacy policy | Written from the real code: every outside service that touches personal data, what it receives, why, where it is stored; purposes and legal basis; retention; rights; grievance contact; children; cookies; platform data policies (for example Google API Limited Use) |
| Terms | Who may use the service (minimum age), accounts, acceptable use, AI-content rules, who owns the output (and third-party licence limits), payments and renewal, cancellation, liability, takedown contact, governing law |
| Refund and cancellation | One wording reused at checkout and on plans pages |
| Cookie notice | What each cookie and tracker does, how to change consent |
| Contact and grievance | Named grievance officer, support hours |
| `security.txt` | Security contact and policy |
| Status page | Live status of the main services |

### 4.6 Data lifecycle

- **Field audit before launch:** delete every field collected but not used. Never ask for ID photos, selfies or precise location unless a law or the core feature needs them.
- **Retention table:** every kind of data (account, content, prompts, logs, tickets, tokens, backups, invoices) with its period and the job that deletes it.
- **Delete account:** in settings; confirm by email; a stated recovery window (for example 14 days); then final deletion that revokes third-party access (OAuth), deletes stored files, cancels subscriptions and mandates, cancels scheduled work, removes personal data from the database and logs, and keeps only what tax law requires.
- **Export:** users can download their data.
- **Restores:** keep a minimal deletion record outside the backup and reapply it after any restore before logins, jobs, payments or posting start.

### 4.7 Outside services and agreements

Keep one list (an admin screen that the privacy page reads): service, what it receives, purpose, country or region, data processing agreement status. Accept or sign the DPA with each. Typical entries: hosting and edge, database and auth, storage, payments, email, AI and voice providers, analytics, error tracking, render or compute servers, stock media APIs, social platform APIs.

### 4.8 Platform policies

- Google APIs: follow the Google API Services User Data Policy (Limited Use) and explain the use in the privacy policy; smallest scopes; link to Google's settings for removing access.
- YouTube: follow the API Services Terms; disclose altered or synthetic content where required; set the made-for-kids flag for children's content (COPPA) and never target ads at children.
- App stores: in-app account deletion; privacy forms (Play Data safety, App Store privacy labels) filled from the same outside-services list.

---

## 5. Cost protection

| Risk | Control |
| --- | --- |
| Alerts that never stop spending | For each provider, record whether its cap stops usage or only emails. Examples: Cloudflare Workers paid plans and Google Cloud budgets only alert; Supabase's spend cap stops some usage but not all. Where a provider only alerts, your own budget guard and kill switch must stop spending. Alerts at 50, 80 and 100 percent go to a phone |
| AI bills | Per-call cost counting with a hard daily and monthly cap (3.7); API quotas in the provider console as a backup |
| Loading whole tables | Fetch only the rows a screen shows; cursor pages with a maximum size; never `SELECT *` into the browser |
| Retry storms | Every retry has a budget, backoff and jitter, and respects `Retry-After`; one failing call cannot become thousands |
| Bots doing expensive work | Uploads, generation and paid calls limited per account and per address on the server |
| File bandwidth | Short-lived owner-only signed links plus download limits; a CDN is not a spending cap; usage alerts on storage operations and requests |
| Polling | No constant polling; slow down over time, stop when the tab is hidden, add jitter; no live sockets unless reviewed |
| Free tiers | Alerts near free-tier limits (analytics events, replays, email credits) |

---

## 6. Launch, payments and speed

### 6.1 Before money is spent

- Trademark search for the product name before buying the domain (India: IP India public search in the relevant classes, for software-as-a-service usually 9, 35, 38, 41 and 42; worldwide: WIPO Global Brand Database).
- Licence audit: fonts (for example SIL Open Font License), music (including AI-generated music terms), stock footage (commercial use, attribution, AI-training bans, "competing service" clauses), images, and every code dependency. No GPL or AGPL code shipped in a closed product unless you accept its terms. Add a licence check to CI.
- Provider accounts created and owned by the client.

### 6.2 Payments and subscriptions

**Basics**
- Gateway handles card data; store only references and status.
- Signed, replay-safe webhooks (HMAC over timestamp and raw body, constant-time compare, old timestamps refused, unique event IDs) plus a reconciliation job against the gateway's API.
- The browser's return from checkout never starts a plan; only a verified webhook or reconciliation does.
- Prices in the local currency with tax shown as the law requires (India: GST inside the shown price or added, written once); tax invoices for every payment with a continuous number series.
- Every payment action takes an idempotency key, so a double click or retry charges once.

**Subscription states** (write them in the database; only verified gateway events, reconciliation or an audited staff action move them):

| State | Meaning | Next |
| --- | --- | --- |
| `pending` | Checkout started | `active` on a verified payment; dropped after a timeout |
| `active` | Paid period running; allowance available | `past_due` on a failed renewal; `cancelling` on cancel |
| `past_due` | Renewal failed; grace period (*decision*, for example 3 to 7 days) with retries on a fixed schedule and emails | `active` on payment; `expired` after grace |
| `cancelling` | Cancelled; recurring mandate revoked at once; plan runs to the end of the paid period | `expired` at period end; `active` if the customer resubscribes |
| `expired` | Back to the free plan; nothing deleted | `pending` on a new checkout |

- Allowances reset on each customer's own billing date, so no single job resets everyone; annual plans grant a monthly allowance twelve times, exactly once each.
- Upgrades and downgrades (*decision*): for example, upgrade at once with the price difference for the days left and the same share of extra allowance; downgrade at the next renewal with no refund. One open change at a time.
- Trials once per person, checked against verified email, OAuth account, phone if collected and payment instrument.
- Cancel is as easy as subscribe: two taps from the plans page; cancels the recurring mandate at once; nothing is charged after.
- India recurring payments (e-mandates): pre-debit notice at least 24 hours before each charge; the customer can cancel the mandate any time.
- Each state change writes a ledger row and an audit row; reconciliation catches missed webhooks; a mismatch alerts staff.
- Gateway outage: checkout shows a clear message; access follows the last verified state.

**Refunds**
- Write the refund rule once (*decision*: for example "no refunds, cancel any time", or a refund window) and reuse the same words in the Terms, a refund page, checkout and receipts. Do not hide it, and do not make claims the rule does not support.
- Customer refunds, if allowed, go through the gateway's refund API and its webhooks, never a manual bank transfer; the refund removes the allowance it paid for and writes a ledger row, a credit note for tax and an audit row.
- Exceptional refunds are staff-only, need a reason, and are capped and audited; fresh MFA for large ones.
- Your own mistakes are fixed automatically: a captured payment that did not start the plan is reconciled; a double capture for one order is refunded or flagged for staff.
- Failed paid work (for example a render that failed) returns the reserved allowance automatically; this is not a refund.
- Disputes and chargebacks: handle the gateway's webhooks, freeze the allowance in dispute, keep evidence (invoice, usage log, terms accepted with version and time), and follow a runbook.
- Refund abuse: repeated refund or chargeback after heavy use is flagged; the account can be suspended under the Terms.

**Other**
- Discounts and sales with clear rules, real end dates and no fake countdowns or fake stock.
- Make up for outages with credits through an audited grant, not ad hoc refunds.

### 6.3 Speed and scale (measure first)

1. **Measure:** find the bottleneck (CPU, network, database, disk) before changing machines. Response size is often the first win.
2. **Use the platform's parallelism:** on servers, run a process per core; on edge functions this is handled for you.
3. **Fix queries:** index every hot lookup; never `ORDER BY random()` or a full-table `COUNT(*)` on a large table (look up by indexed key; use estimates); check query plans at target size.
4. **Cache hot reads:** read-mostly data at the edge or in memory; public pages served from cache with no database call.
5. **Queue bursts of writes** and settle them in background batches.
6. **Change language last,** only when measurement shows the runtime is the limit.

Load tests run at launch traffic and above with human pacing; record a speed ladder (requests per second before and after each fix); fake providers at full load, small real samples on an approved budget.

### 6.4 Reliability

- No-logout releases; versioned job payloads; migrations compatible with old and new code.
- Health check, heartbeats from workers, alerts that reach a phone.
- Recovery time and data-loss targets agreed; restore drill passed.

### 6.5 Mobile app (when the website becomes an app)

- MobSF static scan of every Android and iOS build and dynamic scan of test builds before each store release; no high finding open.
- No keys or secrets in the bundle; tokens in the platform's secure storage (Keychain, Android Keystore).
- Deep links and app links validated; WebViews locked to your own origins.
- In-app account deletion and store privacy forms that match the privacy policy.

---

## 7. Phase gate checklists (copy into the project)

**Before any real customer data**
- [ ] Auth, session and revocation rules built and tested (idle from real activity; revocation scope written down)
- [ ] Every API route denies by default; IDOR tampering matrix passes; parameterized queries only
- [ ] No debug in production; storage buckets private; HTTPS forced
- [ ] CAPTCHA, honeypot and limits on every public form
- [ ] RLS, cross-account and public-key tests pass
- [ ] Rate limits on a shared store, real client address
- [ ] Secrets only in the secret store; scans in CI
- [ ] Security headers and CORS allow-list live
- [ ] Logs redacted; request IDs; alerts reach a phone

**Before taking payments**
- [ ] Signed, replay-safe webhooks and reconciliation; the checkout return never starts a plan
- [ ] Subscription states, grace period and retries tested; one trial per person
- [ ] Refund path through the gateway with ledger, credit note and audit; dispute runbook
- [ ] Cancel in two taps; mandate cancelled at once; refund wording reused everywhere
- [ ] Tax invoices; pre-debit notices for recurring payments
- [ ] No dark patterns

**Before launch**
- [ ] Privacy policy names every outside service; Terms with age, ownership, AI rules
- [ ] Cookie banner blocks every tracker until Accept
- [ ] Consent records; separate marketing consent; 18+ rule
- [ ] Field audit done; retention jobs running; delete-account and export work
- [ ] DPAs accepted; GDPR scope decided; trademark and licence checks saved
- [ ] Spending caps that stop spending, per provider
- [ ] 20-attack checklist re-run; authenticated web scan and staging scans clean
- [ ] Attack bots and user bots pass on staging
- [ ] Restore drill keeps deleted accounts deleted
- [ ] Breach and incident runbooks include DPDP and CERT-In timelines
- [ ] `security.txt`, status page, support hours, grievance contact published
- [ ] Every blocker row closed or accepted in writing
- [ ] Pentest coverage (3.16) mapped and tested; an outside pentest or full authenticated scan passed
- [ ] Production A to Z (section 11) done or marked not applicable with reasons

---

## 8. Questions to ask the client early

1. Who owns each provider account and pays each bill?
2. Which countries may sign up? (decides GDPR)
3. Minimum age? (18 is simplest under the DPDP Act)
4. Refund rule, trial rule, cancellation timing, grace period for failed renewals, upgrade and downgrade rules?
5. Session lengths for customers and staff, access token length, and which APIs must refuse a signed-out session at once?
6. Recovery time and acceptable data loss?
7. Support hours and the named grievance and security contacts?
8. Which analytics and ad tools, and in which data region?
9. Retention period for each kind of data and for invoices?
10. Does the product name pass a trademark search?

---

## 9. Gap register template

```markdown
| ID | Requirement | Status | Where | Phase | Blocker |
| --- | --- | --- | --- | --- | --- |
| SG-001 | Access token length decided, refresh rotation with reuse detection | MISSING | T-xxx | Accounts | Yes |
| SG-002 | Logged-out public-key test reads and writes nothing | MISSING | T-xxx | Accounts | Yes |
| SG-003 | Privacy policy names every outside service | MISSING | T-xxx | Policies | Yes |
```

Then a table of which rows each phase must finish before its gate:

```markdown
| Phase | Rows to finish before its gate |
| --- | --- |
| Foundations | SG-0xx, SG-0xx |
```

---

## 10. Example stack mapping (from the source project)

| Rule | Example implementation |
| --- | --- |
| Edge, WAF, DDoS | Cloudflare in front of everything; Workers serve the app |
| Auth | Supabase Auth (Google and email), JWT verified with JWKS; 15-minute access token; customers 30 days idle from real activity; staff 30 minutes idle and 8 hours total, checked by the app |
| Second lock | Postgres RLS; `pg_graphql` turned off; `security_invoker` views |
| Shared rate-limit store | Durable Objects, one per strict counter |
| Client address | `cf-connecting-ip` |
| Files | R2 with 15-minute signed links; uploads re-encoded on an isolated render server |
| Render server | Container behind Cloudflare Tunnel, no inbound ports, pulls jobs |
| Payments | Cashfree with UPI Autopay; HMAC webhook checks; GST invoices |
| Email | ZeptoMail via the Supabase Auth send-email hook; SPF, DKIM, DMARC |
| AI | Gemini and Sarvam behind an app-level daily and monthly cap and a kill switch |
| Analytics | GA4 and PostHog after consent; Cloudflare Web Analytics cookie-free |

---

## 11. Production readiness A to Z

Everything beyond security that makes an app safe to run for real customers. Each row is a rule to put in the plan with a test or a check.

| Area | Rules |
| --- | --- |
| Accessibility | WCAG 2.2 AA: keyboard for everything, visible focus, labels, 4.5:1 text contrast, captions on videos, reduced motion and reduced transparency respected, screen reader pass on the main journeys, touch targets at least 44 px |
| Analytics | Only after consent (4.4); a short event plan tied to decisions (sign-up, first success, payment, cancel); no personal data in events; test accounts excluded |
| Architecture and environments | Local, preview, staging and production separate, with separate keys and data; staging mirrors production settings; infrastructure as code (3.9) |
| Backups and recovery | Recovery time and data-loss targets agreed; automatic backups and point-in-time recovery; restore drill in isolation that keeps deleted accounts deleted (4.6) |
| Browsers and devices | A written support list (for example the last two versions of Chrome, Safari on iPhone and Mac, Firefox, Edge, Samsung Internet); end-to-end tests on Chromium, WebKit and Firefox; hand checks on a real iPhone and a low-end Android phone |
| CI and releases | Every change through a pull request with review and green CI (types, lint, unit, end-to-end, scans); preview per pull request; one-step rollback; no-logout releases; versioned job payloads; database migrations that work with old and new code (expand, move, contract) |
| Configuration | Settings with safe defaults that fail closed; one list of every setting, who can change it and where |
| Data model | Owner ID on every row, foreign keys with chosen delete rules, status checks, indexes on every hot lookup, timestamps in UTC, money as integers in the smallest unit |
| Documentation | README to run it locally in minutes; architecture and data flow; runbooks for each alert; decisions log; API description; handover notes |
| Email and notifications | Own sending domain with SPF, DKIM and DMARC; transactional and marketing streams apart; bounce and complaint handling; unsubscribe on non-essential mail; templates escaped (3.8); each event sends once |
| Error handling for users | Every screen has loading, empty, error, offline and limit states; plain messages that say what to do next; nothing lost on a failed save; retries safe (idempotency, 3.4) |
| Feature switches | Every risky feature behind a switch; kill switches for payments, posting and paid AI that fail closed; switches checked by workers on each job |
| Internationalisation | Text in one place per language; dates, numbers and currency formatted per locale; right fonts for every script; layouts tested with the longest language |
| Legal | Section 4; Terms, privacy, refunds, cookies, grievance contact, licences (6.1) |
| Load and capacity | Measure first (6.3); load test at launch traffic and above with human pacing; queue limits and back-pressure; known breaking point recorded |
| Monitoring | Uptime checks from outside your own edge every minute, alerts to a phone after two failures; error grouping with request IDs and no personal data; dashboards for traffic, errors, latency, queue depth, spend and sign-ups; a status page fed by the uptime checks |
| Mobile web | Every page fits a 360 px screen without sideways scroll; safe-area insets; inputs that do not zoom; fast on a mid-range phone on 4G |
| On-call and incidents | Who answers alerts and when; severity levels; incident steps (3.11); a written review after every serious incident |
| Performance | Budgets per page (for example LCP under 2.5 s, INP under 200 ms, CLS under 0.1 at the 75th percentile on mobile); images sized and lazy-loaded; video with posters and `preload="none"` below the fold; caching of public pages (3.5) |
| Quality bar for the core output | A written bar for what the product makes (for example video quality), a fixed test set scored on every change, and the result must not get worse |
| Search and AI answers | Titles, descriptions, canonical addresses, sitemap and robots, structured data, `noindex` on private and staging pages, fast pages; a direct answer to each question people ask |
| Support | Help pages, a contact form with CAPTCHA (3.5), ticket tracking, published support hours and response times, canned answers for billing and account questions |
| Testing | Section 3.12 layers plus visual checks at phone, tablet and laptop sizes; user bots that walk every journey on staging; a live bot check after launch |
| Time | Store UTC; show the customer's time zone; schedules handle month ends and daylight-saving changes where they apply; clocks synced (3.11) |
| Upgrades and maintenance | Monthly dependency and runtime updates; a deprecation watch for every provider API; yearly review of keys, accounts and access |
| Vendors | One list of outside services (4.7) with owner, bill, limits, data agreement, status page and a fallback or failure plan for each |
| Handover | Client owns every account; keys rotated at handover; documentation and access list delivered; a support period agreed |

**Production gate:** every row above is either done with its check recorded, or written as not applicable with the reason.
