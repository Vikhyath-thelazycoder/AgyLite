# Research: a good and a weak report

Both answer the same question: "Should our Python service move from library A to library B for HTTP requests?"
The names, numbers and URLs below are made up to show the shape; a real report uses what the pages say.

## Weak

> # Library A vs Library B
>
> Both libraries are popular choices in the Python ecosystem. Library A is known for its simplicity and wide
> adoption, while Library B is a modern alternative with async support and better performance. Many developers
> are switching to Library B. In general, Library B is recommended for new projects, but Library A remains a
> solid choice. Ultimately, the best choice depends on your specific needs.
>
> Sources: official documentation, various blog posts, GitHub.

Why it is weak:

- Not one claim has a URL. "Sources: various blog posts" cannot be checked.
- "better performance" and "many developers are switching" have no number, no date and no source.
- It does not answer the question. "It depends on your needs" is where the research should start, not end.
- It could have been written without reading anything, and probably was.
- Nothing is marked as unverified, although nearly all of it is.

## Good

> # Should the billing service move from library A to library B?
>
> **Answer.** Not now. The service makes only blocking calls from worker threads, so B's main advantage (async)
> does not apply, and B changes two defaults that the service relies on. Revisit when the planned async rewrite
> starts.
> As of: 14 November 2026 · Sources read: 5
>
> ## Findings
> - B supports both sync and async clients; A is sync only.
>   [B documentation, "Async support"](https://example.org/b/async)
> - B does not follow redirects by default; A does. The service's payment-provider client depends on a redirect
>   (`billing/provider.py:44`). [B documentation, "Compatibility with A"](https://example.org/b/compat)
> - B has no default timeout difference worth noting: both require one to be set explicitly for production use.
>   [A documentation, "Timeouts"](https://example.org/a/timeouts)
> - B's maintainers state that its 1.0 release is not yet out and that minor versions may break the API.
>   [B repository README](https://example.org/b/readme)
>
> ## Where sources disagree
> - A benchmark post reports B as 30% faster for sync calls; B's own documentation makes no speed claim for sync
>   use. The post tests one endpoint on one machine. Treated as unverified.
>
> ## Unverified
> - Whether B's connection pool behaves the same under the service's thread count. No source tests it; it would
>   need a load test.
>
> ## Sources
> 1. B documentation, "Async support" — https://example.org/b/async — project docs
> 2. B documentation, "Compatibility with A" — https://example.org/b/compat — project docs
> 3. A documentation, "Timeouts" — https://example.org/a/timeouts — project docs
> 4. B repository README — https://example.org/b/readme — maintainers
> 5. "A vs B benchmark" — https://example.org/blog/bench — personal blog, March 2026

Why it is good:

- The answer is first, and it is an answer: not now, and when to look again.
- Each finding is one checkable fact with the page that owns it, and it is tied to the service's own code.
- The one performance claim comes from a weak source, and the report says so and does not repeat it as fact.
- What no source could settle is named, with what would settle it.
