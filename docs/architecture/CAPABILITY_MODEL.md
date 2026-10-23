# Capability model

A capability is one unit of guidance or tooling the router can select, identified `domain/name`
(e.g. `engineering/security`). There are 63 in 9 domains.

## Source of truth

- `capabilities/<domain>/<name>/card.yaml` — the authored judgement fields (spec §13): name, description, intent tags,
  origin, runtime type, browser/network needs, context level, priority, security class, activation, verification
  requirements, dependencies, related, conflicts, fallback, enabled.
- `capabilities/<domain>/domain.yaml` — domain purpose and capability order.
- `config/priorities.yaml` — the conflict hierarchy (user requirements → project security → architecture →
  methodology → specialists → review → simplicity) and domain defaults.
- Generated, never authored: `capabilities/<domain>/<name>/CARD.md` (the L1 card, ≤ 1,000 bytes) and each bundle's
  `registry.yaml`, which adds provenance fields (source repositories, paths, commits, licenses, token estimate).

```bash
agylite registry list                  # every capability with mode, priority, bundled files
agylite registry show engineering/security --paths
agylite registry check                 # cards, CARD.md and the bundle's registry are valid and current
```

## States

- `enabled: false` cannot be routed; a `DISABLED_BY_POLICY` capability can never be enabled. Since D-049 browser
  verification is the enabled `testing/browser-verification` (and `testing/browser-qa` for gstack `/qa`); D-035's
  `testing/browser-exception` is gone.
- `engineering/simplicity` (Ponytail-derived) is explicit-only: it runs only when the user asks for it.

## Adding a capability

1. Write `card.yaml` and add the id to `domain.yaml`.
2. Map upstream files to it in `tools/audit/extraction-rules.yaml`.
3. `agylite registry cards` (renders CARD.md), seat it in `config/dashboard.yaml`, run the tests.
