---
name: agylite-seo
description: SEO audits, AI-search readiness, keyword/competitor/backlink research and reporting through the routed SEO capabilities and the isolated BeyondSEO runtime, with every claim labelled by evidence.
---

# Agylite SEO

1. **Route:** `agylite route "<request>"`; load only the selected `seo/*` capabilities with `agylite context`.
2. **Runtime:** `agylite runtime status` → install once with `agylite runtime install seo` (core; add
   `--browser` only if the user agrees to the large Chromium download for rendered pages).
3. **Capture:** `agylite seo run crawl <url> [--max-pages N]` (output goes to the project's data dir), then
   `report`, `readiness`, `compare`, `backlinks`, `research` as the capability directs.
4. **Label every claim:** `agylite seo evidence <run dir>` gives what each page supports — FACT, OBSERVATION,
   INFERENCE, HYPOTHESIS or UNKNOWN. Failed or partial captures mean "could not be inspected", never "missing".
5. **Live sites are off-limits by default:** `edit apply|rollback` changes a real website and needs
   `agylite seo authorize --site <site> --task <T-id> --reason "…"` and `--authorization <id>`. Never put
   credentials in prompts, state or logs.

SEO captures are SEO evidence only, never engineering verification. `watch` is blocked.

Verification policy: local test-first (`config/verification.yaml`) — no browser, Chrome DevTools, screenshots or MCP.

End your answer with the output of `agylite used` (what this work used).
