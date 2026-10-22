---
name: research-video
description: YouTube transcripts, metadata, comments, search and channel lists through yt-dlp in the research runtime (agylite research video / video-search / channel); never downloads the video.
---

<!-- Agylite-authored (MP5 §1.4). Derived from Agent-Reach (Panniantong/Agent-Reach, MIT, "Agent Eyes")
skill/references/video.md, YouTube only, without Whisper/Groq transcription and the Chinese platforms. -->

# Video research (YouTube)

## Commands

```bash
agylite research video <youtube-url> --subs            # transcript with timestamps (manual subs, else auto-subs)
agylite research video <youtube-url> --meta            # title, channel, date, duration, views, chapters, description
agylite research video <youtube-url> --comments 50     # top comments (best-effort)
agylite research video-search "<query>" --n 5         # search YouTube
agylite research channel <channel-url> --n 30          # a channel's recent uploads (feeds youtube/analytics)
```

Files land in `~/.agylite/tmp/research/`; the command prints what the agent needs and the path of the full file.

## Retry chains (stop at the first that works)

- **No subtitles**: try `--meta` (the description and chapters often carry the outline) → read the video page with
  `agylite research read <url>` → say there is no transcript. Never transcribe audio: no Whisper, no paid API.
- **Auto-subtitles repeat lines**: YouTube's rolling captions duplicate text; `--subs` already removes repeated
  lines, so quote from its output, not from the raw `.vtt`.
- **Comments empty or failing**: comments are best-effort (YouTube throttles them); continue without them and say so.
- **"Sign in to confirm you're not a bot" / HTTP 429**: wait and retry once later in the task; do not loop.
- **Age-restricted or private video**: report it; never use a logged-in session or the user's cookies.

## Output

Quote with the video URL and the timestamp (`https://youtu.be/<id>?t=<seconds>`). Summaries say what the video says,
not whether it is true; check facts against primary sources (`research/web`). Findings go to
`docs/research/<slug>.md` with a source list.
