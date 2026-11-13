# Plan: move the CLI config from ~/.toolrc to ~/.config/tool/config.json

## Why

XDG paths are the norm, and JSON lets us add nested settings later.

## Steps

1. On startup, if `~/.config/tool/config.json` exists, read it; otherwise read `~/.toolrc` (`readConfig` already
   reads both locations).
2. Migrate: write the old keys (`token`, `region`, `telemetry`) to the new file, converting `telemetry` from the
   string "true"/"false" to a JSON boolean, then rename `~/.toolrc` to `~/.toolrc.bak`.
3. The migration follows the standard RTW rollout.
4. Handle any edge cases during migration as appropriate.

## Done when

The new file is used, and the old one is kept as `~/.toolrc.bak`.
