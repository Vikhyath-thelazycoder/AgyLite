# P16 evidence — SEO domain (2026-10-10)

- `vikhyath runtime install seo` (bundle `495f026f381e`): BeyondSEO 2.9.1, lock `1a4afb47e06c`, core only, **3.0 s**; `runtime status`: ready. `bundle verify` afterwards: intact.
- `vikhyath seo run crawl http://127.0.0.1:8765/ --max-pages 5` (fixture site on loopback): run completed, output in `$VIKHYATH_HOME/projects/<id>/seo/<time>/` (summary, pages.jsonl, findings, readiness, report …); the project tree unchanged. BeyondSEO refused the loopback address (`private_or_nonpublic_address`, its SSRF guard).
- `vikhyath seo evidence <run>` → `presence claims: [UNKNOWN] could not be inspected: No successful usable page capture.` (same for absence claims) — BeyondSEO `capture_quality` run inside the SEO venv.
- `vikhyath seo run watch …` → blocked (exit 2). `vikhyath seo run edit apply --site x` → "authorize it first" (exit 2).
- Upstream suite (copy of the staged pin, SEO venv + pytest, core only): **340 passed, 9 failed, 17 skipped, 26 subtests passed** (11.6 s). Failures: 6 `test_browser_features`, 2 `test_trial_regressions` (auto mode renders), 1 `test_discovery_research::test_doctor_preserves_execution_error` — all hit `No module named 'playwright'` (browser extra, opt-in).
- `python -m unittest discover -s tests`: **218 OK, 3 skipped**; doctor 49/0; validate 22/0.

## Success path without network (2026-10-11)
This machine's DNS was unavailable (`curl https://example.com` → resolving timed out; `ping 8.8.8.8` OK), so a live crawl could not complete (recorded as UNKNOWN, project untouched). The labelling of successful captures was checked offline instead: three saved page records → `vikhyath seo evidence <run>` (BeyondSEO `capture_quality` inside the SEO venv):
- complete page (200, 240 words) → presence **FACT** "seen in a complete capture", absence **FACT**
- JavaScript shell (200, 12 words, 4 scripts) → presence **OBSERVATION**, absence **UNKNOWN** "could not be inspected completely: Possible JavaScript shell…"
- failed page (timeout) → **UNKNOWN** "could not be inspected: No successful usable page capture."
A live public crawl remains to be re-run once DNS works (`vikhyath seo run crawl https://example.com/`).

## Live crawl retry (2026-10-11, after the v2.1.1 install)
`agylite runtime install seo` (2.2 s) then `agylite seo run crawl https://example.com/ --max-pages 5` → exit 1:
1 attempted, 0 inspected, 1 blocked_or_failed (`gaierror: nodename nor servname provided`, `robots_unavailable`).
On this machine `github.com` and `google.com` resolve but `example.com` does not (`dscacheutil`, `curl` timeout), so
the live crawl, and the 6 Graphify `test_security` tests that fetch example.com, stay open until it resolves.

## Live public crawl — success path (2026-10-11)
`example.com` is unresolvable on this network only (router 192.168.1.1 and direct UDP 53 to 1.1.1.1 time out; DNS over
HTTPS returns its A records), so the live crawl ran against the owner's public repo page instead:
`agylite seo run crawl https://github.com/Vikhyath-thelazycoder/vikhyath-ai-engineering-os --max-pages 3` → exit 0;
3 attempted, 2 inspected, 1 skipped by robots.txt (`robots_rule_disallowed`, correct). `agylite seo evidence <run>`:
complete captures labelled [FACT], the disallowed page [UNKNOWN]. **Live crawl: VERIFIED.** The 6 Graphify
`test_security` tests stay open (they need `example.com`; running the upstream suite also needs the owner's permission).

## example.com crawl (2026-10-11, after DNS fix)
`agylite seo run crawl https://example.com/ --max-pages 5` → exit 0; 1 attempted, 1 inspected, 0 failed. Labels:
presence [OBSERVATION] / absence [UNKNOWN] — partial capture because the opt-in browser extra (playwright) is not
installed, exactly as designed. **Live crawl on the spec target: VERIFIED.**
