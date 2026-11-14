# Skill and workflow quality upgrade — plan

**Status: APPROVED by the owner 2026-11-14. Phases 0, 1 and 2 done (all 14 entry skills rewritten). ▶ RESUME at Phase 3 (the 3 Agylite agents; then set `STRICT = True`).**

Owner request (2026-11-14): assess every skill and workflow in this project and make them better and more detailed,
so that agents and people who use them do not produce thin or generic output ("AI slop"). Plan first, start after
approval. This plan runs **before** the open items of `IMPLEMENTATION_PLAN.md` (Step 5 paid batch, the category
view, Step 6); those continue afterwards, unchanged.

Owner decisions taken on 2026-11-14:

| Question | Decision |
|---|---|
| What is rewritten | Agylite's own files only. Upstream skills (Taste, Ponytail, Archify, gstack, EGM and the others) stay untouched: they are pinned and hash-checked, and they change only through rules. |
| Where the detail goes | A core `SKILL.md` of about 4 to 6 KB, plus reference files next to it that the agent reads only when it needs them. |
| How the result is proven | Free checks now (`agylite validate` and the tests). The paid measurement is the Step 5 batch that is already planned, so there is one paid run, not two. |

## 1. What was assessed

| Group | Count | Where | Size today |
|---|---|---|---|
| Entry skills | 14 | `skills/agylite-*/SKILL.md` | 1.1 to 3.4 KB each |
| Agylite agents | 3 | `agents/engineering-architect.md`, `security-reviewer.md`, `production-reviewer.md` | about 1 KB each |
| EGM agents | 9 | `agents/egm-*.md` | 4.6 to 8.2 KB each; rendered from upstream, **out of scope** |
| Agylite's own guides | 7 | `capabilities/*/*/GUIDE.md` | not yet read line by line (Phase 4 starts with that) |
| Capability cards | 82 | `capabilities/*/*/card.yaml` | one "done means" line each |
| Lifecycle workflow | 1 | `config/lifecycle.yaml` | 6 steps, 6 change types |
| Host copies | 3 | `CLAUDE.md`, `AGENTS.md`, `.agents/skills/agylite/SKILL.md` (generated from `agylite/adapters/hosts.py`) | short |

Not assessed and not in this plan: `templates/project-docs/` (9 document templates) and the two CI workflows in
`.github/workflows/`.

## 2. Findings

### 2.1 Errors: instructions that contradict each other

These are the most harmful, because an agent that reads two opposite rules picks one at random.

| # | Finding | Where |
|---|---|---|
| F-1 | Browser verification was turned on by decision D-049, but several files still forbid it. `agylite-engineering` says "never by browser or screenshot" and, three lines later, "UI work also needs `agylite verify --browser`". `agylite-testing` says "Never verify by opening a browser" and, in the next sentence, "UI work also runs the browser check". | `skills/agylite-engineering`, `agylite-testing` (description and body), `agylite-production`, `agylite-security`, `agents/security-reviewer.md`, `CLAUDE.md` line 7, the Antigravity skill template in `agylite/adapters/hosts.py` |
| F-2 | Every skill ends with the same line about browser checks for UI work, including research, YouTube, media, SEO and update review, where it means nothing. | all 14 entry skills |
| F-3 | Every skill starts with "run `agylite route`", but on Claude Code the prompt hook has already routed and the session bootstrap says not to route again. | 12 of 14 entry skills |
| F-4 | References that an agent cannot resolve: "MP3 §2.3", "MP4", "spec §19.2", "D-049". | `agylite-review`, `agylite-design`, `agylite-routing`, the shared footer |
| F-5 | `agylite-review` step 1 uses `origin/<base>` and does not say how to find the base branch. | `skills/agylite-review` |
| F-6 | The lifecycle file still calls verification "local test-first", and its VERIFY step says "nothing visual claimed as verified", which predates the browser check. | `config/lifecycle.yaml` |

### 2.2 Gaps: what the skills do not say

The skills are command lists. They say which command to run and almost never say what a good result looks like.

| # | Gap | Effect on output |
|---|---|---|
| G-1 | No "use when" and "not for" section. | The agent cannot tell that it loaded the wrong skill, or which one to use instead. |
| G-2 | No output section. Only `agylite-review` describes the shape of the answer. | Each run invents its own format; answers are short summaries with no evidence. |
| G-3 | No quality bar to check before finishing. | Nothing names the usual weak output: "should work", findings without `file:line`, claims without a source, placeholder text. |
| G-4 | Failure handling is partial and differs per skill. | When a command or runtime is missing, the agent guesses or silently skips the step. |
| G-5 | Points where the owner must decide are scattered inside steps. | Agents either ask too much or pass a gate without asking. |
| G-6 | No example of a good and a bad result. | The fastest way to show the expected depth is missing. |
| G-7 | The 3 Agylite agents have no output template, no severity scale, no "do not report" list and no rule for an incomplete review. The 9 EGM agents have all of these. | Reviews from the Agylite agents are shorter and less consistent than EGM's. |
| G-8 | Card "done means" lines are sometimes not checkable (example: "anti-slop criteria checked item by item"). | The finish line that the route shows cannot be tested. |

