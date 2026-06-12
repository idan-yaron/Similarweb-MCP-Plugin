# § window-resolution, full rules (sw-foundation-data reference)

Windowed tools resolve relative date keywords server-side. Pass `start_date` and `end_date` as relative keywords (`latest`, `N_months_ago`, `N_days_ago`) directly to the real call: the server resolves them to concrete dates, clamps to its latest published month, and echoes the effective `start_date`/`end_date` plus `meta.last_updated` in the response. So recipes do NOT need a separate probe to resolve the window or learn freshness; the first real windowed call reports both. Live-grounded per `window-relative-keywords`.

Canonical pattern (no client-side date math):

- `end_date = "latest"` (server resolves to its latest published month).
- `start_date = "N_months_ago"`, where N is the recipe's window length (default 3), CLAMPED to the tool's cap (rule 4).

Passing `end_date: <today>` or any month beyond the latest published month returns `VALIDATION_ERROR / Dates not in range`. `latest` and relative keywords sidestep this server-side; never compute and pass `today`.

Rules:

1. Read the effective window and freshness from the first real call's `meta` (`meta.last_updated` plus the echoed `meta.request.start_date`/`end_date`). Use that `last_updated` for any client-side period math (period-over-period deltas) in the same turn.
2. If the user named a specific historical month, pass it as an explicit `end_date`; the server still clamps to its latest published month. If `meta` shows a clamp, add a Caveat: "end_date clamped to <meta.last_updated>; the server's latest published month is the ceiling." Otherwise prefer `latest`.
3. Default window length is rolling 3 months. Note `start_date="N_months_ago"` with `end_date="latest"` spans N+1 calendar months (both endpoints inclusive), so a 3-month window is `start_date="2_months_ago"`; a ~6-month window is `start_date="5_months_ago"`. Recipes may widen ONLY for tools without a 3-month cap.
4. **Capped tools.** `get-keywords-overview`, `get-keywords-seo-overview`, `get-websites-serp-players-agg`, `get-websites-keywords-competitors-agg`, and `get-websites-similar-sites-agg` cap the window at rolling 3 months. The server resolves the relative keyword FIRST and enforces the cap SECOND, so anything over 3 months 400s (and `3_months_ago` is already 4 months, so it is rejected). EXACT-SPAN SUBSET: `get-websites-keywords-competitors-agg` and `get-websites-similar-sites-agg` require the explicit span to be EXACTLY 3 months; a NARROWER explicit span also 400s ("must span exactly 3 month(s)", live-observed on similar-sites with a 1-month span). For those two, pass exactly `start_date="2_months_ago"` + `end_date="latest"`, or omit both dates and let the server default. For the other capped tools, `start_date="2_months_ago"` or narrower is fine. Per `window-relative-keywords`, `keywords-overview-3-month-max`, `keywords-competitors-exact-3-months`, and `similar-sites-window-constraint`.
5. **Single-month tools.** `get-websites-landing-pages-agg` with `granularity: "monthly"` accepts ONLY the most recent calendar month. Pass `start_date="latest"`, `end_date="latest"`, or use `granularity: "daily"` for the last 28 days. See `landing-pages-window-constraint`.
6. **Shopper/categories family.** The schemas for `get-categories-performance-agg` and the shopper siblings (`get-categories-top-brands-agg`, `get-categories-top-keywords-agg`, `get-keywords-top-brands-agg`, `get-keywords-top-products-agg`) document explicit `YYYY-MM` dates only, but the server resolves relative keywords there too (live-confirmed). Pass `start_date="N_months_ago"`/`end_date="latest"` as elsewhere; if the relative form is ever rejected, fall back to explicit `YYYY-MM` derived from a prior call's `meta.last_updated`. Per `window-relative-keywords`.

7. **Prior-period windows (period-over-period).** Derive the prior window with relative keywords, never client-side date arithmetic. For the default rolling 3-month current window (`start_date="2_months_ago"`, `end_date="latest"`), the prior window is `start_date="5_months_ago"`, `end_date="3_months_ago"`. General form for an N-month window: current = `(N-1)_months_ago` through `latest`; prior = `(2N-1)_months_ago` through `N_months_ago`. Both endpoints are inclusive, so always subtract N-1 (not N) when converting a month count to the start keyword; adding one extra month is the most common cause of "Dates not in range" and cap 400s.

Recipes whose first call has no date-range surface (e.g. sw-market-size's category-search) resolve dates only on their later windowed calls.
