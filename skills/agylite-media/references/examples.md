# Media: a good and a weak delivery

Both are for the same request: "Make a launch video for our CLI tool that finds unused dependencies."

## Weak

> Your launch video is ready! It's an exciting, professional 60-second video showcasing the tool's powerful
> features, including the AI-powered analysis dashboard and its 10x speed improvement, with testimonials from
> developers who love it. Check out `video.mp4`!

Why it is weak:

- A CLI tool has no "analysis dashboard", and nothing measured a "10x speed improvement". Both are invented.
- "testimonials from developers who love it" are invented quotes.
- 60 seconds is three times the workflow's length, and nothing says the user asked for it.
- No resolution, no poster, no share text, and no sign that the file was probed or played.
- "exciting, professional, powerful" describe the wish, not the video.

## Good

> Video: `brag-output/brag.mp4` — 20.0 s, 1920×1080, with audio
> Poster: `brag-output/brag.jpg`
> Share text: `brag-output/share-copy.txt`
> Angle: one command shows the dependencies you are paying for and not using.
> Shown: the real terminal run on this repository (`depcheck-lite scan`, 14 unused packages found, 2.1 s), the
> `--fix` flag removing them, and the before and after size of `node_modules` (412 MB → 287 MB) from that run.
> Not shown or not real: the CI integration, because it is not built yet. The terminal recording is sped up 2×
> and says so on screen.
> Workflow: brag-slim; intermediate files in `brag-output/work/`
>
> I can redo the opening two seconds or try a drier tone. Which would you like?
>
> *(output of `agylite used`)*

Why it is good:

- Every number comes from a real run of the tool on a real repository.
- What does not exist yet is left out, and the one edit to reality (the speed-up) is stated.
- The duration and resolution are the probed values of the delivered file.
- The angle is one sentence a viewer could repeat.