### 2.3 How skills reach the agent (this decides where the detail must go)

- **Claude Code:** the prompt hook routes every prompt and sends the lead **upstream** skill. 13 of the 14 entry
  skills carry `disable-model-invocation: true`, so they load only when the user types `/agylite:<name>`. When a
  skill rides along, the hook drops the route cards, and with them the "Done means" line (Step 3 part 5).
- **Cursor, Codex, Antigravity:** no prompt hook. The entry skills are the main instructions.

So a better entry skill helps Cursor, Codex and Antigravity on every task, and helps Claude Code only on slash
commands. To lift Claude Code's normal path, a short finish line has to travel in the hook (Phase 5, an owner
decision, because it adds bytes to every prompt).

To check in Phase 0, not assumed here: whether `agylite adapters install` copies files next to `SKILL.md` to Cursor
and Codex; whether the bundle ID or any pinned hash changes when `skills/` changes.

### 2.4 One routing miss seen while assessing

The request that started this plan ("assess all the skills and workflows … make the skills better") was routed to
five design capabilities and the Taste frontend skill. No capability covers work on Agylite's own skills. It is
listed in Phase 5 as a small routing rule.

## 3. The standard every entry skill will follow

One format, in this order. Sections that do not apply are left out, not filled with padding.

```markdown
---
name: agylite-<domain>
description: <what it produces> — use when <the situations and words that should trigger it>.
disable-model-invocation: true
---

# Agylite <Domain>

<Two or three sentences: what this skill produces, for whom, and what it never does.>

## Use when · Not for
- Use when: <concrete situations>
- Not for: <situation> → use `<other skill>`

## Before you start
<Inputs the work needs. What to do when the prompt already carries an `Agylite route:` line (skip routing).
What to ask the owner when an input is missing.>

## Steps
1. **<Name>.** <Action> — `<command>`. Expect: <what the result looks like>. Move on when: <exit check>.

## Output
<The exact shape of the final answer or deliverable: headings, required fields, where files go.>

## Quality bar
<A checklist the agent runs before it answers. Each line is checkable and names one typical weak output for
this domain, for example "every finding has file:line and a failure scenario" or "no claim without its URL".>

## Stop and ask
<The points where only the owner decides: approvals, spend, live systems, irreversible steps.>

## When something fails
| What you see | What to do |

## References (read only when needed)
- `references/examples.md` — one good and one weak result, with notes on why
- `references/<topic>.md` — long material for one step
```

Rules of the standard:

1. `SKILL.md` stays at or under 6,500 bytes. Longer material goes to `references/`.
2. Every step states what to expect and when to move on. A command without an expected result is not a step.
3. Every command named must exist in the CLI. Every file named must exist.
4. No internal references (plan section numbers, decision numbers, spec paragraphs). Say the rule itself.
5. Verification wording comes from `config/verification.yaml` only, and only in skills where verification applies.
6. Plain words, short sentences, no persuasion ("CRITICAL", "you MUST") unless a rule guards against data loss,
   spend or a live system.
7. The needles that existing tests assert stay in the text (`tests/context/test_entry_skills.py`).

Agents get a matching standard: role in one paragraph, read-only statement, inputs, method, severity scale with
definitions, output template, what not to report, and "if a required file cannot be read, report an incomplete
review, not a verdict".

## 4. Phases

Each phase ends the same way: `python -m unittest discover -s tests`, `agylite validate`, `agylite doctor`,
`agylite adapters render` (no stale host copies), commit, push, update this file's checklist, report to the owner
and stop.

