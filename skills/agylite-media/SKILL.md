---
name: agylite-media
description: Launch videos, demos and showcase material made from a project or a website with the bundled Brag workflow (brag-slim by default) — use when asked for a launch video, a demo video, a product showcase or a short clip that presents a project.
disable-model-invocation: true
---

# Agylite Media

Produces a short video of the real product with its poster frame and share text, made with the bundled Brag
workflow. It shows only what the product has, and its output is a deliverable: a rendered video is never a test
of the product.

## Use when · Not for

- Use when: a launch video, a demo, a showcase clip or presentation material for a project or a website.
- Not for: a YouTube script, title or edit list → `agylite-youtube` · a diagram → `agylite-diagrams` · the UI
  itself → `agylite-design` · proving that the product works → `agylite-testing`. No backend or SEO capability is
  involved.

## Before you start

- **Route.** If the prompt arrived with an `Agylite route:` line, the route is done. Otherwise
  `agylite route "<request>"` → `media/*` only.
- **Input.** The project directory or the website to present. Know the one thing the video should make a viewer
  understand; ask when the request does not say.

## Steps

1. **Plan.** `agylite media plan`. Expect: `mode` (`brag-slim` by default; the full `/brag` only with `--full` and a
   locally installed Hyperframes), the `tools` found (ffmpeg, node, python), `missing`, the `output_dir`
   (`brag-output/`) and a `load` line. Move on when: `missing` is empty, or the user knows what is missing.
2. **Load the workflow.** Run the plan's `load` command with the request added:
   `agylite context --request "<the user's request>" --file files/brag/skills/…`. Follow that workflow from here:
   it defines the story, the tones, the creative laws, the build and the render. This file does not repeat them.
3. **Inspect the real product first**, as the workflow says: what it does, what it looks like, what is worth
   showing. Move on when: every scene you plan shows something that exists.
4. **Build, check, render** as the workflow says. Look at stills from every scene and from mid-transition before
   the full render.
5. **Music cues (optional).** `agylite runtime install brag` once, then `agylite media music-cues <audio>`.
6. **Check the file.** `ffprobe brag-output/brag.mp4` (or the timestamped output folder): duration, resolution and
   an audio stream. Play it once from start to end.

## Output

```markdown
Video: <path of brag.mp4> — <duration> s, <width>×<height>, <with | without> audio
Poster: <path of brag.jpg>
Share text: <path of share-copy.txt>
Angle: <one sentence: what the video makes a viewer understand>
Shown: <the product features or screens that appear, each real>
Not shown or not real: <anything staged, mocked or left out, and why>, or "None"
Workflow: <brag-slim | brag --full>; intermediate files in <output folder>/work/
```

Then offer to redo one scene or try another tone, and end with the output of `agylite used`.

## Quality bar

Check each line before you answer:

- Everything shown exists in the product today. No invented feature, screen, number, customer or quote.
- The first two seconds carry the hook; the length is what the workflow or the user asked for (about 20 seconds
  by default).
- You looked at stills from every scene and from mid-transition: no overflowing text, no collisions, no
  low-contrast text.
- The duration, resolution and audio in the answer come from `ffprobe`, not from the plan.
- The poster is a settled frame (text fully in), and the share text is specific to this product.
- The video is not offered as evidence that the product works.

## Stop and ask

- A tool is missing and has to be installed, or the full workflow needs Hyperframes.
- The video would need real customer names, logos, quotes or numbers that you do not have.
- The product cannot be run or opened, so there is nothing real to capture.

## When something fails

| What you see | What to do |
|---|---|
| `media plan` lists `missing` tools | Name them. Ask before installing; do not switch to a different workflow silently. |
| `--full` is asked but Hyperframes is not installed | Say so and offer brag-slim. |
| The render fails or the file does not play | Report the error and the last step that worked. Do not deliver a broken file. |
| `brag-output/` already exists | The workflow writes a timestamped folder. Give that path. |
| `music-cues` is not available | `agylite runtime install brag` when the user agrees; the video works without it. |

## References (read only when needed)

- `references/examples.md` — a good and a weak delivery of the same launch video, with notes.

No MCP. End your answer with the output of `agylite used` (what this work used).
