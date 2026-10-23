---
name: testing-browser-qa
description: QA a site with gstack's own /qa skill and browse daemon (installed whole by agylite runtime install gstack); report every defect with evidence, fix, re-verify.
---

<!-- Agylite-authored (D-049, IMPLEMENTATION_PLAN §2.2). gstack /qa runs from gstack's own install, as gstack ships it. -->

# Browser QA (gstack /qa)

1. Check the install: `agylite runtime status` (row `gstack`). Missing: `agylite runtime install gstack` (needs Bun;
   telemetry is set to off, optional global hooks are skipped — owner decision 2026-10-22).
2. Run gstack's **/qa** skill on the target URL, exactly as it instructs (it lives in `~/.claude/skills/gstack/qa/`;
   read its `SKILL.md` if the host does not list it). Its browse daemon runs only while the QA task uses it; gstack's
   `browse` stop command ends it at the end of the task.
3. gstack drives Aside (the owner's real browser) only when Aside is installed; otherwise its own headless browser.
   No other logged-in session is used.
4. Done means: every defect gstack found is fixed and re-verified, `agylite verify` (tests) passes, and
   `agylite verify --browser --url <url>` passes (screenshots at 1440/768/390, console, network, overflow, flows).