- [x] **Phase 0 — standard and checker. No skill text changes. DONE 2026-11-14.**
  - The standard is in `CONTRIBUTING.md`, "Writing entry skills and agents".
  - The check is `agylite/diagnostics/skill_quality.py` (list: `python -m agylite.diagnostics.skill_quality`);
    `agylite validate` runs it in a new "Skill Quality" section. It is in report mode (`STRICT = False`, a warning);
    Phase 3 sets `STRICT = True`. Tests: `tests/unit/test_skill_quality.py` (7).
  - It checks: required sections; the 6,500-byte limit; every `agylite …` command inside code against the CLI
    parser, at every subcommand depth; `references/*.md` and `config/*.yaml` files exist; no internal references
    (`MP<n>`, `§`, `D-<nnn>`); no sentence that forbids browser verification while `config/verification.yaml` says
    `tests-and-browser`; the description says "use when"; agents carry the incomplete-review rule. Host copies
    (`CLAUDE.md`, `AGENTS.md`, the Antigravity skill) get the contradiction check only.
  - **Baseline, 126 problems:** 77 missing sections (of 79 required: only `agylite-codebase` and `agylite-routing` have a `## Steps` heading), 17
    descriptions without "use when", 17 internal references, 9 sentences that forbid browser verification (4
    skills, `security-reviewer`, `CLAUDE.md`, `AGENTS.md`, the Antigravity skill), 3 agents without the
    incomplete-review rule, 3 references to upstream files written as if they were the skill's own
    (`agylite-design`: Taste's `references/tells.md` and `references/critique.md`; `agylite-diagrams`: Archify's
    `references/repository-authoring.md`). 0 unknown commands: every command the skills name exists today, and a
    test keeps it so.
  - **Open point 1, answered:** `agylite adapters install` copied only `SKILL.md` to Cursor and Antigravity. It now
    copies the skill's `references/` folder too and removes one that was deleted from the repo (test added). Claude
    Code and Codex read the repo's `skills/` folder directly, so they already get the references.
  - **Open point 2, answered:** the bundle is built from the pinned upstreams only; nothing under `skills/` or
    `agents/` enters the bundle ID or any pinned hash. Rewriting them does not change the bundle. The only
    generated copy is `.agents/skills/agylite/SKILL.md`, which lists the skill names; `agylite adapters render`
    keeps it current.
  - Found while doing this: `AGENTS.md` also forbids browser verification (not in finding F-1); added to Phase 1.

- [x] **Phase 1 — remove the contradictions (F-1 to F-6). DONE 2026-11-14.** Small edits, no rewrite.
  - F-1: the sentences that forbade browser verification are gone from `agylite-engineering`, `agylite-testing`
    (description and body), `agylite-production`, `agylite-security`, `agents/security-reviewer.md`, `CLAUDE.md`,
    `AGENTS.md`, the Antigravity template (`agylite/adapters/hosts.py`, copy re-rendered) and the lifecycle's VERIFY
    step. Where a rule is still needed it now reads "a screenshot alone is never evidence".
  - F-2: the verification line stays, reworded, in engineering, testing, security, production and review; diagrams
    and design keep their own; it is removed from codebase, media, research, seo, update-review and youtube.
  - F-3: the 10 skills with a route step say, under the title, to skip it when the prompt carries an
    `Agylite route:` line.
  - F-4: no plan, spec or decision numbers remain in the skills. F-5: `agylite-review` says how to find the base
    branch. F-6: lifecycle VERIFY purpose and exit reworded (YAML comments left; agents do not read them).
  - Decision D-053 recorded.
  - Two old tests encoded the rules this plan replaces and were changed with it: `test_entry_skills_are_thin`
    (2,200 bytes → 6,500, the standard's limit) and the host policy test (the `config/verification.yaml` line is
    required only in skills that name `agylite verify`, not in all 14).
  - **Checker: 126 → 100.** 0 contradictions, 0 internal references. Left: 77 missing sections, 17 descriptions,
    3 agents without the incomplete-review rule (Phases 2 and 3), and the 3 upstream reference names in
    `agylite-design` and `agylite-diagrams` (Phase 2c, where the real bundle paths are checked).
  - Left as it is: the product tagline "local test-first verification" in the plugin manifests and
    `agylite/adapters/base.py` (a description of the product, not an instruction; changing it touches four manifests).
  - **Found for Phase 4:** the card `testing/local-verification` still says "no browser, Chrome DevTools or
    screenshot step (D-035)" in its "done means" line, and the route shows that line to agents.

