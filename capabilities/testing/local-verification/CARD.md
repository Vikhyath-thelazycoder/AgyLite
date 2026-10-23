# testing/local-verification — Local verification

Local test-first verification: discover and select the smallest sufficient test set by change impact, run unit/integration/API/state tests, types, lint, build; diagnose failures; targeted reruns.

- **Use when:** verify, check whether, works, login flow, checkout flow, user flow, login, checkout …
- **Activation:** on-demand · priority 50 · context L2
- **Needs:** runtime os-native; network local-only; codebase analysis first
- **Loads:** 9 bundled files
- **Done means:** selected checks (tests, types, lint, build) executed with machine-readable results recorded by testing/evidence · no browser, Chrome DevTools or screenshot step (D-035)
- **Web QA class:** CORE
- **Related:** testing/strategy, codebase/impact-analysis · **Fallback:** —
