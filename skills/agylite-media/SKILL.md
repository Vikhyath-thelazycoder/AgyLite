---
name: agylite-media
description: Launch videos, demos and showcase material from a project or website with the bundled Brag workflow — brag-slim by default, no backend or SEO capabilities involved.
---

# Agylite Media

1. **Route:** `agylite route "<request>"` → `media/*` only.
2. **Plan:** `agylite media plan` shows the workflow (brag-slim by default; full `/brag` only with `--full` and a
   locally installed Hyperframes), the tools found (ffmpeg, node, python) and the output dir (`brag-output/`).
3. **Load the workflow:** run the `load` command from the plan (`agylite context --file files/brag/skills/…`)
   and follow it.
4. **Music cues (optional):** `agylite runtime install brag` once, then `agylite media music-cues <audio>`.

Media output is a deliverable, never verification evidence; showing a rendered video is not a test of the product.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
