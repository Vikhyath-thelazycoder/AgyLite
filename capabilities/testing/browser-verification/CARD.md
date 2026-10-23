# testing/browser-verification — Browser verification

Browser check of UI work — screenshots at 1440/768/390, console, network, overflow and flows, next to the tests.

- **Use when:** browser check, check in the browser, screenshots, console errors, responsive check, click path
- **Activation:** on-demand · priority 50 · context L2
- **Needs:** runtime node; network optional; browser required-for-output
- **Loads:** 7 bundled files; entry points: browser-qa, browser-testing-with-devtools, click-path-audit, e2e-runner, e2e-testing
- **Done means:** agylite verify --browser PASSED with screenshots at 1440/768/390 and report.json hashes · the project's tests pass too
- **Web QA class:** CORE (headless CORE, screenshot CORE, chrome_devtools OPTIONAL, visible OPTIONAL)
- **Related:** testing/browser-qa, design/visual-quality · **Fallback:** —
