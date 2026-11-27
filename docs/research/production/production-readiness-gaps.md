# Production readiness by product type: sources, gaps and the requirement catalogue

Date: 2026-11-27. Owner's request: when a user describes a product idea and asks for a plan, Agylite should work out
what kind of product it is (normal website, web app, e-commerce store, Android or iOS app, and so on) and put every
security, privacy, reliability, cost and launch requirement for that kind of product into the plan, in the right phase,
with a test for each. Sources: the owner's playbook, a 103-item pre-launch checklist and web research. This document
lists the gaps between them and what Agylite does today. It is the input for the **Production profiles** step in
`docs/plan/IMPLEMENTATION_PLAN.md`. Nothing in the engine was changed by this research.

> Not legal advice. Every row marked *confirm* carries a date and must be checked against the current official text
> when a project uses it. The catalogue built from this document stores a `checked` date per legal row, and
> `agylite validate` will flag rows older than six months (see the plan, PP1).

## Answer

1. **Agylite has no idea what kind of product it is planning.** `agylite project init --docs` copies nine generic
   templates (`templates/project-docs/`); `SECURITY.md` is 33 lines of empty prompts; nothing detects e-commerce, mobile
   or AI, and nothing writes a requirement, phase or test from the product type. The route for "build me an
   online store" loads planning, architecture, implementation and security cards, but no list of what a store must
   have.
2. **The owner's playbook (source A) is the strongest source** and should be the core of the catalogue: auth and
   sessions, IDOR, rate limits, AI, admin, the 20 attacks, OWASP coverage, Indian privacy law, payments and
   subscriptions, cost caps, and an A–Z of production readiness. It was written for one SaaS shape (accounts,
   subscriptions, AI, India), so it does not cover the other product types well.
3. **The 103-item checklist (source B) adds 31 items A lacks,** mostly engineering run-time: N+1 queries, connection
   pooling, migration rollbacks, unique constraints, cache invalidation, cold starts, timeouts, circuit breakers,
   fallbacks, error boundaries, gradual rollout, autoscaling, CDN and image work, seed data, versioning, changelogs, DNS
   TTL, certificate renewal, multi-region sales tax, AI context limits, model fallbacks, streaming, provider 429s,
   embeddings and vector search, caching AI answers, and disaster-recovery drills that cover secrets and DNS as well as
   data.
4. **Both miss most of what is specific to a product type** (section 3.2): e-commerce (PCI DSS v4.0.1 payment-page
   scripts, card testing, stock reservation, the order state machine, returns, shipping, cash on delivery, product
   disclosures, accessibility law for shops), marketplaces (seller KYC, split payouts, tax collected at source, review
   authenticity), mobile apps (OWASP MASVS, store rules and their 2026 deadlines, store privacy forms, age-signal laws,
   in-app purchase rules, signing keys, forced updates, crash reporting, offline sync), static sites (domain and DNS
   hygiene, email-spoofing protection for domains that send no mail, post-launch search setup), public APIs (keys,
   versioning, deprecation, outbound webhooks), and new law in force since the playbook's sources (EU AI Act Article 50
   since 2 August 2026, EU Cyber Resilience Act reporting since 11 September 2026, the European Accessibility Act since
   28 June 2025, the DPDP Rules timeline, RBI authentication directions from 1 April 2026).
5. **Plan:** one requirement catalogue (each rule with its phase, test, product types and sources), a product-type
   detector with one intake question when unsure, and plan and document generation from the two. Details and order are
   in the plan's **Production profiles** step (PP0–PP6), placed after Step 5b and feeding Step 6 and Step 7.

## Sources

