---
name: research-web
description: Research a question on the open web - discover with the host's web search, read 3-8 primary sources with agylite research read, and write a sourced report. Read-only.
---

<!-- Agylite-authored (MP5 §1.4). Method derived from Agent-Reach (Panniantong/Agent-Reach, MIT, "Agent Eyes")
skill/SKILL.md and references/{search,web}.md, without MCP, Exa, the Chinese platforms and the update nag; the output
rule follows Matt Pocock's research skill (pocock/research). -->

# Web research

Agylite reads; the host searches. Nothing here posts, logs in or opens a browser.

## Method

1. **Discover** with the host's own web search tool (Claude Code `WebSearch`, or the host's equivalent). If the host
   has no web search tool, say so and ask the user for URLs. Never scrape a search engine.
2. **Pick 3-8 primary sources**: the owner of each fact (official docs, the project's repo, the paper, the vendor's
   page), not a write-up of it. Follow every claim back to the source that owns it.
3. **Read** each one:

   ```bash
   agylite research read <url>              # via Jina Reader (r.jina.ai): clean text, the page URL is sent to r.jina.ai
   agylite research read <url> --direct     # plain HTTP GET + text extraction on this machine, no third party
   agylite research rss <feed-url> --limit 10
   ```

4. **Quote with URLs.** Every claim carries the URL it came from; anything you could not confirm is marked
   **unverified**.

## Retry chain (stop at the first that works)

1. `agylite research read <url>` fails or returns a login wall / empty text → `agylite research read <url> --direct`.
2. Both empty: the page renders with JavaScript. Try the site's RSS/Atom feed, its docs source on GitHub
   (`agylite research github`), or another source for the same fact. Do not open a browser.
3. Still nothing: report the URL as unreadable and move on.

Private URLs (`localhost`, private IPs, `.local`/`.internal`, URLs with `token=`, `key=` or `sig=`) are never sent to
Jina Reader; `read` refuses them unless you pass `--direct`.

## Where things go

- Findings: one report `docs/research/<slug>.md` in the project, with a **Sources** list at the end (title + URL per
  source). Each claim cites its source; unverified claims say so.
- Temporary downloads: `~/.agylite/tmp/research/` (the commands put them there). Never write anything else into the
  project.

## Other channels

- What people say on X / Reddit: `research/social` (`agylite research doctor` shows what is enabled).
- YouTube transcripts, metadata, comments: `research/video`.
- GitHub repos, code and issues: `research/code`.
