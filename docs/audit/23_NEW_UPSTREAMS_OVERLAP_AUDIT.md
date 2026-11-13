# 23 — New upstreams: staging audit and overlap plan (Elaya, Cloudflare, Trail of Bits)

Date: 2026-11-02 · Decision: D-051 · Status: **bundled 2026-11-13 (Step 4)**, bundle 752ed8ac07dd. Pins moved from
`candidates/` into the live evidence. How the plan below was implemented: the "REFERENCE" demotions are
`route_excluded` in `config/priorities.yaml` (the files stay bundled and load by name; `agylite validate` fails if one is
named in a `sources_priority`, a rule `skill` or a `skill_overlaps` pair), because REFERENCE in the extraction rules
means "not bundled". Elaya loads next to Taste through a `skill_overlaps` pair limited to the `landing-conversion` rule,
so dashboards and settings pages do not get it. Guarantees 1-3 are `tests/routing/test_one_owner.py` and
`tests/bundle/test_transforms.py::test_elaya_keeps_part_a_only`.

Owner requirement (2026-11-02): **no overlap** with ECC, gstack, Addy, Agency or anything else that already covers
security or design, and no ordinary errors. The rule applied here: **one owner per job.** Every job has exactly one
skill that loads for it; anything else that does the same job is demoted to REFERENCE (still searchable with
`agylite skills` and loadable on an explicit `agylite skill load`, never loaded by a route).

## 1. Pins, licenses and scan

| Key | Repo | Pin | Files | License | Scan (scan_upstream.py) |
|---|---|---|---|---|---|
| `elaya` | elayadesign/ai-design-skills | `456d9e0` (2026-11-02, 16 commits) | 9 | MIT | clean; only CI files flagged (`.github/` workflow, `scripts/validate_skills.py`), not extracted |
| `cfsecurity` | cloudflare/security-audit-skill | `c1c8a8c` (2026-09-14) | 22 | MIT | clean: no MCP, network, hooks, telemetry; `shell_exec` only in the two `*.test.cjs` files |
| `tob` | trailofbits/skills | `2be6433` (2026-10-28) | 1,598 (97 skills, 44 plugins) | CC BY-SA 4.0 (share-alike; non-blocking per D-002) | repo-wide: MCP 7, hooks 28, network 16, telemetry 8 — all outside the kept plugins except as noted in §3 |

Evidence: `docs/audit/evidence/candidates/` (pins, per-file hashes, scan JSON). Kept apart from the live evidence
folders on purpose: `tests/bundle/test_rules.py` requires those to match the bundled repos exactly.

## 2. Design — Elaya

### What it is

Two skills. `figma-designer` (22 KB) and `landing-page-design` (22 KB: Part A strategy, Part B visual system).

### Overlap check against Taste, OpenDesign, UI/UX Pro Max, Appllama

A landing-page request today routes to `design/design-direction` + `design/frontend`; the whole skill loaded is
**Taste** (`taste-skill/SKILL.md`, 38 KB), which already covers landing pages: audience and the one action the page
must drive, section roles (features, proof, testimonial, pricing, FAQ, CTA…), headline length rules, and it
explicitly warns against the stock "hero, logos, three features" sequence. UI/UX Pro Max has `landing.csv`
(landing patterns, CTA placement, conversion notes; queried by script, not loaded). OpenDesign's `copywriting` and
`marketing-psychology` are 1 KB pointers in `media/showcase`.