| ID | Source | What it is | How it is used |
|---|---|---|---|
| A | `docs/research/production/security-privacy-playbook.md` | Owner's playbook, 2026-11-26/27, sections 0–11 | Core of the catalogue; its phase map becomes the default phase order |
| B | "103 Things Developers Should Know Before Shipping to Production" (Vikas Yadav, vikasbuilds.com, PDF given by the owner 2026-11-27; page 1 also carried fragments of the same author's "Website & App Security Checklist" (27 checks, October 2026) and "10 Things to Do After Publishing Your Website" (checked 18 October 2026)) | Third-party free checklist | Gap source only. Items are cited by number and short title; the text is not copied. Rules taken from it are written in our own words |
| C | Web research 2026-11-27 (links at the end) | Official pages and law-firm or vendor summaries of dated rules | Gap source and the dated facts in section 3.3 |
| D | This repository at `3f2a81b` | `templates/project-docs/`, `agylite/cli.py` (`project init --docs`), `capabilities/engineering/{planning,security}`, the plan's Step 6 and Step 7 notes | What exists today |

## 1. What Agylite does today (source D)

| Area | Today | Gap |
|---|---|---|
| Product type | None. `lifecycle.detect_stage` (new or existing) and `detect_stack` (languages, frameworks) only | No type, no facets (payments, accounts, AI, uploads, mobile), no countries |
| Project documents | `project init --docs` copies `ARCHITECTURE, DESIGN, FEATURES, IMPLEMENTATION_PLAN, PRD, PROJECT_DECISIONS, SECURITY, SYSTEM_WORKFLOW, TRD` with `{{PROJECT_NAME}}` and `{{DATE}}` filled in, never overwriting | All prompts, no rules; no gap register; no privacy or legal document; no launch checklist; the plan template has one empty phase |
| Planning route | `engineering/planning` (grilling, to-spec) with architecture, implementation, testing strategy and security on a new-product request | Questions are generic. Nothing asks about countries, payments, age, refunds, store release |
| Security capability | `engineering/security` + `testing/security` (gstack CSO, Cloudflare security audit, Trail of Bits, Addy hardening) | Strong for reviewing code; nothing turns a product type into required controls up front |
| Step 6 note (2026-11-15) | "Nothing suitable found: product analytics, privacy/GDPR and legal pages, cloud cost, offline/PWA, app store release, incident runbooks" | These are catalogue modules here (PRIV, COST, MOB-STORE, OPS) |
| Step 7 note | Product pipeline stages to be designed; "which stages are skipped for which product" open | The product type and facets decide this |
| Older plan item (owner 2026-11-19) | "Security profiles": core, +auth, +e-commerce, +admin/CMS, +AI app, +public API, infra, monitoring | Kept and widened into Production profiles: more types, privacy, cost, reliability, launch, mobile, law |

## 2. Product types and facets

A project has **one base type**, any number of **facets**, and a set of **markets** (countries whose law applies).
The catalogue's rules say which types, facets and markets they apply to. A rule applies when its type matches **or**
one of its facets is present, and its market (if any) is one of the project's markets.

### 2.1 Base types

| Type | Examples | Detection signals (request words; repository files) | Usually skipped |
|---|---|---|---|
| `static-site` | landing page, portfolio, brochure site, docs site, blog without accounts | "landing page", "portfolio", "website for my business", "one-pager"; Astro/Hugo/Jekyll/11ty, `next export`, no server routes, no database | Accounts, payments, admin, RLS, sessions |
| `content-site` | blog or news site with a CMS, community content | "blog", "CMS", "articles", "newsletter"; WordPress, Ghost, Sanity, Contentful, Payload | Payments unless facet |
| `web-app` | SaaS, dashboard, internal tool, booking system | "SaaS", "dashboard", "users can sign in", "app where…"; server routes, auth library, database | — |
| `ecommerce` | own store selling physical or digital goods | "store", "shop", "sell", "cart", "checkout", "products", "orders"; Shopify, Medusa, Saleor, WooCommerce, Stripe/Razorpay/Cashfree with orders tables | Subscriptions unless facet |
| `marketplace` | many sellers, platform takes a cut | "marketplace", "vendors", "sellers", "commission", "like Etsy/Amazon for…"; Stripe Connect, Razorpay Route, Cashfree split payouts | — |
| `mobile-app` | Android and/or iOS app (native, React Native, Flutter, Expo) | "Android", "iOS", "Play Store", "App Store", "mobile app"; `android/`, `ios/`, `app.json` (Expo), `pubspec.yaml`, `*.xcodeproj`, `build.gradle` | SEO, cookie banner (replaced by store privacy forms and ATT) |
| `api-service` | public or partner API, backend for others | "API", "SDK", "developers can call", "webhooks for customers"; OpenAPI file, no frontend | Design, SEO, cookie banner |
| `cli-or-library` | CLI, package, plugin | "CLI", "library", "package", "npm/pip package"; `bin/`, `pyproject.toml` with scripts, no server | Nearly every web rule; keeps supply chain, secrets, licence, release |
| `browser-extension` | Chrome/Firefox extension | "extension", "Chrome add-on"; `manifest.json` with `manifest_version` | SEO; adds store-review and permissions rules (*added later if asked*) |

A product can be two types (a web app with mobile apps): the detector returns a primary type and a `also` list, and
rules for every listed type apply.

### 2.2 Facets (each switches on a module)

| Facet | Signals | Module |
|---|---|---|
| `accounts` | sign in, users, profiles | AUTH, AUTHZ, SESSION |
| `payments-one-time` | buy, checkout, pay | PAY |
| `subscriptions` | plans, monthly, trial | SUBS |
| `admin` | admin panel, staff, CMS, back office | ADMIN |
| `ugc` | users post, comments, reviews, uploads public | UGC, MOD |
| `uploads` | upload files, images, video | UPLOAD |
| `ai` | AI, chatbot, LLM, generate, summarize; AI SDKs | AI, AI-LAW |
| `oauth-integrations` | connect Google/YouTube/Instagram, post for the user | OAUTH, PLATFORM |
| `realtime` | chat, live, multiplayer, WebSocket | RT |
| `email-sending` | sends email, newsletter, notifications | EMAIL |
| `children` | kids, school, under 18, family | KIDS |
| `regulated` | health, finance, lending, insurance, legal advice | REG (asks for a specialist; no full rules) |
| `video-publishing` | YouTube, video editing for publishing | PLATFORM (YouTube terms, synthetic content disclosure, made-for-kids) |
| `b2b` | teams, organisations, workspaces, SSO | TENANT |
| `location` | maps, GPS, nearby | LOC |
| `offline` | works offline, PWA | OFFLINE |

### 2.3 Markets

`IN` (India), `EU`, `UK`, `US` (plus US states where a law is state-level), `global`. Signals: currency (₹, INR,
GST, UPI), named countries, the payment gateway (Razorpay or Cashfree suggests India), "worldwide". When the market is
unknown the intake asks one question ("Which countries may sign up or buy?"), because it decides GDPR, tax and
accessibility law (source A §8 Q2).

### 2.4 One question when unsure

If the type or a money facet is unclear after reading the request and the repository, the planning grill asks **one**
question with the detector's best guess first, for example: *"Is this (1) a website people only read, (2) a web app
people sign in to, (3) an online store, (4) a mobile app, or a mix? Who pays, for what, and in which countries?"* The
answer is stored in project state and is never asked again unless the user changes it.

## 3. Gaps

### 3.1 Source B items that source A lacks or only touches

Items of B that A already covers well are not listed (for example input validation, SQL injection, XSS, CSRF, CORS,
SSRF, webhooks, idempotency, backups, refunds, cookie consent, account deletion, export, prompt injection, spend caps,
evals, hallucination checks). The 31 below become new catalogue rows.

| B # | Item (B's title) | A today | New rule (module) |
|---|---|---|---|
| 2 | N+1 queries | — | No query inside a loop over rows; a test counts queries per list endpoint (DATA) |
| 3 | Connection pooling | — | Pooled connections sized to the database's limit; serverless uses the provider's pooler (DATA) |
| 5 | Migration rollbacks | Expand-move-contract only | Every migration has a written undo or a forward fix, tried on staging (DATA) |
| 9, 10 | Race conditions, row locking | Allowance and coupon races only | Stock, seats, balances and bookings change in one transaction with a row lock or a conditional update; 20-parallel-request test (DATA, SHOP) |
| 11 | Unique constraints | — | Uniqueness (email, handle, order number, idempotency key, webhook event ID) enforced in the database, not only in code (DATA) |
| 13 | Soft deletes | — (A's deletion is hard) | Soft delete only for business records with a purge job; personal data still hard-deleted on erasure requests, so soft delete never blocks a legal deletion (DATA, PRIV) |
| 17 | Cache invalidation | Restore purge only | Every cached value has a named invalidation trigger; prices and stock never served stale at checkout (PERF) |
| 19 | Cold starts | — | Measure cold start on the chosen host; keep checkout and auth paths warm or off cold-start platforms (PERF) |
| 20 | Timeouts | — | Every outbound call has a timeout shorter than the caller's (OPS) |
| 25 | Dead letter queues | Named in A §3.9 | Kept; plus a replay tool and an alert on DLQ depth (OPS) |
| 26 | Cron jobs | Retention jobs only | Every scheduled job reports a heartbeat; a missed run alerts (OPS) |
| 30 | Autoscaling | — | Scaling limits set with an upper bound (a cost cap, not only capacity) (OPS, COST) |
| 31 | CDN | Edge in front | Static assets on a CDN with long cache and hashed names (PERF) |
| 32 | Image optimization | Sized and lazy | Modern formats (AVIF/WebP), responsive sizes, a build check on image weight (PERF) |
| 33 | Bundle size | Page budgets | JavaScript budget per route checked in CI (PERF) |
| 34 | Error tracking | Error grouping | Named error tracker with release tags, source maps uploaded privately, personal data scrubbed (OPS) |
| 39 | Error boundaries | Error states | UI error boundaries per region so one widget cannot blank the screen (UX) |
| 40 | Friendly error pages | Plain messages | Custom 404 and 500 pages with a way back and the request ID (UX) |
| 43 | Feature flags (gradual) | Kill switches | Gradual rollout by percentage or cohort for risky features (OPS) |
| 45 | Circuit breakers | Fail closed | Circuit breaker per outside provider; open state shows a clear message (OPS) |
| 46 | Fallbacks | — | Named fallback per dependency (cached data, queue for later, read-only mode) (OPS) |
| 47 | Postmortems | Written review | Blameless template with timeline, cause, actions and owners (OPS) |
| 54 | Password hashing | Leave to provider | When not using a provider: Argon2id (or bcrypt with the 72-byte rule) and a leaked-password check (AUTH) |
| 58 | 2FA for users | Staff only | Optional 2FA for customers; required for sellers and anyone who handles money (AUTH, MKT) |
| 69, 70 | Preview deploys, seed data | Preview named | Seed script with fake data only; preview deploys use test keys and no production data (DEV) |
| 71, 72 | Versioning, changelogs | — | Semantic versions for releases and APIs; a user-facing changelog (DEV, API) |
| 74, 75 | DNS, SSL renewal | CAA, DNSSEC | Lower TTL before moves; certificate auto-renewal with an expiry alert 14 days out; domain auto-renew and registrar lock (OPS, SITE) |
| 81 | Sales tax and VAT | India GST only | Tax by customer location per market (GST, EU VAT with OSS, US sales tax via a tax service) (TAX) |
| 94–97 | Context limits, model fallbacks, streaming, provider rate limits | — | Trim or summarise history to a token budget; a second model or provider on failure; streamed answers; queue and back off on provider 429 (AI) |
| 100, 101 | Embeddings, vector search | One line on retrieval | Per-tenant filters at query time, re-embedding plan on model change, deletion propagates to the index (AI-RAG) |
| 102 | Caching AI answers | — | Cache by normalised prompt and context hash, per tenant, never across users with private data (AI, COST) |
| 103 | Disaster recovery drills | Data restore drill | DR drill covers data, secrets, DNS, the domain registrar, the host account and the CI pipeline (OPS) |

From B's page-1 fragments: "Check Git history for leaks" is in A (Gitleaks on full history). "Connect Google Search
Console" and "Submit your sitemap" are **not** in A: they become post-launch rules (LAUNCH): verify the domain in Google
Search Console (DNS TXT, keep the record) and Bing Webmaster Tools, submit the sitemap, check indexing and Core Web
Vitals reports after two weeks. The remaining items of B's two other lists were not visible in the PDF and were not
checked.

### 3.2 Missing from both A and B (web research, by type)

#### Every web product (CORE)

| Rule | Why | Source |
|---|---|---|
| Pick a verification level: OWASP ASVS 5.0 L1 for sites and simple apps, L2 for anything with accounts, money or personal data; map catalogue rows to ASVS chapters | ASVS 5.0.0 (30 May 2025, 17 chapters V1–V17, three levels) gives the catalogue an external yardstick and a pentest scope | C: OWASP ASVS |
| Domain protection: registrar lock, auto-renew, MFA on the registrar, CAA | A domain lost or hijacked takes the whole product | C (general practice) |
| Domains that send no email publish SPF `v=spf1 -all`, DMARC `p=reject` and a null MX | Stops others spoofing the brand's domain; A only covers domains that send | C (general practice) |
| `security.txt` with an expiry date, plus a vulnerability disclosure policy | A has the file; the policy and the RFC 9116 `Expires` field are missing | C |
| Third-party script inventory: every script on a page listed with owner and purpose; Subresource Integrity where the file is static | Payment-page and consent rules both need it | C: PCI DSS 4.0.1 |

#### Static and content sites (SITE)

| Rule | Source |
|---|---|
| Forms go to a server function with CAPTCHA, honeypot and limits; no form-to-email service that exposes the address | A §3.5 (applies here even without accounts) |
| Hosting with HTTPS, headers and redirects configured as code (`_headers`, `vercel.json`, `netlify.toml`) | A §3.5 |
| Analytics consent, or a cookie-free analytics option where the market allows | A §4.4 |
| Post-launch search setup (Search Console, Bing, sitemap, robots, Open Graph images) | B fragments; A §11 |
| Redirect map when replacing an old site (301 from every old URL) | C (general practice) |
| Legal pages: privacy notice even for a contact form; imprint where the market requires it (Germany, Austria) | C |
| Accessibility: WCAG 2.2 AA; the European Accessibility Act applies to e-commerce and some services sold in the EU, not to a pure brochure site (*confirm* per project) | C: EAA |

#### Web apps and SaaS (APP, TENANT)

| Rule | Source |
|---|---|
| Tenant isolation for team products: every row has a tenant ID, RLS or a query scope by tenant, cross-tenant tests | A covers per user only |
| Invitations: expiring single-use links, role chosen by the inviter, seat limits enforced on the server | C (general practice) |
| B2B extras: SSO (SAML/OIDC) only through a maintained library or provider, SCIM if asked, audit log export, data residency answer, a DPA customers can sign | A §3.10 #3 (SAML) |
| Uptime promise written (or "no SLA") and status page linked | A §4.5 |

#### E-commerce (SHOP), on top of PAY

| Rule | Source |
|---|---|
| Hosted checkout or the gateway's iframe fields so card data never touches the server; decide the PCI SAQ with the acquirer. Since PCI DSS v4.0.1, SAQ A needs the payment page to be safe from script attacks: either apply 6.4.3 (script inventory, authorisation, integrity) and 11.6.1 (change and tamper detection on the payment page) or rely on the provider's confirmation; SAQ A-EP and D must implement both (mandatory since 31 March 2025; *confirm with the acquirer*) | C: PCI SSC, Report URI, Akamai |
| India: no card numbers stored by the merchant (card-on-file tokenisation since 2022; only the last four digits and issuer kept for reconciliation) | C: RBI |
| Prices, stock, discounts, shipping and tax recalculated on the server at order time; the cart's numbers are display only | A §2 (general), made specific |
| Order saved (`pending`) before payment; finalised once, atomically, from a verified webhook or reconciliation; the order state machine (`pending → paid → packed → shipped → delivered`, `cancelled`, `refund_requested → refunded`, `returned`) written in the database with allowed moves only | Owner's 2026-11-19 note; C |
| Stock reserved at checkout with a timeout, released on payment failure; no overselling under 20 parallel buys | B #9–10 made specific |
| Card-testing defence: limits per IP, device, email and card BIN on payment attempts; CAPTCHA or 3-D Secure after failures; alert on decline-rate spikes; never reveal which check failed | C: Stripe |
| Coupon and gift-card abuse: single-use codes, per-customer limits, no stacking unless stated, balance changes locked | A §3.16 (business logic) |
| Address and phone validation; delivery pin-code check (India); shipping partner webhooks verified like payment webhooks | C |
| Cash on delivery (India): limits per order and customer, OTP or call confirmation for high-risk orders, return-to-origin rate tracked | C (market practice) |
| Returns and refunds: written policy per category, return window, who pays return shipping, refund to the original method through the gateway | A §6.2; C: E-Commerce Rules |
| Product disclosures (India Consumer Protection (E-Commerce) Rules 2020): seller name and address, country of origin, total price with taxes and charges, return, refund, exchange, warranty and delivery terms, grievance officer name and contact. A 2026 amendment is reported to take effect on 1 January 2027 with more seller disclosures (best-before date, return shipping cost) (*confirm*) | C: Rules 2020, Khaitan & Co. 2026 |
| India Legal Metrology (Packaged Commodities) declarations on product pages for packaged goods (*confirm* scope) | C (general knowledge, not re-checked) |
| GST: e-invoicing above the turnover threshold set by the government (*confirm* the current threshold with the accountant) | A §4.3, extended |
| EU shops: European Accessibility Act applies since 28 June 2025 to the whole buying journey (EN 301 549, WCAG 2.1 AA today, WCAG 2.2 in the next edition); 14-day withdrawal right and the withdrawal form; EU VAT One-Stop Shop | C: EAA summaries |
| Fake reviews: only verified buyers can review, reviews not edited or hidden for being negative; India IS 19000:2022 online consumer reviews standard; US FTC rule on fake reviews (2024) (*confirm*) | C (general knowledge, not re-checked) |
| Order emails: confirmation, shipping and refund emails sent once per event (idempotent), with the invoice attached or linked | A §11 (email) |
| Abandoned-cart emails only with marketing consent | A §4.4 |

#### Marketplaces (MKT), on top of SHOP

| Rule | Source |
|---|---|
| Seller onboarding with KYC through the payment provider (bank account, tax ID); sellers cannot change payout details without fresh 2FA and a cooling-off period | C (Stripe Connect, Razorpay Route practice) |
| Split payments and payouts only through the provider's split feature; the platform never holds funds it is not licensed to hold (*confirm* the provider's model and RBI payment aggregator rules) | C |
| India GST: e-commerce operators collect TCS on sellers' net sales and file returns (*confirm with the accountant*) | C (general knowledge, not re-checked) |
| Seller isolation: a seller sees only their orders, customers' data limited to what delivery needs, masked phone numbers where possible | A §3.2 made specific |
| Listing moderation, takedown process and intermediary grievance handling (India IT Rules) | A §4.3 |

#### Mobile apps (MOB, MOB-STORE)

| Rule | Source |
|---|---|
| Verification standard: OWASP MASVS v2.1 (8 groups: STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY) with MASTG tests; MAS-L1 for most apps, L2 for money or health; MobSF in CI (A) | C: OWASP MAS |
| Server rules still apply: the app is just another untrusted client; ASVS for the backend | C: MASVS v2 notes |
| No secrets in the app bundle; tokens in Keychain or Android Keystore; no sensitive data in logs, screenshots of sensitive screens blocked where needed | A §6.5; C |
| Network: TLS only (App Transport Security, Android network security config, no cleartext); certificate pinning only with a pin-rotation plan | C |
| Abuse: Play Integrity API and App Attest / DeviceCheck for sign-up, payments and free credits | C (platform docs, not re-checked) |
| Google Play target API: new apps and updates must target Android 16 (API 36) from 31 August 2026; existing apps must target API 35 to stay visible on newer devices; extensions to 1 November 2026; the level rises every year | C: Google Play help |
| Android 16 KB memory pages: apps targeting Android 15+ must support them; Google's page gives 1 February 2027 for updates (earlier dates circulated; *confirm* in Play Console) | C: developer.android.com |
| New personal Play developer accounts (created after 13 November 2023): closed test with at least 12 testers opted in for the last 14 days before production access; plan two to three weeks for it | C: Google Play help |
| Android developer verification: from 30 September 2026 users in Brazil, Indonesia, Singapore and Thailand can install only apps from verified developers (sideloading included); global in 2027 | C: Android developers blog |
| Apple privacy manifest and required-reason APIs (since 1 May 2024), including each third-party SDK's own manifest | C: Apple |
| Account deletion inside the app (Apple 5.1.1(v), since 30 June 2022; Google Play also needs a web link for deletion) | C: Apple; A §4.8 |
| Store privacy forms (Play Data safety, App Store privacy labels) filled from the outside-services list; App Tracking Transparency prompt before any cross-app tracking | A §4.8; C |
| In-app purchase rules: digital goods and subscriptions use the store's billing (with the US exception since the 30 April 2025 ruling: external purchase links allowed on the US storefront); physical goods and real-world services must not use in-app purchase (*confirm* against the current guidelines) | C: Apple guideline updates |
| Age signals: Texas App Store Accountability Act in effect (app stores pass age bands; developers must use them and rate the app and its in-app purchases); Utah and Louisiana similar; Apple and Google offer age-range APIs (*confirm* per project) | C: Wiley, MoFo |
| Release safety: app signing key in Play App Signing or a backed-up keystore; staged rollouts; a minimum-version check that can force an update; over-the-air updates only for JavaScript or assets, within store rules | C (platform practice) |
| Crash and ANR reporting with personal data scrubbed; crash-free sessions target before full rollout | B #34 made specific |
| Push notifications: permission asked in context, opt-out respected, no personal data in notification text on the lock screen | C |
| Deep links: Android App Links and iOS Universal Links verified (assetlinks.json, apple-app-site-association); WebViews locked to own origins (A) | A §6.5 |
| Offline: local data encrypted, conflict rules for sync written down, queued actions idempotent | C |
| Accessibility: VoiceOver and TalkBack pass, Dynamic Type, 44/48 px targets | A §11 |
| Store listing: screenshots, privacy policy URL, support URL, content rating questionnaire, review notes with a demo account | C |

#### Public APIs (API)

| Rule | Source |
|---|---|
| API keys: shown once, stored hashed, scoped, rotatable, with a prefix that secret scanners recognise | C (general practice) |
| Per-key quotas and limits with `429` and `Retry-After`; usage visible to the customer | A §3.6 |
| OpenAPI description kept in sync and fuzzed (Schemathesis, A) | A §3.12 |
| Versioning and deprecation: version in the path or header, `Deprecation` and `Sunset` headers, a written notice period | B #71; C (RFC 8594) |
| Outbound webhooks to customers: signed (HMAC with timestamp), retried with backoff, event IDs for de-duplication, an endpoint verification step, no calls to private addresses (SSRF rules) | A §3.5 mirrored |

#### AI products (AI, AI-LAW)

| Rule | Source |
|---|---|
| EU AI Act Article 50, in force since 2 August 2026: tell people when they are talking to an AI; mark AI-generated audio, image, video and text so it is machine-detectable; label deepfakes; systems on the market before 2 August 2026 have until 2 December 2026 for the marking duty only; fines up to €15 million or 3 % of turnover (*confirm* scope) | C: Cooley, Morgan Lewis, BSI |
| Provider data terms: zero or limited data retention where offered, no training on customer data, region of processing in the privacy notice | A §4.7 extended |
| Per-user and per-tenant token accounting (B #92) feeding the hard cap (A) | A §3.7, B |
| Model and prompt versions recorded with every output so a bad change can be traced and rolled back | C (general practice) |

#### Children, regulated and platform rules

| Rule | Source |
|---|---|
| US COPPA amended rule (compliance date 22 April 2026, *confirm*): verifiable parental consent, separate consent for third-party disclosure, written retention policy | C (general knowledge, not re-checked) |
| Regulated products (health, lending, insurance, investment advice): the plan records "needs a specialist review" and stops before launch; Agylite does not write those rules | Owner scope |
| YouTube and video publishing (Agylite's YouTube domain): altered or synthetic content disclosure, made-for-kids flag, music and footage licences | A §4.8, §6.1 |

### 3.3 Dated facts to update in source A

| A says | Current (2026-11-27) | Action |
|---|---|---|
| DPDP Rules: "confirm which obligations are in force" | Rules notified 13–14 November 2025; Board provisions at once; consent managers from November 2026; most fiduciary duties (notice, consent, security, breach, retention, children) 18 months after notification, about May 2027. The 72-hour breach report and one-year log retention were not re-confirmed in this research | Store the phase dates in the catalogue's IN rows with `confirm` |
| No mention | EU Cyber Resilience Act: reporting of actively exploited vulnerabilities and severe incidents through ENISA's platform since 11 September 2026; full product rules from December 2027. Applies to "products with digital elements" placed on the EU market (mobile apps, desktop software, devices); pure SaaS is mostly out of scope (*confirm* per product) | New EU row for mobile and CLI types |
| No mention | EU AI Act Article 50 (above) | New AI-LAW rows |
| WCAG 2.2 AA | European Accessibility Act enforceable since 28 June 2025 for e-commerce and listed services in the EU | New EU row for shops and apps |
| RBI e-mandates | RBI Authentication Mechanisms for Digital Payment Transactions Directions 2025 (dated 25 September 2025; comply by 1 April 2026): two factors, one dynamic, risk-based checks allowed | Note in the IN payment rows (gateways implement it; the merchant must not bypass it) |
| OWASP Top 10 2025, API 2023, LLM 2025 | Plus ASVS 5.0 (May 2025) and MASVS v2.1 | Map catalogue rows to both |

## 4. The catalogue: modules and which product types get them

Each module is a group of rules in the catalogue (`config/production/requirements.yaml`, plan PP1). Rule IDs are
`<MODULE>-<nn>`. ● = always for this type, ○ = when the facet is present, – = not applicable (the plan writes the
module as "not applicable: <reason>, recheck if <trigger>").

| Module (main sources) | static-site | content-site | web-app | ecommerce | marketplace | mobile-app | api-service | cli-or-library |
|---|---|---|---|---|---|---|---|---|
| CORE: secrets, HTTPS, headers, CORS, debug off, scans in CI, supply chain (A 3.3–3.5, 3.12, 3.16) | ● | ● | ● | ● | ● | ● | ● | ○ secrets, supply chain, licence only |
| SITE: forms, hosting config, domain and DNS, search setup (A 3.5, 11; B 74–75, 90; C) | ● | ● | ● | ● | ● | – | – | – |
| AUTH / AUTHZ / SESSION / IDOR (A 3.1, 3.2, 3.2a; B 54–58) | – | ○ | ● | ● | ● | ● | ● keys | – |
| ABUSE: rate limits, bots, CAPTCHA (A 3.6) | ○ forms | ● | ● | ● | ● | ● | ● | – |
| ADMIN (A 3.8) | – | ○ | ○ | ● | ● | ○ | – | – |
| DATA: model, migrations, constraints, transactions, N+1, pooling, backups (A 11; B 1–14) | – | ○ | ● | ● | ● | ● backend | ● | – |
| UPLOAD (A 3.5) | – | ○ | ○ | ○ | ● | ○ | ○ | – |
| PAY (A 6.2 basics; C PCI, RBI) | – | – | ○ | ● | ● | ○ | ○ | – |
| SUBS (A 6.2) | – | ○ | ○ | ○ | ○ | ○ | ○ | – |
| SHOP (C) | – | – | – | ● | ● | ○ | – | – |
| MKT (C) | – | – | – | – | ● | – | – | – |
| TAX and invoices (A 4.3, 6.2; B 81–82) | – | – | ○ | ● | ● | ○ | ○ | – |
| UGC and moderation (A 4.3; C) | – | ○ | ○ | ○ reviews | ● | ○ | – | – |
| AI, AI-RAG, AI-LAW (A 3.7; B 91–102; C) | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| OAUTH and PLATFORM (A 4.8) | – | ○ | ○ | ○ | ○ | ○ | ○ | – |
| EMAIL (A 3.1, 11; B 76) | ○ | ● | ● | ● | ● | ○ | ○ | – |
| PRIV: notice, consent, rights, retention, deletion, export, processors (A 4; B 84–88) | ● notice only | ● | ● | ● | ● | ● + store forms | ● | – |
| PRIV-IN / PRIV-EU / PRIV-US / KIDS (A 4.1–4.3; C) | by market | by market | by market | by market | by market | by market | by market | – |
| A11Y (A 11; C EAA) | ● | ● | ● | ● (law in EU) | ● | ● native | – | – |
| PERF (A 6.3, 11; B 15–19, 29–33) | ● | ● | ● | ● | ● | ● app size, startup | ● latency | – |
| OPS: monitoring, alerts, timeouts, retries, breakers, flags, DR, incidents (A 3.11, 6.4, 11; B 20–47, 103) | ● uptime, certificate | ● | ● | ● | ● | ● crash reporting | ● | ○ release only |
| COST: caps that stop, alerts (A 5; B 92–93) | ○ | ○ | ● | ● | ● | ● | ● | – |
| DEV: environments, CI, reviews, preview, seed data, versioning, changelog, IaC (A 11; B 63–73) | ● | ● | ● | ● | ● | ● | ● | ● |
| MOB and MOB-STORE (A 6.5; C) | – | – | – | – | – | ● | – | – |
| API (C; B 71) | – | – | ○ public API | ○ | ○ | – | ● | – |
| LEGAL and LAUNCH: terms, policies, trademark, licences, security.txt, status page, support, go/no-go (A 4.5, 6.1, 7; B fragments) | ● light | ● | ● | ● | ● | ● | ● | ○ licence, release |

Phase placement follows A §1 (Design → Prep → Foundations → Accounts, data, billing → Core features → Integrations →
Admin → Hardening → Load test and launch → After launch), with a **Store release** phase added for mobile apps and a
**Payments** gate (A §7 "Before taking payments") for SHOP, MKT, PAY and SUBS. A phase gate lists the blocker rows of
the modules that apply.

## 5. Intake questions by type

Asked once, only when the request and repository do not answer them; source A §8 is the base for every type.

| Type or facet | Extra questions |
|---|---|
| All | Countries (decides GDPR, tax, accessibility law); minimum age; who owns each provider account; recovery time and acceptable data loss; support hours and named grievance and security contacts |
| ecommerce, marketplace | Physical, digital or both; payment gateway; cash on delivery; shipping partner; return window and who pays return shipping; GST registration and invoice series; stock source (own warehouse, dropship, sellers) |
| marketplace | Who is the seller of record; commission model; seller payout schedule; KYC provider |
| subscriptions | Refund rule, trial rule, grace period, upgrade and downgrade rule (A Q4) |
| mobile-app | Android, iOS or both; native or cross-platform; Play account type (personal or organisation, created before or after 13 November 2023); digital goods sold in the app; push notifications; offline use; tracking or ads (ATT) |
| ai | Which providers; data sent; outputs shown to others or published; audience in the EU (Article 50) |
| api-service | Public or partner; how customers get keys; versioning promise |
| static-site | Forms and where they go; analytics; domain and registrar; replacing an old site (redirects) |

## 6. Decisions taken in this research (defaults; the owner can change them)

| Decision | Default | Why |
|---|---|---|
| Name | "Production profiles" (widens the 2026-11-19 "Security profiles" item) | The rules cover privacy, cost, reliability and launch, not only security |
| Storage | One YAML catalogue + per-module reference pages for agents; rules never duplicated in templates | One source for the generator, the validator and the skill |
| Source B text | Cited by number and short title, rules rewritten | Third-party content; Agylite ships its own words |
| Legal rows | Kept, each with `markets`, `checked` date and `confirm: true` | Laws move; stale rows are flagged, never silently trusted |
| Regulated domains | Flag and stop for a specialist, no rule set | Out of scope and risky to approximate |
| Browser extensions | Type recognised; rules only when a project needs them | No current demand |

## Web sources (read 2026-11-27)

- PCI DSS v4.0.1 and SAQ A: [Report URI FAQ](https://blog.report-uri.com/pci-dss-4-0-1-saq-a-and-client-side-security-a-plain-english-faq/),
  [Report URI on 6.4.3 and 11.6.1](https://blog.report-uri.com/pci-dss-4-0-1-and-requirements-6-4-3-and-11-6-1-what-changed-for-payment-page-scripts/),
  [Akamai](https://www.akamai.com/blog/security/pci-dss-v4-0-1-changes-qualify-saq-a),
  [Cloud Security Alliance](https://cloudsecurityalliance.org/articles/pci-dss-6-4-3-and-11-6-1-a-deep-dive-into-payment-page-security-and-integrity-requirements),
  [Adyen script security](https://docs.adyen.com/development-resources/pci-dss-compliance-guide/script-security)
- Card testing: [Stripe, checkout fraud](https://stripe.com/resources/more/checkout-fraud)
- OWASP: [ASVS project](https://owasp.org/www-project-application-security-verification-standard/),
  [ASVS on GitHub](https://github.com/OWASP/ASVS), [MASVS releases](https://github.com/OWASP/owasp-masvs/releases),
  [MASTG releases](https://github.com/OWASP/mastg/releases)
- Google Play: [target API level](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en),
  [target SDK](https://developer.android.com/google/play/requirements/target-sdk),
  [16 KB page sizes](https://developer.android.com/16kb-page-size),
  [closed testing for new personal accounts](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en),
  [developer verification](https://support.google.com/android-developer-console/answer/16561738?hl=en),
  [developer verification blog, March 2026](https://android-developers.googleblog.com/2026/03/android-developer-verification.html)
- Apple: [5.1.1(v) account deletion](https://developer.apple.com/support/offering-account-deletion-in-your-app),
  [required reason APIs](https://developer.apple.com/tutorials/data/documentation/bundleresources/describing-use-of-required-reason-api.md),
  [US guideline changes, May 2025 (MacRumors)](https://www.macrumors.com/2025/05/01/apple-updates-u-s-app-review-guidelines-epic/)
- Age-signal laws: [Wiley, state App Store Accountability Acts](https://www.wiley.law/alert-State-App-Store-Accountability-Acts-Introduce-New-Obligations-for-App-Developers),
  [MoFo, Texas law in effect](https://www.mofo.com/resources/insights/251111-texas-targets-app-stores-with-new-accountability-law)
- India: [DPDP Rules 2025 (PIB)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf),
  [YourStory on the 18-month rollout](https://yourstory.com/2025/11/digital-personal-data-protection-dpdp-rules-2025-rollout-over-18-months),
  [RBI card-on-file tokenisation](https://website.rbi.org.in/web/rbi/-/notifications/tokenisation-card-transactions-permitting-card-on-file-tokenisation-coft-services-12159),
  [RBI authentication directions 2025](https://website.rbi.org.in/web/rbi/-/press-releases/rbi-issues-directions-on-framework-on-authentication-mechanisms-for-digital-payment-transactions),
  [E-Commerce Rules 2020 (Khaitan & Co.)](https://khaitanco.com/thought-leaderships/Stricter-Regulations-on-E-Commerce-The-Consumer-Protection-E-Commerce-Rules-2020),
  [E-Commerce Amendment Rules 2026 (Khaitan & Co.)](https://www.khaitanco.com/sites/default/files/2026-09/Ergo_E-Commerce%20Amendment%20Rules_18%20September%202026.pdf)
- EU: [AI Act Article 50 (Cooley)](https://cooley.com/news/insight/2026/2026-08-03-eu-ai-act-transparency-obligations-take-effect-2-august-2026),
  [Article 50 guide](https://artificialintelligenceact.eu/transparency-rules-article-50/),
  [CRA reporting (European Commission)](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting),
  [CRA (Ireland NCSC)](https://ncsc.gov.ie/cra/),
  [EAA for online retailers (Bird & Bird)](https://www.twobirds.com/en/insights/2025/a-guide-to-navigating-the-european-accessibility-act-for-online-retailers-service-providers-and-plat),
  [EAA (Ireland NDA)](https://nda.ie/eaa)
- Not re-checked on the web in this research (from general knowledge, marked *confirm* above): India Legal Metrology
  declarations, IS 19000:2022, GST TCS for e-commerce operators and the e-invoicing threshold, the US FTC fake-reviews
  rule, the COPPA compliance date, Play Integrity and App Attest details, RFC 8594 and RFC 9116 fields.