- [x] **Phase 2 — rewrite the 14 entry skills to the standard, in four batches. DONE 2026-11-14.**
  - **2a (pilot): `agylite-engineering`, `agylite-review`.** The owner reads these two and approves the format
    before the rest is written. Changes to the format are made here, once.
    **Written 2026-11-14, waiting for the owner's approval of the format.** Sizes: engineering 1,795 → 6,418
    bytes, review 2,078 → 5,712 (limit 6,500); each has `references/examples.md` (one weak and one good result
    for the same task, with the reasons). Every command and flag in the new text was checked against `--help`;
    the test needles are kept. Checker: 100 → 88. Engineering is 82 bytes under the limit, so anything added to
    it later must go to `references/`. Not confirmed in the live bundle: `egm/egm-resolve` (it is in the Step 4b
    candidate bundle, not in the active one); the review skill's failure table says what to do when a skill is
    not known.
  - 2b: `agylite-testing`, `agylite-security`, `agylite-production`, `agylite-codebase`, `agylite-routing`.
  - 2c: `agylite-design`, `agylite-diagrams`, `agylite-media`.
  - 2d: `agylite-research`, `agylite-youtube`, `agylite-seo`, `agylite-update-review`.
  - Each skill gets `references/examples.md` (one good, one weak result). Every command and flag in the new text
    is run or checked against `--help` before it is written down.
  - Done means, per batch: the checker passes for the batch; the test needles are still present; each skill was
    read once from top to bottom as an agent with no other context, and every step could be carried out.

  - **Result (2026-11-14).** The owner approved the pilot format ("Yeah, good. Continue it."); 2b, 2c and 2d
    followed in the same format. All 14 skills pass the check; **checker 88 → 15**, and the 15 left are the three
    agents (Phase 3). Sizes in bytes, before → after: codebase 2,125 → 4,844 · design 3,352 → 6,499 · diagrams
    1,605 → 5,204 · engineering 1,795 → 6,418 · media 1,140 → 4,839 · production 1,280 → 5,047 · research 1,610 →
    5,306 · review 2,078 → 5,712 · routing 3,239 → 5,335 · security 1,435 → 5,791 · seo 1,596 → 5,387 · testing
    1,794 → 5,194 · update-review 2,240 → 5,303 · youtube 1,708 → 5,273. Total 27.0 KB → 76.2 KB, plus 14
    `references/examples.md` files (read on demand).
  - Design is 1 byte and engineering 82 bytes under the 6,500 limit: anything added to them goes to `references/`.
  - Upstream reference files are now named by their bundle path (`files/taste/skills/taste-skill/references/…`,
    `files/archify/archify/references/…`); the check treats `references/…` without a path in front as the skill's
    own folder.
  - Commands were checked against the CLI parser and `--help`. **Not checked against a live run:** the flags of
    the tools that Agylite passes through to an upstream engine (`design taste draw|inspect|lint`,
    `youtube hookscore|title|deadair|chapters|retention|swipe`, `seo run …`, `diagram finalize|guide`); they are
    kept exactly as the old skills had them. The example files use made-up projects and say so where numbers or
    URLs are invented.
  - The routing examples use three real `agylite route --brief` results, among them "Look into why messages per
    user are high" → `DESIGN_CHANGE · low (tags)`, a wrong route worth a rule in Phase 5.

- [ ] **Phase 3 — the 3 Agylite agents.** Rewrite to the agent standard. EGM agents are not touched.
  - Done means: each agent has the severity scale, the output template and the incomplete-review rule; the
    checker is switched to hard failure.

- [ ] **Phase 4 — Agylite's own guides and the card finish lines.**
  - Read the 7 `GUIDE.md` files and bring them to the same standard where they fall short.
  - Review `description` and `verification_requirements` on all 82 cards; rewrite the ones that are not
    checkable. `intent_tags` are **not** changed, because they drive routing.
  - Done means: every card's finish line names something a person can check; the routing tests are unchanged
    and pass.

- [ ] **Phase 5 — workflow.**
  - `config/lifecycle.yaml`: wording made current; each step's exit stays one checkable sentence.
  - **Owner decision needed:** should the prompt hook keep one "Done means" line for the lead capability even
    when a skill rides along (about 100 to 200 characters per prompt, inside the 9,600 limit)? This is what
    carries the finish line to Claude Code's normal path.
  - A routing rule so that work on Agylite's own skills, agents and workflows does not route to design
    (section 2.4), with a routing test.
  - Done means: hook size test passes; the new routing scenario passes.

- [ ] **Phase 6 — close.**
  - Every test, `validate`, `doctor`, a bundle build, `CHANGELOG.md`, and a version bump if the owner wants one.
  - Dry-run the Step 5 suites again and give the owner the updated estimate, because the skills changed.
  - Then return to `IMPLEMENTATION_PLAN.md`: Step 5 (paid batch, measures this upgrade), the category view,
    Step 6.

## 5. Risks

| Risk | How it is handled |
|---|---|
| More text costs more tokens on hosts that load entry skills on every task. | The 6,500-byte limit; long material is in `references/`, read on demand. Sizes before and after are recorded per skill. |
| A rewrite drops a rule that a test or a benchmark relied on. | The test needles are kept; each batch runs the whole test suite; Step 5 measures afterwards. |
| The new text names a command or flag that does not exist. | The checker compares every command with the CLI parser; each one is also run or checked with `--help`. |
| Changing card text moves routing. | Only `description` and `verification_requirements` change; `intent_tags` and rules are untouched; the routing tests must pass unchanged. |
| A hook finish line raises the cost of every Claude Code prompt. | It is an owner decision in Phase 5, with the byte count shown first. |
| Files under `skills/` change a bundle or adapter hash. | Checked in Phase 0 before any text is changed. |

## 6. What this plan does not do

- It does not edit upstream skills or the EGM agents.
- It does not add skills or capabilities (Step 6 does that).
- It does not run any paid benchmark.
- It does not touch `templates/project-docs/` or the CI workflows.
