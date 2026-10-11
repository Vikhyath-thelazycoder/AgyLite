# P25 evidence — diagnostics & measured benchmarks (2026-10-11)

## Benchmark (`vikhyath benchmark --compare --out docs/benchmarks/RESULTS.md`, bundle `a6c52114bc4d`)
- OLD plugins measured on this machine: ecc@ecc 2.2.3, open-design@open-design 1.0.0, ui-ux-pro-max@ui-ux-pro-max-skill 2.13.0 (ECC is installed twice; counted once).
- Every turn: OLD 127,169 B ≈ **31,792** est. tokens · NEW 3,663 B ≈ **915** (13 own skills/agents + 1,196 B L0 bootstrap).
- 22 spec scenarios: OLD ≈ **1,019,809** · NEW ≈ **176,408** est. tokens → **83 % less**. Per-task detail in RESULTS.md (NEW L1+L2 is sometimes slightly larger than the OLD task files for single-skill tasks, because L1 cards and the L2 file index are added; the per-turn saving dominates).
- Routing accuracy **22/22**; route p50 0.23 ms, p95 0.34 ms; L0 2 ms; L1+L2 p50 12 ms, p95 15 ms.
- A first run double-counted ECC (two installs) → fixed: one install per plugin.

## Doctor (this machine)
50 passed, 0 failed, 10 warnings: ECC (~31,105 est. tokens/turn), Open Design and UI/UX Pro Max installed separately; MCP servers they enable: `chrome-devtools` (ECC, UI/UX Pro Max), `playwright`, `open-design`, `shadcn`; pins audited 8 days ago; 1 duplicate UI/UX design file in the bundle. A first version failed Karpathy as a "stale pin" using the upstream's last-commit date; corrected to the audit capture date.

## Closure
Absolute-import tracing found 2 open gaps: `graphify/tests/test_skillgen.py` imports the excluded `tools/skillgen` → the test is excluded (matrix: 42 gaps, 0 open). Bundle rebuilt: `a6c52114bc4d` known-good, 2,582 files, self-tests exit 0.

## Tests
`tests/unit/test_p25.py`: fake installed plugin with `chrome-devtools` MCP + `~/.claude.json` server → reported; a `ghp_…` version string and an MCP env secret are not printed; function-local `from graphify.serve import …` resolves, third-party imports do not; benchmark compare on a fixture plugin root → routing all ok, NEW per-turn < 6,000 B. Full suite **245 OK, 3 skipped**.

## Graphify upstream suite — per-file breakdown (carried from P12)
Copy of the pinned upstream, scratch venv (core deps + pytest): **5,853 passed, 66 failed, 263 skipped** (4 min 31 s).
| Failures | File | Cause |
|---:|---|---|
| 18 + 12 | test_terraform, test_terraform_modules | `tree-sitter-hcl` extra not installed |
| 7 | test_r_extractor | R grammar (`tree-sitter-language-pack` extra) not installed |
| 7 | test_erlang_extractor | Erlang grammar extra not installed |
| 5 | test_vbnet_extractor | `tree-sitter-vb-dotnet` extra not installed |
| 5 | test_solidity_extractor | `tree-sitter-solidity` extra not installed |
| 6 | test_security | `example.com` DNS lookup — this machine has no DNS (environment, not code) |
| 4 | test_ollama_retry_cap | LLM/Ollama backend not installed (LLM extraction excluded, SEC-09) |
| 1 | test_install_references | `graphify install` (excluded, SEC-08) |
| 1 | test_languages | `KeyError: 'coherence_check'` in an upstream markdown-frontmatter test (upstream issue; markdown extraction is not used by `affected`) |
None of the failing areas is used by `update/query/path/explain/affected` on the languages the OS fixtures use.

## Graphify `test_security` re-run (2026-10-11, bundle 2502140a790a)
Copy of the pinned upstream, scratch venv (core + pytest): **54 passed, 6 failed** (3 min 3 s). All 6 failures are
`ValueError: DNS resolution failed for 'example.com'` — this network cannot resolve that one domain (router and direct
UDP 53 time out; DNS over HTTPS resolves it). Environment, not code; they pass once `example.com` resolves.
