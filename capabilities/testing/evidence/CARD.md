# testing/evidence — Evidence

Machine-readable verification evidence (command, suite, counts, result, artifact hash) written to the project's verification state.

- **Use when:** evidence, test results, verification evidence
- **Activation:** internal · priority 50 · context L1
- **Needs:** runtime os-native
- **Loads:** OS-native (no bundled files)
- **Done means:** every record states command, exit code and counts · "looks correct" or a screenshot alone is never evidence
- **Web QA class:** CORE
- **Related:** testing/local-verification, testing/release-verification · **Fallback:** —
