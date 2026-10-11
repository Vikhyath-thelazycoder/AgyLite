# testing/release-verification — Release verification

Re-verify gates and evidence before claiming completion.

- **Use when:** verify complete, ready to ship, is it done, definition of done
- **Activation:** on-demand · priority 70 · context L2
- **Needs:** runtime node
- **Loads:** 4 bundled files; entry points: delivery-gate, verification-loop
- **Done means:** every gate re-verified on the final state
- **Web QA class:** CORE
- **Related:** engineering/completion · **Fallback:** —
