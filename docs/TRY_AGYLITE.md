# Try Agylite on a real build

A hands-on test. Another Claude Code session builds a small app and checks itself, then prints a report.
You paste that report into a chat in the Agylite repo for review. You are not testing the app. You are testing
whether Agylite routed the request, followed its lifecycle, verified with tests and recorded evidence.

## Your part (two steps)

1. Make an empty folder and open a **new Claude Code session** in it:
   ```bash
   mkdir -p ~/Developer/agylite-trial && cd ~/Developer/agylite-trial && code .
   ```
2. Paste the whole prompt below into that session. A browser tab opens with the Agent Office dashboard, where you
   can watch the agents work. When the session finishes, copy its **AGYLITE TRIAL REPORT** and paste it into the
   Agylite repo chat.

---

## Prompt to paste

````text
This is an Agylite trial. Do every step yourself, in order, in this folder. Do not skip steps or ask me to run
anything. If a command fails, record the exact error in the report and continue.

SETUP
1. Run: git init ; agylite doctor | tail -2 ; agylite project init --docs
2. Start the live dashboard in the background so I can watch:
   agylite dashboard --open --idle-minutes 60
   (keep it running; put its URL in the report)

BUILD — use Agylite for all of it
3. Task: a small Python command-line todo app in this folder. Commands: add "<text>", list, done <id>.
   Todos are saved to a local JSON file. Standard library only. Unit tests included.
4. Run agylite route "<the task>" first. Load only the routed capabilities with agylite context.
5. Follow the route's lifecycle exactly: UNDERSTAND → PLAN (agylite plan add-task P1 … --acceptance …) →
   IMPLEMENT (set-status IN_PROGRESS) → TEST → VERIFY (agylite verify, then READY_FOR_VERIFICATION) →
   RECONCILE (set-status VERIFIED --evidence <evidence file>).
6. No browser or screenshot verification. Local tests only.

AFTER-CHECKS — run each one and keep its real output
7. python3 <app file> add "buy milk" ; python3 <app file> list ; python3 <app file> done 1 ; python3 <app file> list
8. agylite verify
9. ls .agylite/evidence/
10. agylite plan show P1
11. agylite state
12. agylite events list | tail -20
13. agylite route "design a clean landing page for the todo app"     (record only the capability ids)
14. agylite route "run an SEO audit of my website"                    (record only the capability ids)
15. agylite route "make a 30 second launch video for the todo app"    (record only the capability ids)

REPORT — finish with exactly this block, filled in. Paste real command output; do not summarise it away.

=== AGYLITE TRIAL REPORT ===
Date/time:
Dashboard URL:
Doctor (step 1):
Route for the build (capability ids, browser, verification_mode):
Context loaded (which ids, roughly how many tokens/bytes):
Lifecycle steps done (each step + the command used):
Files created:
Step 7 app run output:
Step 8 verify output:
Step 9 evidence files:
Step 10 plan task + status:
Step 11 state:
Step 12 events (last 20):
Steps 13–15 routing ids:
Anything skipped, failed or surprising:
=== END REPORT ===
````

---

## What a good report looks like (for the reviewer)

- The build route has `engineering/*` and `testing/*`, `browser: disabled`, `verification_mode: local-test-first`.
- A P1 task was added **before** any code was written, and it ends **VERIFIED** with an evidence file.
- `agylite verify` shows `PASSED` with `failed=0`, and the app commands work.
- The events include route/capability selection, state updates and verification.
- Steps 13–15 each stay in one domain: only `design/design-direction`, only `seo/*`, only `media/launch-video`.
- A BLOCKING requirement question was answered with `agylite project answer` before the task started.
- Phase P1 ends VERIFIED with the evidence, and the events carry the session id.
