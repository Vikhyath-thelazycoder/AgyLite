# Upstream updates: how to see that they run

Agylite pins every upstream to a 40-character commit (`docs/audit/evidence/upstream-staging-snapshot.yaml`). New
upstream commits reach users only through a reviewed pull request.

- **Where to look.** GitHub → the repository's **Actions** tab → workflow **"Upstream updates"**. A healthy workflow
  shows a daily `check` run (scheduled) with jobs, and a weekly/monthly run that opens a pull request. A run named after
  the file path with **0 jobs** means GitHub could not load the workflow file: run `actionlint` on it.
- **What the pull request looks like.** One PR with the new pins (`upstream-staging-snapshot.yaml`, the inventories in
  `upstream-file-hashes/`), the regenerated extraction matrix, docs, notices and cards, and the test and benchmark
  results in its description.
- **Nothing reaches users until that PR is merged** and released: the plugin's engine follows the plugin version, and
  an engine only builds bundles from the pins in the version it installed.
- **On this machine,** `agylite doctor` → *Supply Chain* shows the oldest pin per tracking policy (warned after 14 days
  for `weekly`, 45 for `monthly` and `releases`, never for `manual`) and the date of the last `agylite update --latest`
  run, or "never".
