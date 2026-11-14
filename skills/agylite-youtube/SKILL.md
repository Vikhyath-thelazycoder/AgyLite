---
name: agylite-youtube
description: YouTube creator work in the creator's own voice (scripts and hooks, titles and thumbnails, Shorts picks, edit decision lists, chapters, SEO, retention and outlier analysis, plans, comment replies), scored with the bundled tools — use when asked to write or improve a YouTube script, hook, title, thumbnail idea, chapters or description, or to analyse a video's or a channel's performance. Writes only.
disable-model-invocation: true
---

# Agylite YouTube

Produces written YouTube material (a script, a hook, titles, an edit list, chapters, an analysis or a plan) in
the creator's voice, with scores that come from running the tools. It never cuts, renders or uploads video, and
nothing here publishes: the skills write, the creator uploads.

## Use when · Not for

- Use when: scripts, hooks, titles and thumbnail ideas, Shorts picks, edit decision lists, chapters, video SEO,
  retention or outlier analysis, a content plan, replies to comments.
- Not for: a launch or demo video of a product → `agylite-media` · general web research → `agylite-research` ·
  website SEO → `agylite-seo`. Cutting or rendering video is not part of Agylite: offer the edit decision list
  (`yt-edit`) and the Shorts picks (`yt-shorts`) to apply in the creator's own editor.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>"` → `youtube/*`; load the routed skill whole (`agylite skill load ytagent/yt-<name>`)
  and follow it. It defines the method for its kind of work; this file says how Agylite runs it.
- **Voice.** `agylite youtube voice init` once; every skill reads `~/.agylite/youtube/voice.md`. While it is the
  unfilled template, ask for it (or for three of the creator's videos), or go on and mark the output
  **generic voice**.

## Steps

1. **Get the inputs** from research, not from memory:
   `agylite research video <url> --subs` (the transcript) and `agylite research channel <url> --swipe
   collected.json` (at least 4 videos per channel). Move on when: you hold the transcript or the data the task
   needs.
2. **Write** as the routed skill says, in the creator's voice.
3. **Score with the tools.** Run them; never estimate a score yourself:

   ```bash
   agylite youtube hookscore --hook "…"
   agylite youtube title --title "…" --thumb "…"
   agylite youtube deadair <transcript>
   agylite youtube chapters <transcript>
   agylite youtube retention <export.csv> [--transcript t]
   agylite youtube swipe <collected.json> --min 2.0
   ```

4. **Iterate.** Rewrite and score again as often as the routed skill asks. Keep each version with its score.
   Move on when: the skill's target is met, or you can show that further versions stopped improving.
5. **Deliver** the files in the project, and say where they are.

## Output

```markdown
<What was made> — <path of the file>
Voice: <the creator's voice.md | generic voice (voice.md is not filled in)>
Scores (from the tools): <tool: score for the final version; the versions tried and their scores>
Based on: <transcript, export or channel data used, with the URL or file>
For the creator to do: <what must be done by hand: record, cut, upload>
Not checked: <claims in the script that need the creator's confirmation>, or "None"
```

Then the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Every score in the answer is the output of a tool run in this session, for the exact text delivered.
- The hook and the title promise only what the video delivers. No claim the script does not back up.
- Timestamps, quotes and numbers come from the transcript or the export, not from memory.
- It sounds like the creator's voice file. Without one, the output is marked **generic voice**.
- No invented channel statistics, view counts, sponsors or audience facts.
- All the iterations the routed skill asks for were done, and the versions are shown with their scores.
- The answer does not say that a video was edited, rendered or uploaded.

## Stop and ask

- The voice file is the empty template and the creator has not said whether generic voice is acceptable.
- The script needs a fact about the creator, the product or a sponsor that you do not have.
- The request is to edit, render or upload video.

## When something fails

| What you see | What to do |
|---|---|
| No transcript is available for the video | Say so. Ask for the transcript or the script; do not write chapters or an edit list from the title. |
| `channel` returns fewer than 4 videos | The outlier analysis is not reliable. Say so and report what there is. |
| A tool is missing or errors | `agylite youtube status` shows the tools. Report the score as not available; do not make one up. |
| The score does not improve after several versions | Stop, show the versions and their scores, and say which you would use and why. |
| The retention export is in an unexpected format | Say which columns are missing and ask for the standard export. |

## References (read only when needed)

- `references/examples.md` — a good and a weak delivery of the same hook and title task, with notes.

End your answer with the output of `agylite used` (what this work used).
