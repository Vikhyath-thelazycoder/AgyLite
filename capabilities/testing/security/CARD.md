# testing/security — Security

Authn/authz, input validation, request and dependency checks; Semgrep/CodeQL runs and SARIF triage.

- **Use when:** security test, auth test, semgrep, codeql, sarif, static analysis, sast
- **Activation:** on-demand · priority 85 · context L2
- **Needs:** runtime os-native; network local-only; codebase analysis first
- **Loads:** 33 bundled files; entry points: codeql, sarif-parsing, semgrep, semgrep-rule-creator
- **Done means:** authn/authz and input-validation checks executed with results
- **Web QA class:** CORE
- **Related:** engineering/security · **Fallback:** —