| Elaya section | Verdict | Why |
|---|---|---|
| A1 Intake (offer, ICP, objections, traffic source, proof assets) | **NEW — keep** | nothing bundled asks for traffic source, objections or proof assets |
| A2 Page structure (fixed 12-section order) | **CONFLICT — drop** | the fixed order is the stock sequence Taste forbids; Taste owns structure |
| A3 Layout selection by traffic/intent (classic, long-form, minimal, comparison) | **NEW — keep** | picks the page type from intent; Taste picks composition, not page type |
| A4 Conversion rules (message match, one CTA, benefit first, risk reversal, objections) | **NEW — keep** | not covered beyond "one primary action" |
| A5 Copywriting formulas | **NEW — keep** (minus its pointer to B1) | Taste has headline length rules, not formulas |
| A6 Build order | **CONFLICT — drop** | Taste's own build flow owns this |
| A7 SEO and AEO (index/noindex, FAQ schema) | **DUPLICATE — drop** | BeyondSEO owns SEO: `noindex` (references/crawler.md, measurement-boundaries.md) and keyword-to-landing-page mapping (playbooks/keyword-research/keyword-to-page-map.md) |
| A8 Pitfalls | **NEW — keep** | conversion pitfalls only |
| Part B (type, spacing, radius, backgrounds, hero, icons, motion, states, B11 "mandatory" tagline reveal) | **DUPLICATE/CONFLICT — drop** | Taste + UI/UX Pro Max + OpenDesign motion own the visual system; B sets fixed values that contradict them and declares "this file wins" |
| `figma-designer` | **EXCLUDE (MCP)** | works only through the Figma MCP (`use_figma` + a `figma-use` skill); no-MCP rule |

**Is it useful?** Yes, but narrowly: Part A is a real conversion-strategy layer nothing in the bundle has. As a
"base of all design" it would be wrong — Part B would fight Taste on every page. Elaya's own credits say "Parts of
this skill were adapted from taste-skill", which confirms the visual half is derived from what we already ship.

**Plan (step 4):** new capability `design/landing-conversion` (intent: landing page, marketing page, conversion,
CTA, signup page, waitlist, pricing page), bundled file = `landing-page-design/SKILL.md` ADAPTed to Part A only
(A1, A3, A4, A5, A8 + the "Strategy" checklist items; ≈ 5 KB, ≈ 1,300 tokens). It loads **together with** Taste
on landing pages: Taste leads on look and structure, Elaya leads on what the page says and why. One rewrite test
asserts Part B, A2, A6 and A7 are absent so an upstream update cannot bring them back silently.

**Paid test (owner: test only Elaya):** suite `design-elaya`, landing-page tasks, three arms — no skill, Elaya's
original `landing-page-design` (whole), AgyLite (Taste + Elaya Part A). Graded on conversion structure (one CTA,
message match, risk reversal, objection handling, specific benefits) plus the existing design checks.

## 3. Security — Cloudflare + Trail of Bits

### What loads today (before any change)

`agylite route "do a security review of our auth and session code"` → `engineering/security`, `engineering/review`,
`testing/security`; whole skills loaded: **Addy `security-and-hardening` and gstack `cso`** (both primaries of
`engineering/security`), plus the review capability's skills (gstack review with its `specialists/security.md`).
So three security playbooks already overlap on one request. Bundled security files today:

| Upstream | Files | Job |
|---|---|---|
| Addy | `security-and-hardening` (+ `hardening-patterns`), `references/security-checklist.md`, `agents/security-auditor.md` | secure coding while building; audit agent |
| gstack | `cso` (+ `audit-phases`), `review/specialists/security.md`, `careful` / `freeze` / `guard` / `unfreeze` | full audit; security pass inside code review; destructive-command guardrails |
| ECC | `security-review` (+ `cloud-infrastructure-security.md`), `agents/security-reviewer.md`, `safety-guard` | review checklist; review agent; guardrails |
| Agency | 13 role prompts (appsec engineer, pentester, AI-code auditor, architect, cloud architect, compliance, incident responder, secrets engineer, senior secops, threat detection, threat intel, IAM, privacy) | role personas |

### Cloudflare `security-audit` vs Trail of Bits

Cloudflare (1 skill + 15 domain files, 230 KB) has a guidance mode and a full-audit mode, diff-scoped runs, a
refutation/validation phase, insecure defaults, and a deep supply-chain and release domain. That makes four of the
eight Trail of Bits plugins I first proposed duplicates:

| Trail of Bits plugin | Verdict | Reason |
|---|---|---|
| `differential-review` | **DROP** | Cloudflare scoped runs cover "the diff between two source refs" |
| `fp-check` | **DROP** | Cloudflare VALIDATION-AND-REPORTING is the refutation phase; fp-check also ships global `Stop`/`SubagentStop` prompt hooks (matcher `*`) that fire on every session stop — against the no-global-hooks rule |
| `insecure-defaults` | **DROP** | covered in Cloudflare CLOUD-AND-DEPLOYMENT, WEB-PROTOCOL-AND-AUTH, RESOURCE-EXHAUSTION |
| `supply-chain-risk-auditor` | **DROP** | Cloudflare SUPPLY-CHAIN-AND-RELEASE owns dependency resolution, CI and release trust; this one also needs network (osv.dev, npm, PyPI, deps.dev, GitHub, scorecard) |
| `variant-analysis` | **KEEP** | different job: given one found bug, find its siblings across the codebase |
| `sharp-edges` | **KEEP** | different job: misuse-resistance review of API/config/crypto designs (Read/Grep/Glob only) |
| `static-analysis` (semgrep, codeql, sarif-parsing) | **KEEP** | runbooks for running local tools; Cloudflare has none. Runs only when `semgrep`/`codeql` are already installed (no installs); `run-scans.sh` forces `--metrics=off` |
| `semgrep-rule-creator` | **KEEP** | different job: writing custom rules |

Excluded from the kept plugins: `workflows/*.js` (host-specific pipelines that `find "$HOME"` for installed plugin
paths), `tests/`, `evals/`, `.claude-plugin/`, `commands/` (host slash commands), the `insecure-defaults` and
`supply-chain` reference JSON. Kept: `skills/**`, `agents/sharp-edges-analyzer.md`, README for provenance.

### One owner per job (step 4)

| Job | Owner (loads) | Demoted to REFERENCE (never routed) |
|---|---|---|
| Security review, vulnerability question, audit, pen test (guidance + full audit) — `engineering/security` | **Cloudflare `security-audit`** | gstack `cso` + `audit-phases`; ECC `security-review` + `cloud-infrastructure-security.md` + `security-reviewer` agent; Addy `security-auditor` agent; Agency `appsec-engineer`, `penetration-tester`, `ai-generated-code-auditor` |
| Secure coding while building a feature (hardening checklist) — new `engineering/secure-coding` | **Addy `security-and-hardening`** (+ `hardening-patterns`, `security-checklist`) | — |
| Security pass inside an ordinary code review — `engineering/review` | gstack review `specialists/security.md` (unchanged) | on a SECURITY_CHANGE review the review capability no longer loads a whole skill; Cloudflare leads |
| Find variants of a known bug | **ToB `variant-analysis`** | — |
| API / config footgun review | **ToB `sharp-edges`** | — |
| Run Semgrep / CodeQL, read SARIF — `testing/security` | **ToB `static-analysis`** | — |
| Write a Semgrep rule | **ToB `semgrep-rule-creator`** | — |
| Destructive-command guardrails (opt-in) | **gstack `careful` / `freeze` / `guard`** | ECC `safety-guard` (same three modes, duplicate) |
| Specialist roles (incident response, compliance, threat intel, secops, detection, IAM, privacy, architecture, cloud architecture, secrets) | Agency role prompts, only when the role is named | — |

The demotions fix overlaps that exist **today**, not only ones the new repos would add.

### Guarantees (tests added in step 4, so "no overlap" is checked, not promised)

1. For every security and landing-page scenario in `tests/routing/scenarios.yaml`, the route loads exactly one
   whole skill per job above (new overlap test fails if two owners of one job load together).
2. No REFERENCE file appears in any `sources_priority`, `skill_hints` or `skill_overlaps` entry
   (`agylite validate` check).
3. Rewrite tests: Elaya Part B / A2 / A6 absent; fp-check hooks, ToB `workflows/` and `commands/` absent.
4. Tier 0 + full unit suite + doctor + validate green before the bundle switches.

## 4. Pre-existing failure found while staging

`tests/unit/test_p25.py::test_compare_reports_routing_and_lower_new_baseline` fails on clean `main` (`32b61f7`):
always-loaded L0 is **8,005 bytes** against an 8,000-byte ceiling. Not caused by this staging (it fails with these
files removed). Owner decision 2026-11-02: quality first, a larger budget is fine — ceiling raised to 10,000 bytes
(≈ 2,500 tokens) in the test; the L0 itself is unchanged.
