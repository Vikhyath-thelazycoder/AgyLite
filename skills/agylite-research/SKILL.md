---
name: agylite-research
description: Research a question from the web, YouTube, GitHub and (opt-in) X and Reddit into one sourced report in docs/research/, where every claim carries the URL it came from — use when asked to research, compare, look up or find out what sources say about something. Read-only.
disable-model-invocation: true
---

# Agylite Research

Produces one report that answers the question, in which every claim has the URL of a page that was actually read
and anything unconfirmed is marked as such. It is read-only: nothing here posts, likes, comments or messages, and
no browser or logged-in session is used.

## Use when · Not for

- Use when: a question needs outside sources: a comparison, the state of a tool or a topic, what a document or a
  video says, what people report.
- Not for: a question about this codebase → `agylite-codebase` · an SEO audit of a site → `agylite-seo` · YouTube
  scripts or titles → `agylite-youtube` (it uses these commands for its inputs).

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>"` → `research/*`; load the routed guide (`agylite skill load agylite/research-web`).
- **The question.** Write it as one sentence that an answer can be checked against. Ask when the request leaves
  open what is being compared, for whom, or as of when.

## Steps

1. **Discover** with the host's own web search tool (Claude Code `WebSearch`). Expect: candidate pages. No web
   search tool: say so and ask the user for URLs. Never scrape a search engine.
2. **Pick 3 to 8 primary sources:** the owner of each fact (official docs, the project's repository, the paper,
   the vendor's page), not a write-up of it. Move on when: each part of the question has a source that owns it.
3. **Read each one.** A search result's snippet is not a reading.

   ```bash
   agylite research read <url>                      # via r.jina.ai; --direct reads on this machine
   agylite research rss <feed>
   agylite research video <youtube-url> --subs      # or --meta, --comments N
   agylite research video-search "<q>"
   agylite research channel <url>
   agylite research github "<q>"
   ```

   Move on when: for every claim you will make, you have read the page that supports it.
4. **X and Reddit (opt-in).** `agylite research doctor` first. When they are disabled, say so and go on with web
   sources; the owner enables them once with `agylite research enable x|reddit`. Never ask for a password or for
   cookies in chat. Research reads as the owner's account: keep the volume low.
5. **Write the report** to `docs/research/<slug>.md`. Temporary files stay in `~/.agylite/tmp/research/`.

## Output

The report file, and in the chat its path plus the answer in two or three sentences:

```markdown
# <The question>

**Answer.** <Two to five sentences. The direct answer first.>
As of: <date> · Sources read: <n>

## Findings
- <Claim, with the number, version or date it rests on.> [<source title>](<url>)

## Where sources disagree
- <What A says, what B says, which is more likely right and why>, or "None found"

## Unverified
- <A claim you could not confirm from a source that owns it, and what you tried>, or "None"

## Sources
1. <Title> — <url> — <publisher or author, date of the page when it has one>
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every claim has a URL, and you read that page in this session. Nothing is cited from memory or from a snippet.
- The source owns the fact. A blog post about a release is not the source for what the release contains.
- Numbers, versions and quotes are copied exactly, with the date they refer to.
- The answer comes first and answers the question that was asked.
- Disagreement between sources is reported, not averaged away or hidden.
- What you could not find or confirm is listed under "Unverified". An empty list means everything was confirmed.
- Each source in the list is used by at least one finding. No padding to make the list longer.

## Stop and ask

- The question is too wide for 3 to 8 sources: propose the narrower question.
- A source needs a login, a payment or an account that is not enabled.
- The findings contradict what the user assumes: say so plainly; do not soften the answer to fit.

## When something fails

| What you see | What to do |
|---|---|
| `read` fails, or returns a login wall or empty text | `agylite research read <url> --direct`. |
| Both are empty (the page renders with JavaScript) | Try the site's feed, its docs source on GitHub (`agylite research github`), or another source for the same fact. Do not open a browser. |
| Still nothing | List the URL as unreadable and go on. Do not cite it. |
| A private URL (localhost, a private IP, a URL with a token) | `read` refuses it unless you pass `--direct`. It is never sent to a third party. |
| X or Reddit is disabled | Say so and continue with web sources. |
| Only secondary sources exist | Use them, and say that no primary source was found. |

## References (read only when needed)

- `references/examples.md` — a good and a weak report on the same question, with notes.

End your answer with the output of `agylite used` (what this work used).
