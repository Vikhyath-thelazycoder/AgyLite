# Routing: three routes and how to act on each

The route lines below are real output of `agylite route "<request>" --brief --existing`.

## 1. High confidence: act on it

Request: "Fix the payment webhook security."

```text
SECURITY_CHANGE · high (rules) · engineering/security, engineering/backend, testing/security,
testing/local-verification, codebase/impact-analysis + deps: testing/evidence, …
```

Good: tell the user `Route: SECURITY_CHANGE · engineering/security, engineering/backend, testing/security,
testing/local-verification · confidence high`, load those capabilities with the request text, run the `impact`
command first, and follow the lifecycle for a security change (it requires negative tests).

Weak: loading `engineering/security` only "because it is the main one", or adding `engineering/review` and
`engineering/architecture` "to be safe". The route is the minimum set; both changes make the result worse.

## 2. Low confidence: confirm first

Request: "Look into why messages per user are high."

```text
DESIGN_CHANGE · low (tags) · design/design-direction
```

Only a tag matched, and the match is wrong: this is a question about data or backend behaviour, not about design.

Good: "I read this as an investigation of why the messages-per-user number is high, in the backend or the data,
not a design task. Is that right? Which service or report shows the number?" Then route again with `--paths` once
the files are known.

Weak: loading the design capability and starting to redesign a screen, because the route said so. `low` means the
route is a guess that needs the user's confirmation.

## 3. Unmatched: say so and go on

Request: "Improve onboarding for new people."

```text
FEATURE_CHANGE · UNMATCHED · no capability fits; using principles only
```

Good: "No Agylite capability covers this request as written, so I will work from general principles. Do you mean
the onboarding screens in the app, or the onboarding document for new developers?" The answer usually makes the
next route match.

Weak: picking a capability that sounds close (documentation, UX) and loading it without saying that the route did
not match; or stopping and refusing to help.
