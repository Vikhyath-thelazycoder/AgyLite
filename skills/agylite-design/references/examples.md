# Design: a good and a weak final answer

Both are for the same request: "Build the landing page for our invoicing tool for freelancers. Inspiration:
two sites the owner likes."

## Weak

> I've created a modern, clean landing page with a stunning hero section, a features grid, testimonials from happy
> customers and a pricing table. It uses a sleek purple gradient inspired by the reference sites and is fully
> responsive. Here's a screenshot — I think it looks great!

Why it is weak:

- No DESIGN.md approval and no chosen direction: UI code was written before the owner decided anything.
- "modern, clean, stunning, sleek" describe nothing. Which direction is this, and for whom?
- "testimonials from happy customers" on a new product means invented quotes.
- "inspired by the reference sites" with their gradient may be their brand colour, which is identity.
- The only evidence is a screenshot and an opinion. No inspect, no lint, no verify.
- "fully responsive" names no width that was checked.

## Good

> Direction: D2 "Ledger" — for freelancers who distrust finance software: calm, exact, paper-like. Chosen by the
> owner from three options on 14 Nov.
> Sources: DESIGN.md approved by the owner, 14 Nov (palette and type kept; the first site's blue was shifted 24°
> in hue, see MERGE_NOTES.md; its commercial typeface replaced by an open one, recorded).
> Built: hero with a real invoice as the visual, "how it works" in three steps, pricing (2 plans), FAQ, footer.
> States: hover, focus and disabled on all buttons and links; the email field has error and success states.
> Widths: 1440 / 768 / 390.
> Checks: inspect 0 FAIL, 2 WARN (long FAQ answers at 390 px; hero image weight) · lint PASSED · design check
> PASSED · `agylite verify --inspect dist/index.html` PASSED (`.agylite/evidence/20261114T152210.json`)
> Deviations: None
> Not done: no testimonial section. The product has no customers yet, so there are no real quotes; the section is
> left out, not filled with invented ones. The two WARN items are listed for the owner to decide.
>
> *(output of `agylite used`)*

Why it is good:

- The direction has a name, an audience and a reason, and the owner picked it.
- What came from inspiration is stated, including what was changed so that no identity was copied.
- The states and the three widths are named, so they can be checked.
- The checks are commands with counts and an evidence file; the screenshot is not the proof.
- It says what it left out and why, and does not invent content to fill a section.
