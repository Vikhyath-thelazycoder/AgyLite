# Update and rollback

Upstreams never update themselves. Updates are explicit, checked and reversible.

```bash
agylite update <repo> <40-char commit sha> [--source DIR] [--self-test]
agylite rollback [--to <bundle id>]
agylite gc [--dry-run]
```

**update** — copy the current evidence, take the new commit's inventory (blob hashes) and pin, diff it (bundled paths
and capabilities affected), refuse it if a bundled file still references a path the commit removed, build a new bundle
beside the current one, verify its integrity and registry (and runtime self-tests with `--self-test`), and switch
`current` only if everything passes. `previous` keeps the old bundle. A failed or interrupted update leaves `current`
untouched. History: `~/.agylite/updates/history.jsonl`; event UPSTREAM_UPDATED.

**rollback** — switches to `previous` or a named bundle, only if it is known-good and re-hashes intact. Files,
registry, provenance and the runtime locks derived from them change together. Event UPSTREAM_ROLLBACK.

**gc** — keeps `current`, `previous` and the two newest failed builds; removes other bundles, runtimes that no kept
bundle uses, and leftovers of interrupted builds.

Tags and branches are refused because they move; pin a commit.

## Staying current: review → benchmark → the owner approves (P28, MP6)

Owner decision 2026-10-21: nothing switches on its own — not locally, not in CI, not at session start.

```bash
agylite update --check                         # newest commit per upstream (git ls-remote; seconds, nothing downloaded)
agylite update --review --due --tier1-plan     # review every due upstream (or --repo X); writes ~/.agylite/updates/review-<date>/REPORT.md
agylite update --pending                       # reviewed candidates waiting for the owner
agylite update --approve gstack@514fbfd        # switch to that reviewed candidate (refuses a stale review)
agylite update --reject ecc@90606c8 --reason "…" # remember it; the next review starts after this range
agylite update --latest                        # alias of --review --due (prints that updates need approval)
agylite update --schedule install              # optional weekly review on this Mac (Mondays 09:00); `remove` undoes it
```

What a review does, per upstream with new commits:

1. **Collect** the non-merge commits pin..target from the blobless mirror (`~/.agylite/mirrors/`; only new objects).
2. **Classify** every commit by rules (no model call): `BREAKING` (a bundled file deleted/renamed, or a `REWRITES`
   pattern that no longer matches), `PRIMARY` (a file first or second in some capability's `sources_priority`),
   `BUNDLED`, `NEW_SKILL`, `NEW_UNCLASSIFIED`, `POLICY` (MCP config, hooks, telemetry, a new installer or a license
   change that would reach the bundle; any new MCP config file), `SECURITY` (security words in the message and a
   bundled/runtime path touched), `IRRELEVANT`.
3. **Show** section-level diffs (`#`–`###`, token deltas; the unified diff for PRIMARY files), runtime version changes
   and the changelog between them.
4. **Build and check** a candidate bundle without activating it (`~/.agylite/updates/<repo>-<sha12>/`), run Tier 0 on
   it against the current bundle, and print the Tier 1 plan (never run).
5. **Verdict:** `SECURITY_FAST_TRACK`, `ADOPT`, `ADOPT_AFTER_TIER1`, `NEEDS_RULES` (with `<repo>-proposed-rules.patch`),
   `HOLD`, `SKIP`, and "requests nobody routed" since the last review.

A candidate is built against the other upstreams' current pins, so approving one makes the other pending reviews
stale: approve, then review the rest again. The L0 bootstrap shows `updates: N reviewed upstream update(s) awaiting
approval` from local files only. The `agylite-update-review` skill walks the owner through a report.

In the repository, `.github/workflows/upstream-updates.yml` checks daily and, weekly (and monthly for monthly
upstreams), reviews, approves only `ADOPT` / `SECURITY_FAST_TRACK` upstreams inside the runner's throwaway home, and
opens one pull request labelled `needs-owner-approval` with the report as its body (never auto-merged). Merging it is
the owner's approval for everyone who installs the plugin.
