# SEO: a good and a weak audit

Both are for the same request: "Audit our shop's website. Organic traffic to the product pages has dropped."
The numbers and URLs below are made up to show the shape; a real audit uses what the capture shows.

## Weak

> ## SEO Audit Results
>
> Your site has several SEO issues that are hurting your rankings:
>
> - Missing meta descriptions on many pages
> - Page speed could be improved
> - Content is thin and should be expanded with relevant keywords
> - No structured data
> - Build more high-quality backlinks
>
> Fixing these issues will significantly improve your organic traffic. The traffic drop was caused by the recent
> Google algorithm update.

Why it is weak:

- No page is named and no number is given. "many pages" could be 2 or 200.
- It reads like a checklist that fits any site. Nothing shows that these items are this site's problem.
- "The traffic drop was caused by the algorithm update" is a guess stated as fact. A crawl cannot show that.
- "No structured data" may mean that it was not found on pages that failed to load.
- "expand content with relevant keywords" and "build backlinks" are not fixes anyone can carry out.
- The question (why the product pages dropped) is not answered.

## Good

> ## SEO: shop.example — why product pages lost organic traffic
>
> Captured: 212 pages on 14 Nov; failed or partial: 9 (the `/account/…` pages need a login)
>
> ### Findings (most important first)
> 1. **FACT** 148 of 160 product pages carry `<meta name="robots" content="noindex">`.
>    - Evidence: for example `shop.example/p/oak-desk`; the tag is in the page head of every page that uses the
>      `product.html` template. Category pages and the home page do not have it.
>    - Effect: these pages are asking search engines to drop them. This alone can explain the fall.
>    - Fix: remove the tag from `templates/product.html`. The 12 product pages without it use the old
>      `product-legacy.html`.
> 2. **OBSERVATION** 61 product pages share one title, "Product – Shop".
>    - Evidence: `shop.example/p/oak-desk`, `/p/pine-shelf` and 59 more in the run's report.
>    - Effect: search results cannot tell the pages apart.
>    - Fix: build the title from the product name in `templates/product.html`: `{{ product.name }} – Shop`.
> 3. **HYPOTHESIS** The noindex tag arrived with the template change in October.
>    - Evidence: none in the capture; a crawl shows the present only. The repository history of
>      `templates/product.html` would confirm or refute it.
>
> ### Could not be inspected
> - The 9 account pages (login required). They are not meant to rank.
>
> ### Not in this audit
> - Ranking and traffic figures (no search console access), backlinks, page speed.

Why it is good:

- The first finding answers the question, with a count, an example page and the template that causes it.
- Each finding has its label. The guess about when it happened is marked as a hypothesis, with what would settle it.
- The fixes name the file and the change.
- Pages that could not be read are listed as such, and nothing is concluded about them.
