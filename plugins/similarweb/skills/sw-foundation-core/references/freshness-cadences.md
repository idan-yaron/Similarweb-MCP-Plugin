# Freshness cadences (sw-foundation-core reference)

Cadences observed in production (subject to drift; re-grounded each release). `meta.last_updated` on each response remains the source of truth.

At the 2026-08-06 enumeration the latest published month across the website-analysis family was `2026-06` (`meta.last_updated: "2026-06-30"`), so a monthly-bucket answer trails the current date by one to two months. Say so in Caveats when the user asks for "this month".

| Bucket | Approximate cadence | Example tools |
|--------|---------------------|---------------|
| Daily | New rows arrive per day (inferred from the per-day news payload, not yet probe-confirmed; read `meta.last_updated`) | `get-sales-signals-news` [^news-payload] |
| Monthly | Updated at month boundary | `get-websites-traffic-and-engagement`, `get-website-analysis-traffic-channels`, `get-website-analysis-traffic-channels-share`, `get-website-analysis-search-spend`, `get-brands-sales-performance-agg`, `get-categories-performance-agg` [^cat-perf-window] |
| Monthly, published as a rolling 12-month coverage window | Month boundary; the describe tools report the exact window per country | `get-industry-demographics-age-distribution`, `get-industry-demographics-gender-shares`, `get-industry-unique-users` and their `-agg` and `-describe` siblings [^industry-window] |
| Monthly, with a hard 3-month request cap | Month boundary | `get-demand-search-trends` and its `-aggregated`, `-keywords`, `-keywords-aggregated` siblings [^demand-window] |

[^news-payload]: `get-sales-signals-news` returned 1.7 MB (2,587 lines) for a DEFAULT window on shopify.com. Always pin a narrow date window and treat the response as file-buffered, never inlined into context. Write the buffer under `$HOME/.similarweb-plugin/tmp/` or the platform temp dir, NEVER the working directory (a multi-megabyte third-party payload must not land in the user's project or git tree), and delete it in the same turn it is consumed.

[^cat-perf-window]: `get-categories-performance-agg` rolls its `meta.last_updated` monthly but its data window defaults to a 3-year aggregate (`2023-04-01` through last-completed-month), NOT a rolling 30-day window. Pass explicit `start_date` / `end_date` to override.

[^industry-window]: The free `get-industry-demographics-describe` and `get-industry-unique-users-describe` calls return the per-country available window (2025-07 through 2026-06 for every listed country at the 2026-08-06 probe) alongside the ~210-entry category vocabulary. Read the describe rather than assuming a window. That vocabulary uses tilde-separated two-level slugs (`Lifestyle~Fashion_and_Apparel`, plus a top-level `AI_Chatbots_and_Tools`) and is DISTINCT from the slash-separated display taxonomy `get-websites-website-rank` returns and from the numeric Amazon category IDs; see sw-foundation-data § category-vocabulary.

[^demand-window]: `get-demand-search-trends` caps a request at 3 months ("Currently, this endpoint supports only an interval of 3 month(s) of data") while its SERVER DEFAULT window is 12 months, which 400s. An explicit window is therefore mandatory on every call, and `country` is required. It charged 0 credits on a 3-month monthly window.

The near-real-time bucket that previously listed the `get-apps-*` active-users and downloads tools is retired: those names were absent from the live tool list at both the 2026-06-11 and the 2026-08-06 enumerations. See `references/apps-catalog.md`.
