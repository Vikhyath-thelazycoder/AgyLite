---
name: agylite-youtube
description: YouTube creator work — scripts and hooks, titles and thumbnails, Shorts picks, edit decision lists, chapters, SEO, retention and outlier analysis, plans and comment replies — in the creator's voice. Writes only; never renders, cuts or uploads video.
---

# Agylite YouTube

1. **Route:** `agylite route "<request>"` → `youtube/*`; load the routed skill (`agylite skill load ytagent/yt-<name>`).
2. **Voice:** `agylite youtube voice init` once; every skill reads `~/.agylite/youtube/voice.md`. While it is the
   unfilled template, ask for it (or three of the creator's videos), or proceed and mark the output **generic voice**.
3. **Tools** (run them; never eyeball a score): `agylite youtube hookscore --hook "…"`, `title --title "…" --thumb "…"`,
   `deadair <transcript>`, `chapters <transcript>`, `retention <export.csv> [--transcript t]`, `swipe <collected.json> --min 2.0`.
   Inputs come from research: `agylite research video <url> --subs` (transcript), `agylite research channel <url>
   --swipe collected.json` (≥ 4 videos per channel).

This domain writes scripts, edit lists, Shorts picks, titles, chapters and plans. It never cuts, renders or uploads
video. If asked to edit or render, say that video editing is not part of Agylite yet, and offer the edit decision list
(`yt-edit`) and Shorts picks (`yt-shorts`) to apply in the user's editor. Nothing publishes: the skills write, the
creator uploads.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
