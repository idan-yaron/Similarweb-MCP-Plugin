# Apps-shaped queries (sw-foundation-core catalog reference)

**Presence varies by account.** Resolve it per sw-foundation-core § tool-surface presence, from the live tool list at planning time, at zero data credits. This file describes what each tool DOES and what it COSTS; it makes no claim about whether your connector exposes it. Some accounts do not expose this family; if a call fails as unknown-tool, that is why, and the render is § error-rendering Pattern 7.

Grounded in `apps-tool-constraints` and `mcp-tool-catalog-v1`.

## Read this first: `app_id` must match `store`

The identifier and the store are one pair, not two independent parameters. Passing an id from one store with another store's value returns **HTTP 404 `NOT_FOUND` "Data not found"**, which reads exactly like a genuine no-data answer and is not one. Never report a 404 here as "this app has no data" without first checking the pairing.

- `store: "google"` takes a package name (`com.spotify.music`).
- `store: "apple"` takes a numeric id.
- `store: "unified"` takes the opaque hash that `get-apps-search` returns at `store: "unified"`, and only that.

`get-apps-search` returns ids in the shape of the store you asked it for, so search and analyse in the same store. Live-verified both ways on 2026-08-10.

**Store support differs per tool** and is enforced by the schema: retention and install-penetration are `google` only; ranks, ratings and audience-demographics take `google` or `apple` but not `unified`; downloads, active-users and sessions accept all three. Read the schema rather than assuming the family is uniform.

## Discovery

| Intent | Tool | Key params | Notes |
|--------|------|------------|-------|
| Find an app and get its id | `get-apps-search` | term, store, limit, search_in | 1 credit per returned row. Returns `{app_id, store, title, publisher_name, icon_small_url}`. The id shape follows `store`; see above. |
| App metadata | `get-apps-details` | store (required), app identifier per the live schema | 7 credits at the grounded shape. |

## App performance

Every tool below takes `app_id` plus `store`; most also require `country`. Pass an explicit window and an explicit `metrics` list where the schema offers one.

| Intent | Tool | Cost (at the shape measured) | Notes |
|--------|------|------------------------------|-------|
| Installs from the stores | `get-apps-downloads` | 1 credit per month (1 month = 1, 3 months = 3) | Only metric is `downloads`. |
| Active users | `get-apps-active-users` | 1 credit per month | Monthly granularity gives MAU, daily gives DAU. ONE field, no split inside a call, so stickiness needs two calls. |
| Session behaviour | `get-apps-sessions` | 1 credit per metric per month (5 metrics = 5, 1 metric = 1) | Five metrics available; unrequested ones return null. Trim the list, it is the cost lever. |
| Store revenue and ARPU | `get-apps-revenue` | 2 credits per metric per month (2 metrics = 4, 1 metric = 2) | Monthly only. Payload carries `revenue_flag: "estimated"`. **Never present as reported financials.** Often null on sparse coverage. |
| 30-day retention curve | `get-apps-retention` | **20 credits per month** (1 month = 20, 2 months = 40) | `store: "google"` only. Its schema has NO `metrics` parameter, so there is no lever except the window. The steepest per-month price in the family, and the window multiplies it directly; bound the window hard. |
| Store chart position over time | `get-apps-ranks` | **0 credits** | Daily. Rows per date x type x category x device, so multiple rows per app per date. **`limit` is ignored**, see the payload note below. |
| Ratings and their distribution | `get-apps-ratings` | 1 credit per metric per month (1 metric = 1) | `google` or `apple`. Seven metrics including the 1-to-5 distribution; unrequested ones return null. |
| Leaderboard for a category | `get-apps-top-charts` | **0 credits** | Takes NO `app_id`: a leaderboard keyed on `category_id` + `country` + `store`. Only those three are required; the server defaults `device` and `type` and echoes them in `meta.request`. **`limit` is ignored**, see below. |
| Audience age and gender | `get-apps-audience-demographics` | 1 credit per returned field (gender = 2, age = 5, both = 7) | FIVE age buckets and NO `_share` suffix, unlike the web demographics tools. Trim `metrics`, it is the cost lever. |
| Audience interests | `get-apps-audience-interests` | **0 credits** | Overlapping apps with `cross_usage` and `affinity` plus app metadata, sorted by `cross_usage`. Free, so reach for it early. |
| Install penetration | `get-apps-install-penetration` | 1 credit per month | `store: "google"` only. Single `install_penetration` field. |
| Category classification | `get-apps-iab-categories` | 1 credit per returned row (all versions = 7, `["v1"]` = 2) | Returns IAB v1, v2 and v3 rows, each `declared` or `inferred`. `iab_versions` is the cost lever. |
| SDKs detected in the app | `get-apps-technographics-sdks` | **30 credits, no lever** | The most expensive call in the family. `date` must be `YYYY-MM-DD`; the keyword `"latest"` is rejected. The window is locked to exactly the last 28 days and cannot be narrowed, and `limit` bounds the rows but NOT the price. Call it only when the SDK list is the actual answer. |

Costs above were measured on one app, one month, at the parameter shape named in each row. Treat the shape as part of the claim: change the metrics list, the row count or the window and re-measure rather than extrapolating.

**Two tools ignore `limit`.** `get-apps-top-charts` returns roughly 200 rows whatever limit you pass, and `get-apps-ranks` returns the same row set at any limit. Both are free in credits and neither is free in payload, so never inline a top-charts response on the assumption that a limit bounded it. Narrow `category_id` instead, or summarise rather than dumping rows.

## When the family is not exposed on a connector

Render § error-rendering Pattern 7 and offer the nearest website-side view, labelled for what it actually measures:

| App question | Website-side view | What changes |
|---|---|---|
| App audience demographics | `get-websites-demographics-agg` | Web visitors to the brand's site, not app users |
| App engagement | `get-websites-traffic-and-engagement` | Web sessions, not app sessions |
| App category leaders | `get-websites-top-sites-by-category-agg` | Web traffic rank, not store rank |

**Never equate the two.** App installs, store revenue and app sessions are different quantities from web visits, measured on a different panel. The pivot answers an adjacent question; it does not substitute for the app metric, and any render using it must say so.
