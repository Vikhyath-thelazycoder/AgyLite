---
name: agylite-seo
description: SEO audits, AI-search readiness, keyword, competitor and backlink research and reporting through the routed SEO capabilities and the isolated BeyondSEO runtime, with every claim labelled by its evidence — use when asked to audit a website, check why pages do not rank, research keywords or competitors, or report on a site's SEO.
disable-model-invocation: true
---

# Agylite SEO

Produces SEO findings in which every claim says what kind of evidence it rests on (FACT, OBSERVATION, INFERENCE,
HYPOTHESIS or UNKNOWN) and points to the captured page that supports it. It never calls something missing when
the page could not be inspected, and it never changes a live website without a recorded authorization.

## Use when · Not for

- Use when: a site audit, AI-search readiness, keyword, competitor or backlink research, an SEO report.
- Not for: implementing the fixes in the code → `agylite-engineering` (the route's `pipeline` gives the order:
  SEO audit → engineering → testing) · YouTube SEO → `agylite-youtube` · general research → `agylite-research`.
  SEO captures are SEO evidence only, never engineering verification.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>"`; load only the selected `seo/*` capabilities with
  `agylite context --request "<the user's request>" <id>…`.
- **Scope.** The site or URL, how many pages to crawl, and what the owner wants to learn. Ask when the request
  says only "do SEO".

## Steps

1. **Runtime.** `agylite runtime status`; install once with `agylite runtime install seo` (core; add `--browser`
   only if the user agrees to the large Chromium download for rendered pages). Move on when: the runtime is ready.
2. **Capture.** `agylite seo run crawl <url> [--max-pages N]`. Expect: a run directory in the project's data
   directory, with the pages that were fetched and the ones that failed. Move on when: you know which pages were
   captured, which failed, and why.
3. **Analyse** as the routed capability directs: `agylite seo run report`, `readiness`, `compare`, `backlinks`,
   `research`.
4. **Label every claim.** `agylite seo evidence <run dir>` gives what each page supports:
   - **FACT** — read directly from the capture (the title tag is 84 characters).
   - **OBSERVATION** — seen across pages in the capture (14 of 40 pages share one meta description).
   - **INFERENCE** — follows from facts by known rules (the duplicate descriptions will likely be rewritten).
   - **HYPOTHESIS** — a possible cause that the capture cannot confirm (traffic fell because of the redesign).
   - **UNKNOWN** — could not be inspected.
5. **Rank the findings** by the effect on the owner's goal and by the work needed, not by how many pages show them.

## Output

```markdown
## SEO: <site> — <what was asked>

Captured: <n> pages on <date>; failed or partial: <n> (<which, why>)

### Findings (most important first)
1. **<FACT | OBSERVATION | INFERENCE | HYPOTHESIS>** <the finding, with the number>
   - Evidence: <page URL and what the capture shows>
   - Effect: <what it costs, in the owner's terms>
   - Fix: <the concrete change and where>

### Could not be inspected
- <page or question, and why>, or "None"

### Not in this audit
- <what was out of scope: rankings, traffic data, backlinks …>
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every finding carries a label and names the captured page that supports it.
- A failed or partial capture is reported as "could not be inspected", never as "missing".
- No ranking, traffic or search-volume number appears unless a capture or a source in this run gave it.
- A HYPOTHESIS is called one. It is not written as the cause.
- Each fix says what to change and where (the page, the tag, the template), not "improve the content".
- The first finding is the one that matters most for the owner's goal, not the first one the tool printed.
- No generic checklist items that the capture did not show to be a problem on this site.

## Stop and ask

- **Live sites are off-limits by default.** `agylite seo run edit apply|rollback` changes a real website and needs
  `agylite seo authorize --site <site> --task <T-id> --reason "…"` first, then `--authorization <id>`.
- The Chromium download for rendered pages.
- Credentials for a site, a search console or an analytics account: never put them in prompts, state or logs.

## When something fails

| What you see | What to do |
|---|---|
| The crawl fails or is blocked for some pages | List them under "Could not be inspected" with the reason. Do not conclude anything about them. |
| Pages render with JavaScript and come back empty | Say so; offer the `--browser` runtime. Until then those pages are UNKNOWN. |
| The runtime is not installed | `agylite runtime install seo` when the user agrees. |
| `edit apply` is refused | It needs an authorization. Ask the owner; do not look for another way to change the site. |
| `watch` is asked for | It is blocked: no background process. Offer a repeat crawl and `compare`. |

## References (read only when needed)

- `references/examples.md` — a good and a weak audit of the same site, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
