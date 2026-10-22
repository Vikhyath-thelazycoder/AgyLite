---
name: research-social
description: What people say on X/Twitter and Reddit, read-only and opt-in through agylite research x / reddit; falls back to web sources when a channel is not enabled.
---

<!-- Agylite-authored (MP5 §1.4). Derived from Agent-Reach (Panniantong/Agent-Reach, MIT, "Agent Eyes")
skill/references/social.md, without OpenCLI browser sessions, browser cookie reading, MCP and the Chinese platforms. -->

# Social research (X and Reddit)

## First: what is enabled

```bash
agylite research doctor        # x: enabled|disabled · reddit: enabled|disabled (rdt-cli unmaintained upstream since 2026-03)
```

X and Reddit work only after the owner enabled them once. If a channel is **disabled**, say so in one line and
continue with web sources (`research/web`: Hacker News threads, forum pages and blog posts are readable with
`agylite research read`). To enable, the owner runs `agylite research enable x` or `agylite research enable reddit`
and pastes the cookie values there (hidden input). **Never ask for a password**, and never ask for cookie values in
chat.

## Commands (read-only)

```bash
agylite research x "<query>" --n 10              # ≤ 20 results per call
agylite research reddit "<query>" --n 10         # ≤ 25 results per call
agylite research reddit "<query>" --sub python   # one subreddit
agylite research reddit --read <post-id>         # one post with its comments
```

There is no posting, liking, replying, voting or messaging, and there never will be.

## Retry chains (stop at the first that works)

- **X search** (X changes its endpoints often): retry once → search fewer, more specific words → read known
  accounts' posts through the web (`agylite research read https://x.com/<user>`) → report X as unavailable today.
- **Reddit**: `rdt-cli` is unmaintained upstream; on an auth error the cookie has expired (the owner re-runs
  `agylite research enable reddit`) → on other errors read `https://old.reddit.com/r/<sub>/` with
  `agylite research read --direct` → report Reddit as unavailable.

## Politeness and risk

Research reads as the owner's own account. Keep volume low: a few searches per task, one call per second at most
(the commands wait between calls). The owner accepts the platforms' terms-of-service risk.

## Output

Quote posts with their URL and date. Opinions are opinions: report how many posts said what, never turn a thread
into a fact. Findings go to `docs/research/<slug>.md` with a source list (see `research/web`).
