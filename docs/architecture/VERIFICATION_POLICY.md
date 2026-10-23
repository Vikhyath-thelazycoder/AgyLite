# Verification policy

`config/verification.yaml` is the one source of truth (D-049, superseding D-035). Every host gets the same policy.

## What "done" means

- **Every change:** the project's own tests, types, lint and build pass (`agylite verify`; impacted tests first, the full
  suite for release verification). Evidence is a command with its exit code and counts.
- **UI or website work** (any style or markup change, pages, app screens, user flows) additionally needs the browser
  check: `agylite verify --browser [--url <url>] [--flows .agylite/flows.yaml]`. It runs automatically when style or
  markup changed. It uses the pinned browser runtime (`agylite runtime install browser`: Playwright 1.64.0 + Chromium,
  a throwaway context per viewport, never a personal profile), serves or starts the project when no URL is given, and
  FAILS on any of:
  - a console error or page error
  - a failed request to the app itself (4xx/5xx or network failure)
  - horizontal overflow at 390 px
  - an image without alt text
  - a failing flow (`goto`, `click {role, name}`, `fill`, `expect_text`, `expect_url` — plain data; scripts are refused)

  It writes screenshots at 1440, 768 and 390 px plus `console.json`, `network.json`, `flows.json` and `report.json`
  (sha256 of each) to `<project>/.agylite/evidence/browser/<run-id>/`. Pages and app screens also need Taste inspect
  with 0 FAIL (`design_verification`). Without the runtime the check is BLOCKED (NOT_RUN), never a pass.
- **Screenshots never count alone.** The agent may read them (Taste's look-and-fix loop and gstack QA rely on that).
- **QA requests** ("QA the site", "test the site", "click through") route to gstack `/qa` (`testing/browser-qa`), run
  from gstack's own install (`agylite runtime install gstack`; telemetry and update check off, optional global hooks
  skipped).
- **Diagrams:** Archify's finalize, including its headless Chrome browser-check (`diagram_verification`).
- **Still off:** the simulator recording loop, logged-in browser sessions and cookie reading (gstack's own Aside flow
  is the one exception the owner accepted). The Chrome DevTools MCP server is never configured; its `chrome-devtools`
  command line is used instead, with usage statistics off.
