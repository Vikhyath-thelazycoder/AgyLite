---
name: agylite-research
description: Research a question from the web, YouTube, GitHub and (opt-in) X and Reddit — the host's web search finds pages, `agylite research` reads them, and the findings become one sourced report in docs/research/. Read-only.
---

# Agylite Research

1. **Route:** `agylite route "<request>"` → `research/*`; load the routed guide (`agylite skill load agylite/research-web`).
2. **Discover** with the host's own web search tool (Claude Code `WebSearch`). No web search tool: say so and ask the
   user for URLs. Never scrape a search engine.
3. **Read** 3-8 primary sources: `agylite research read <url>` (via r.jina.ai; `--direct` reads on this machine),
   `rss <feed>`, `video <youtube-url> --subs|--meta|--comments N`, `video-search "<q>"`, `channel <url>`,
   `github "<q>"`. X and Reddit: `agylite research doctor` first; when disabled, say so and continue with web sources
   (the owner enables them once with `agylite research enable x|reddit`; never ask for a password or for cookies in
   chat). Research reads as the owner's account: keep volume low.
4. **Report:** `docs/research/<slug>.md` with a source list; every claim has its URL, unverified claims say so.
   Temporary files stay in `~/.agylite/tmp/research/`.

Read-only: nothing here posts, likes, comments or messages, and no browser or logged-in session is used.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
