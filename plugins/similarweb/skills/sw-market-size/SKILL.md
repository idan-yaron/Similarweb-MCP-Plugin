---
name: sw-market-size
description: Market size profile for a category or keyword cluster. Use when the user asks about market size, total addressable market, category sizing, top brands in a category, or share of voice within a vertical. The MCP exposes categories as two disjoint flows. The Amazon shopper flow uses a numeric ID plus an Amazon TLD and offers rich analytics. The Web industry flow uses a PascalCase slug plus an ISO country and offers only domain plus rank. They do not translate. Recipe defaults to the Amazon flow for richer sizing, treats Web as an opt in companion, and falls back to Web only with a caveat when no Amazon match exists. Delegates capability gating, citations, error rendering, and handoff JSON to sw foundation. Never fabricates total click math.
---
# sw-market-size

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations
- sw-foundation-render: § handoff-json-schema (when intent=handoff)

## Hard rules (NEVER violate)

- NEVER auto-pick `data[0]` from `get-categories-search`. Resolution is ambiguous (99 hits for `"technology"` in T11 probe), and the first row may be a Books subcategory instead of the intended retail category. Disambiguate by presenting top matches at shallowest `category_depth` in retail-relevant root trees, OR accept a `category_id` directly. See `tests/grounded/categories-search-resolution.md`.
- NEVER pass `country` to `get-categories-search`. The schema does not accept it; categories are Amazon-domain-scoped (6-entry TLD enum). To get country-specific Amazon demand, pass `domain: "amazon.de"` instead of `country: "de"`.
- NEVER pass `query` to `get-categories-search`. The actual parameter is `search_term`; the docstring is wrong.
- NEVER translate an Amazon `category_id` to the Web `category` slug or vice versa. They are completely disjoint enums. Amazon ID `10048700011` returns `400 VALIDATION_ERROR: Selected category is not supported.` from `get-websites-top-sites-by-category-agg`. The two surfaces are bridged ONLY by matching the user's free-text input independently against each enum.
- NEVER fabricate `total_clicks` as the sum of all 4 click-breakdown fields. The empirical equation is `total_clicks = category_paid_clicks + category_organic_clicks` ONLY. `brand_paid_clicks` and `brand_organic_clicks` are a parallel attribution dimension (which brand the click landed on), NOT additive to category clicks. See `tests/grounded/categories-performance-shape.md`.
- NEVER fabricate a single "market share" without committing to a basis. Commit to `revenue_share` as the canonical metric; render `total_views_share` and `units_sold_share` as adjacent columns for transparency. Top-10 sums to ~80% of revenue, ~64% of views, ~36% of units sold (long tail differs by basis).
- NEVER conflate `top_brand` (winner of clicks for the keyword) with `associated_brand` (brand the keyword refers to; null when non-branded). For `"smart watch"`, `associated_brand = null` and `top_brand = "SAMSUNG"`. Render both columns and footnote the distinction.
- NEVER claim `get-websites-top-sites-by-category-agg` returns a "market size" or any traffic number. It returns ONLY `{domain, rank}` per row. To get visits, fan out into `get-websites-traffic-and-engagement` per domain (expensive, capability-gated, opt-in via `--enrich-traffic`).
- NEVER assume a `rank` field on `-agg` rows. Top-brands and top-keywords are pre-sorted server-side; order IS rank. Add `rank = i+1` client-side.
- NEVER trust the docstring's "last 28 days" default window. Empirical default for every `-agg` variant probed in T11 is 3 years (`2023-04-01` through last-completed-month). Document the actual window from `meta.request`.
- NEVER attempt Web subcategory slugs with `/` (e.g. `Computers_Electronics_and_Technology/Search_Engines`). Returns `400 VALIDATION_ERROR` even for hierarchies the Similarweb web UI exposes. Top-level slugs only.
- NEVER allow `--enrich-traffic` without `--web-companion`. Exit with usage hint.

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reference prior findings in cross-reference lines (rank/competitor reuse is rare for sw-market-size since the flow is category-keyed, but a prior recipe's window or surfaced competitor set may still inform the audience-overlap NEXT MOVES). If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

`COUNTRY` is used ONLY by the `--web-companion` flow; the Amazon flow uses `--amazon-tld` instead.

```bash
INPUT="<first positional arg, free text>"     # e.g. "wearable technology", "cybersecurity"
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
AMAZON_TLD="${AMAZON_TLD:-amazon.com}"         # enum: amazon.com | amazon.co.uk | amazon.it | amazon.fr | amazon.de | amazon.ca
AMAZON_TLD="${AMAZON_TLD,,}"
WEB_COMPANION="${WEB_COMPANION:-false}"
ENRICH_TRAFFIC="${ENRICH_TRAFFIC:-false}"
if [ -z "$INPUT" ]; then
  echo "Usage: /sw-market-size <category-or-keyword-cluster> [--country <iso-2>] [--amazon-tld <tld>] [--web-companion] [--enrich-traffic]"; exit 1
fi
if [ "$ENRICH_TRAFFIC" = "true" ] && [ "$WEB_COMPANION" != "true" ]; then
  echo "--enrich-traffic requires --web-companion"; exit 1
fi
case "$AMAZON_TLD" in
  amazon.com|amazon.co.uk|amazon.it|amazon.fr|amazon.de|amazon.ca) ;;
  *) echo "Invalid --amazon-tld; allowed: amazon.com, amazon.co.uk, amazon.it, amazon.fr, amazon.de, amazon.ca"; exit 1 ;;
esac
```

## Step 2: smoke-first probe + lazy capability gating (MANDATORY)

Per sw-foundation-core § smoke-first sequencing AND § capability-gating:

1. **Smoke (one call, sequential)**: `get-categories-search`, `domain=$AMAZON_TLD`, `search_term=$INPUT`. Wait. No other call yet. On 200, cache and go to 2A. On 403, secondary probe `get-categories-performance-agg` (`domain=$AMAZON_TLD`, `category="1"`, smallest window); if also 403, render § error-rendering Pattern 5 and STOP; if 200, abort with Caveat "Cannot resolve category without `get-categories-search`; pass a numeric category ID, or pivot to `--web-companion`." Other error: retry once; if still failing, mark fragile-this-run and proceed.
2. **2A**: apply § capability-gating using the smoke result plus any persisted entries. Per-call denial via § error-rendering pattern 3, appended to `tools_inaccessible` at end of run.

REQUIRED (Amazon flow):
- `get-categories-search`
- `get-categories-performance-agg`
- `get-categories-top-brands-agg`
- `get-categories-top-keywords-agg`

OPTIONAL (Amazon flow, downgrade gracefully if absent):
- `get-categories-sales-performance-agg`

REQUIRED for `--web-companion`:
- `get-websites-top-sites-by-category-agg`

OPTIONAL for `--web-companion --enrich-traffic`:
- `get-websites-traffic-and-engagement`

If `--web-companion` was supplied but `get-websites-top-sites-by-category-agg` is not accessible, skip the Web companion section and note in Caveats: "Web companion not accessible on this plan; Amazon shopper sizing only."

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. sw-market-size is single-category, so this rarely fires. If the conversation contains a list of categories or keyword clusters and the user did not pin one, ask which one to size (single confirmation).

## Step 4: Plan the call sequence

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `get-categories-search` | Resolve user input to an Amazon `category_id`. Params: `domain` = `$AMAZON_TLD`, `search_term` = `$INPUT`. NO `country`, NO `query`. Returns up to ~100 ambiguous matches. Recipe MUST disambiguate. |
| 2 | `get-categories-performance-agg` | Total Amazon demand for the resolved category. Single row, 6 metrics, 3-year default window. Params: `domain`, `category` (numeric ID from Step 1). |
| 3 | `get-categories-top-brands-agg` | Top 10 brands pre-sorted by revenue desc. Params: `domain`, `category`, `limit: 10`. Optionally pass `metrics: ["revenue_in_usd","revenue_share","total_views_share","units_sold_share","conversion"]` to cut cost. |
| 4 | `get-categories-top-keywords-agg` | Top 10 keywords pre-sorted by `keyword_total_clicks` desc. Params: `domain`, `category`, `limit: 10`. |
| 5 (if accessible) | `get-categories-sales-performance-agg` | Optional sales-perf cut. Params: `domain`, `category`. |
| 6 (if `--web-companion`) | `get-websites-top-sites-by-category-agg` | Web industry leaderboard. Params: `category` (PascalCase slug matched from user input against hardcoded list), `country` (ISO-2), `limit: 10`. Returns ONLY `{domain, rank}` per row. |
| 7 (if `--web-companion --enrich-traffic`) | `get-websites-traffic-and-engagement` | Looped per ranked domain from Step 6 (up to 10 calls). Returns visits + engagement metrics. Expensive: ~10-20 data credits per domain. |

Hardcoded Web slug list (top-level only, case-sensitive, confirmed working in T11 probe):
`Computers_Electronics_and_Technology`, `Health`, `Finance`, `Sports`, `News_and_Media`, `E-Commerce_and_Shopping`. If user input does not match exactly, the recipe asks one disambiguation question with the closest 3-5 slugs from the list.

## Step 5: Execute

Step 1 runs first. From its response:
- If 0 nodes returned: Amazon flow fails. If `--web-companion` was supplied, run only Steps 6 (and optionally 7); render with Caveat "Amazon shopper data not available for this category; running Web-industry leaderboard only." If `--web-companion` was NOT supplied, ask the user once: "No Amazon match for `<input>`. Want to try a different search term, or run this as a Web-industry leaderboard instead?".
- If 1+ nodes returned: disambiguate. Sort by `category_depth` ascending; prefer retail-relevant root trees in this order: `Electronics`, `Toys & Games`, `Sports & Outdoors`, `Home & Kitchen`, `Health & Household`, `Beauty & Personal Care`. Skip `Books > Children's Books > ...` and other educational/book subtrees unless the user explicitly typed `"books"` or a book-related term. If the top match by these heuristics is unambiguous AND its `category_path` reasonably matches the user input, proceed. Otherwise, present the top 5 matches to the user with their `category_path` + `category_depth` and ask them to pick.

Steps 2, 3, 4 are independent given the resolved `category_id`; parallelize. Step 5 is independent and can join the parallel batch. Step 6 (if `--web-companion`) is independent of Steps 2-5 and can run in parallel. Step 7 (if `--enrich-traffic`) loops per domain after Step 6 completes; parallelize within the loop.

Client-side derivations after responses arrive:
1. Add `rank = i+1` to each top-brands row.
2. Add `rank = i+1` to each top-keywords row.
3. Compute `top_5_revenue_share = sum(revenue_share for first 5 brands)`.
4. Compute `top_10_revenue_share = sum(revenue_share for first 10 brands)`.
5. Compute HHI from top-10 `revenue_share` values: `hhi = sum(s * s for s in revenue_shares) * 10000`. Note: top-10 covers only ~80% of revenue, so HHI is an underestimate (call this out in the rendered section).
6. Verify the click identity from Step 2: `total_clicks == category_paid_clicks + category_organic_clicks`. If the identity fails by more than 1 unit (rounding), flag with `[!gap]` in the rendered output (the assumption from T11 grounding has shifted).

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, sw_coins, last_updated}`. Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped. For Step 6, distinguish `400 VALIDATION_ERROR` (unrecognized slug; ask the user to re-pick from the hardcoded list) from `404 NOT_FOUND` (recognized slug but no data for the country+window; report empty Web companion section with Caveat).

## Step 5.5: Brand-family consolidation check

Run AFTER Step 3 resolves top-brands but BEFORE rendering. Scan for parent-brand family memberships from the list below. If 2+ brands in top-N belong to the same parent, surface a `## Brand-family consolidation` subsection AFTER the top-brands table (parent / constituents / consolidated `revenue_share` + `revenue_in_usd`). If no matches, omit.

Recognized brand-families (heuristic):

| Parent | Constituent brands |
|--------|--------------------|
| Apple | Beats, Apple |
| Alphabet (Google) | Google, YouTube, Fitbit, Nest |
| Meta | Facebook, Instagram, WhatsApp, Oculus |
| Amazon Inc. | Amazon, Ring, Eero, Audible, Kindle, Whole Foods |
| Microsoft | Microsoft, LinkedIn, GitHub, Activision-Blizzard, Xbox, Surface |
| Adobe | Adobe, Figma |
| Samsung | Samsung, Harman Kardon, JBL, AKG |
| Sony | Sony, Bose-via-Sony (where applicable), PlayStation |
| Procter & Gamble | Gillette, Oral-B, Pampers, Tide |
| Unilever | Dove, Axe, Ben & Jerry's, Hellmann's |
| L'Oréal | Maybelline, NYX, La Roche-Posay, CeraVe |
| Estée Lauder | MAC, Clinique, La Mer, Bobbi Brown |
| Inditex (Zara) | Zara, Pull&Bear, Bershka, Massimo Dutti |
| LVMH | Louis Vuitton, Dior, Tiffany & Co., Sephora |

Matching: case-insensitive substring or exact-brand match; require 2+ matched constituents in the top-N for a parent to count as "consolidated". Computation: `consolidated_revenue_share = sum(revenue_share for matched)`, `consolidated_revenue_usd = sum(revenue_in_usd for matched)`.

The list is intentionally narrow; document its scope in the rendered subsection. If the category has obvious parent-brand structure not covered above, suggest the user inspect the top-brands table manually.

## Step 6: Classify output intent

Per sw-foundation intent-aware output rendering rules. Default: narrative.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Body output target ~3000-4000 chars (dual-surface justifies size).

**Header (FIRST line of output, ONE italic line):** `*{category_path} | {AMAZON_TLD} | {window} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Top brands by revenue_share:** Unicode top-N horizontal bars (top 5-10 brands; cumulative top-5 % rendered below). Replaces Mermaid pie. If Step 5.5 surfaced consolidation, render a parent-rollup top-N bar set adjacent.
- **HHI concentration:** Unicode threshold-position bar with FRAGMENTED / MODERATE / CONCENTRATED markers at 1500 and 2500.

Sections in order:

- `## Executive read` (numbers-LIGHT, max 3 sentences. Lead with HHI verdict label from sw-foundation-render § expert-heuristics (`FRAGMENTED` / `MODERATE` / `CONCENTRATED`); name ONE most-important finding (consolidated-leader revenue_share when Step 5.5 fired, else raw top brand). If --web-companion succeeded, name the #1 Web domain in the same paragraph. When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Category metadata` (table: `Field` / `Value`. Rows: `Resolved category`, `Amazon category_id`, `category_path`, `category_depth`, `parent_category_name`, `Amazon TLD`, `Search term`. If --web-companion succeeded: also `Web slug` and `Web country`.).
- `## Total demand` (table from Step 2 response. Rows: `search_volume`, `total_clicks`, `category_paid_clicks`, `category_organic_clicks`, `brand_paid_clicks`, `brand_organic_clicks`. Window cited above the table from `meta.request.start_date` and `meta.request.end_date`. Footnote: "`total_clicks = category_paid_clicks + category_organic_clicks`. Brand-attribution clicks (`brand_paid_clicks` + `brand_organic_clicks`) are a parallel rollup of who won the click; NOT additive to total_clicks.").
- `## Top brands` (table from Step 3 response. Columns: `Rank`, `Brand`, `Revenue share`, `Total views share`, `Units sold share`, `Revenue (USD)`, `Conversion`. Use `revenue_in_usd` for the revenue column. Shares rendered as percent to 2 decimal places. Footnote: "Top 10 covers ~80% of category revenue; long tail not surfaced. `revenue_share` is the canonical market-share metric used for concentration math; `total_views_share` and `units_sold_share` shown as orthogonal alternatives.").
- `## Brand-family consolidation` (ONLY if Step 5.5 found at least one parent with 2+ matched constituents in the top-N. Columns: `Parent`, `Constituents`, `Consolidated revenue share`, `Consolidated revenue (USD)`. Sort rows by `Consolidated revenue share` descending. Footnote: "Heuristic match against a curated list of well-known consumer-tech and CPG parent-brand families. Not exhaustive; analysts should inspect the top-brands table manually for category-specific groupings (private label, regional holding companies, recent acquisitions).").
- `## Top keywords` (table from Step 4 response. Columns: `Rank`, `Keyword`, `Total clicks`, `Avg price (USD)`, `Branded type`, `Associated brand`, `Top brand (winner)`, `Top brand share`. Render `associated_brand = null` as `n/a`. Footnote: "`top_brand` is the brand winning the most clicks for the keyword, NOT the brand owning the keyword. For non-branded queries, top_brand may differ from any associated brand. `top_brand_share` is fraction of clicks on this keyword won by the top brand.").
- `## Concentration` (HHI from top-10 `revenue_share`, top-5 cumulative `revenue_share`, top-10 cumulative `revenue_share`. **Apply the market concentration label per sw-foundation-render § expert-heuristics**: `HHI < 1500` -> `FRAGMENTED` (room to enter); `1500 <= HHI < 2500` -> `MODERATE`; `HHI >= 2500` -> `CONCENTRATED` (entrenched incumbents). The label becomes the first word of the verdict line. Footnote: "HHI computed from top-10 only; absolute HHI is higher when the long tail is included. Threshold labels per sw-foundation-render § expert-heuristics.").
- `## Sales performance` (only if Step 5 returned data; render the response as-returned).
- `## Web companion` (only if `--web-companion` AND Step 6 returned data. Subsections: `Matched slug` (line: "Slug: `<slug>`, country: `<country>`"), then top-sites table from Step 6 with columns `Rank`, `Domain`. If `--enrich-traffic` AND Step 7 returned data, additional `## Traffic enrichment` subsection: one row per top domain with `Visits`, `Pages per visit`, `Avg visit duration`, `Bounce rate` columns from `get-websites-traffic-and-engagement`. Note total looped cost.).
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the strongest signal in the render:
  - **Competitive teardown of the top brand** (use consolidated parent apex when Step 5.5 fired):
    `"How does <top-brand>.com stack up against <2nd-brand>.com and <3rd-brand>.com?"`
    followed by one sentence on head-to-head sizing of category leaders.
  - **AEO audit of the consolidated parent or #1 brand**:
    `"Is <leader>.com showing up in AI answers for the <category> space?"`
    followed by one sentence on testing whether the leader's AEO posture matches its category dominance.
  - **Audience overlap among top brands** when the leader pool looks like one pond:
    `"What's the audience overlap between <top-1>, <top-2>, and <top-3>?"`
    followed by one sentence on duplication vs incremental reach across the top of the category.

  If `--web-companion` succeeded AND the #1 Web domain differs from the top Amazon
  brand's apex, prefer the audience-overlap question for the second bullet, asking
  `"What's the audience overlap between <top_amazon_brand>.com and <top_web_domain>?"`
  with one sentence on how the Amazon shopper population differs from the broad-web population.)
- `## Caveats` (per sw-foundation-render § error-rendering, only if any tool returned null / was unavailable / was skipped / fell back to web-only mode / disambiguation took place / a Web slug mapping was ambiguous).
- `## Sources` (collapsible). Last element of the output unless `intent=handoff`.
- `[optional] ## Handoff` (JSON, only when intent=handoff).

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-market-size handoff

```json
{
  "category": {
    "amazon": {
      "id": "<numeric string>",
      "name": "<category_name>",
      "path": "<category_path>",
      "depth": 0,
      "parent_category_id": "<numeric string>",
      "parent_category_name": "<name>",
      "amazon_tld": "amazon.com",
      "resolved_from": "<user input>",
      "search_term": "<actual search_term passed>"
    },
    "web_slug": null
  },
  "performance": {
    "search_volume": 0,
    "total_clicks": 0,
    "category_paid_clicks": 0,
    "category_organic_clicks": 0,
    "brand_paid_clicks": 0,
    "brand_organic_clicks": 0,
    "window": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "note": "3-year default unless explicit dates passed"}
  },
  "top_brands": [
    {"rank": 0, "brand": "<name>", "revenue_share": 0.0, "total_views_share": 0.0, "units_sold_share": 0.0, "revenue_in_usd": 0, "conversion": 0.0}
  ],
  "top_keywords": [
    {"rank": 0, "keyword": "<text>", "keyword_total_clicks": 0, "keyword_average_price": 0.0, "branded_type": "Branded|Non-Branded", "associated_brand": "<name>|null", "top_brand": "<name>", "top_brand_share": 0.0}
  ],
  "concentration": {
    "hhi_from_top_10": 0.0,
    "top_5_revenue_share": 0.0,
    "top_10_revenue_share": 0.0,
    "note": "HHI from top-10 rows only; absolute HHI is higher with the long tail"
  },
  "brand_family_consolidation": null,
  "sales_performance": null,
  "web_companion": null
}
```

`brand_family_consolidation` is `null` by default. It is populated by Step 5.5 ONLY when at least one recognized parent has 2+ matched constituents in the top-N. Shape when populated:

```json
{
  "<parent>": {
    "constituents": ["<brand>", "<brand>"],
    "consolidated_revenue_share": 0.0,
    "consolidated_revenue_usd": 0
  }
}
```

Keys are parent names; values carry the matched constituent list (subset of the top-N brands) and the summed shares/revenue. Heuristic match per the recognized-families list in Step 5.5; not exhaustive.

Field semantics:
- `category.web_slug` is `null` unless `--web-companion` succeeded.
- `performance.window.note` records that the default window is 3-year aggregate per T11 grounding, NOT 28 days as the docstring claims.
- `top_brands` rows pre-sorted by revenue desc as returned; `rank` is the client-side `i+1`.
- `top_keywords` rows pre-sorted by `keyword_total_clicks` desc; `associated_brand` may be `null`.
- `concentration.hhi_from_top_10` computed as `sum(revenue_share ** 2) * 10000` over the top-10 rows.
- `sales_performance` is `null` unless Step 5 was accessible AND returned data.
- `web_companion` is `null` unless `--web-companion` was supplied AND Step 6 returned data. Shape when populated:

```json
{
  "slug": "<matched PascalCase slug>",
  "country": "<iso-2>",
  "top_sites": [{"rank": 1, "domain": "<domain>"}],
  "traffic_enrichment": null
}
```

`traffic_enrichment` is `null` unless `--enrich-traffic` was supplied AND Step 7 returned data. Shape when populated: a list keyed by domain with `visits`, `pages_per_visit`, `avg_visit_duration`, `bounce_rate` from `get-websites-traffic-and-engagement`.

## Edge cases

- **Input does not resolve to an Amazon category** (Step 1 returns 0 nodes): if `--web-companion` was supplied, fall back to Web-only mode and note in Caveats. If not supplied, ask once: "No Amazon match for `<input>`. Want to try a different search term, or run this as a Web-industry leaderboard instead?" with explicit options.
- **Step 1 returns many ambiguous matches** (e.g. 99 hits for "technology"): present top 5 by shallowest depth in retail-relevant root trees, ask the user to pick. Do NOT auto-pick `data[0]`.
- **User passes a full Web-category name instead of a slug** (e.g. "Computers Electronics and Technology"): convert to PascalCase_With_Underscores form and try; if that fails with 400, ask one disambiguation question with closest matches from the hardcoded slug list.
- **Web slug not in hardcoded list**: ask "Which closest matches: [present 3-5 closest from the list]?". Hardcoded list: `Computers_Electronics_and_Technology`, `Health`, `Finance`, `Sports`, `News_and_Media`, `E-Commerce_and_Shopping`.
- **Web tool returns `400 VALIDATION_ERROR`**: unrecognized slug; ask user to re-pick from the hardcoded list. Distinct from 404 (recognized but no data).
- **Web tool returns `404 NOT_FOUND`**: recognized slug but no data for the country + window. Render empty Web companion section with Caveat: "No Web-industry data for slug `<slug>` in country `<country>` for the rolling-3-month window."
- **`--enrich-traffic` passed without `--web-companion`**: exit with usage hint at Step 1.
- **User passes a non-default Amazon TLD** (e.g. `--amazon-tld amazon.de`): accept any of the 6 enum values. `revenue` will be in native currency (EUR); `revenue_in_usd` is the USD-normalized field per `categories-top-brands-shape`. Recipe always uses `revenue_in_usd` for the rendered revenue column to keep cross-domain sums consistent.
- **`total_clicks != category_paid_clicks + category_organic_clicks`** (identity drift from T11 grounding): flag with `[!gap]` in the Total demand section: "Click identity from grounding does not hold; the click breakdown semantics may have shifted server-side."
- **`get-categories-sales-performance-agg` access-denied at runtime**: skip Step 5; skip the Sales performance section; note in Caveats: "Sales performance not accessible on this plan."
- **`get-websites-top-sites-by-category-agg` access-denied at runtime** (and `--web-companion` supplied): skip Step 6; skip the Web companion section; note in Caveats: "Web companion not accessible on this plan; Amazon shopper sizing only." If the entire user request was Web-only (no Amazon match), exit with "Neither Amazon shopper nor Web industry data is accessible for `<input>` on this plan."
- **`get-websites-traffic-and-engagement` access-denied at runtime** (and `--enrich-traffic` supplied): skip Step 7; render the Web companion top-sites table without the Traffic enrichment subsection; note in Caveats: "Traffic enrichment not accessible on this plan; Web companion rendered as domain leaderboard only."

## Cowork artifact (when 10+ top brands)

Persistent artifact per sw-foundation-render-cowork § Tier 3. SUPPLEMENTAL; markdown ALWAYS renders unchanged.

**Trigger.** Step 3 returned 10 or more top-brand rows.

**Slug.** `sw-market-<category-slug>-<yyyymm>` (slug = kebab-cased `category_path`). Call `mcp__cowork__list_artifacts` first; if exists, prefer `update_artifact`.

**Two-step.** `Write` HTML to `~/sw-market-<category-slug>-<yyyymm>.html`, then `mcp__cowork__create_artifact({id, html_path, description, mcp_tools})`. See sw-foundation-render-cowork § Tier 3 for call shape + CSP whitelist.

**Page:**

1. Header (category + Amazon TLD + window + `meta.last_updated`).
2. HHI badge per § expert-heuristics: `FRAGMENTED` (<1500), `MODERATE` (1500-2500), `CONCENTRATED` (>=2500). Footnote: "HHI from top-10 only; absolute HHI higher with long tail."
3. Toolbar: "top N" (10 / 25 / 50; default 25), "sort by" (revenue_share / market_share / total_clicks / conversion_rate). State in `localStorage`.
4. Chart.js horizontal bar of top-N by `revenue_share`. Labels: `revenue_share %` + `revenue_in_usd` ($N.NB / $N.NM).
5. Grid.js sortable table. Columns: `rank`, `brand`, `revenue_share`, `market_share` (alias for `total_views_share`), `total_clicks`, `conversion_rate`, `last_updated`.
6. Optional Chart.js pie (top-10 + "all others") when brand count > 25.

**MCP tools (prefix `mcp__similarweb__`; substitute the prefix your session exposes for the Similarweb tools, which is connector-specific on Cowork):** `get-categories-top-brands-agg`, `get-categories-performance-agg`.

**localStorage:** `sw-market-top-n`, `sw-market-sort-by`, `sw-market-sort-order`.

**Rules:** `revenue_share` percent to 2 decimals; `revenue_in_usd` as `$N.NB` / `$N.NM` / `$N,NNN`; `conversion_rate` percent to 2 decimals, `n/a` when null; `total_clicks` is click-attribution (per categories-top-brands-shape), NOT additive to category clicks; top-10 covers ~80% of revenue.

**Skeleton (runtime LLM fills in SRI hashes + actual data):**

```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>sw-market</title>
<style>
:root{color-scheme:light}
body{font:14px/1.4 system-ui;margin:0;padding:16px;background:#fff;color:#111}
.b{display:inline-block;padding:6px 14px;border-radius:6px;font-weight:600}
.b.fragmented{background:#d1fae5;color:#065f46}
.b.moderate{background:#fef3c7;color:#92400e}
.b.concentrated{background:#fee2e2;color:#991b1b}
</style>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" integrity="sha384-..." crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
</head><body>
<header><h1>Market: Electronics</h1><span class="meta">amazon.com | last_updated 2026-04-30</span></header>
<div id="badge" class="b"></div>
<canvas id="bar" height="320"></canvas><div id="grid"></div><canvas id="pie" height="280"></canvas>
<script>
const SW='mcp__similarweb__',CATEGORY_ID='10048700011',TLD='amazon.com';
const topN=parseInt(localStorage.getItem('sw-market-top-n')||'25',10);
const tier=h=>h<1500?'fragmented':h<2500?'moderate':'concentrated';
async function load(){
  const [brands]=await Promise.all([
    window.cowork.callMcpTool(SW+'get-categories-top-brands-agg',{domain:TLD,category:CATEGORY_ID,limit:topN}),
    window.cowork.callMcpTool(SW+'get-categories-performance-agg',{domain:TLD,category:CATEGORY_ID})
  ]);
  const rows=(brands?.data||[]).map((b,i)=>({rank:i+1,...b}));
  const hhi=rows.slice(0,10).reduce((s,b)=>s+b.revenue_share**2,0)*10000;
  const t=tier(hhi);
  const el=document.getElementById('badge'); el.className=`b ${t}`; el.textContent=`${t.toUpperCase()} (HHI ${hhi.toFixed(0)})`;
  renderBarChart(rows); renderGrid(rows);
  if(rows.length>25) renderPie(rows);
}
load().catch(e=>document.body.insertAdjacentHTML('beforeend',`<pre>${e.message}</pre>`));
</script></body></html>
```

Runtime LLM fills in SRI hashes (from Cowork's CSP `integrity` directives), resolved `CATEGORY_ID`, and the three render functions. Skeleton fixes the contract: two SRI-pinned CDN scripts, async `load()` calling two MCP tools, client-side HHI per Step 5 derivation #5.

**Failure handling.** Per sw-foundation-render-cowork § Failure handling. If `create_artifact` is unavailable, one line in `## Caveats` and continue markdown-only.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this market profile" -> `~~deck` (pptx by default). Layouts: title slide, Total demand, Top brands, Top keywords, Web companion, Concentration verdict (HHI), Strategic insights.
- "Export the top-brands table to a spreadsheet" -> `~~spreadsheet` (xlsx by default). Tabs: total demand, top brands (revenue + traffic share), top keywords, web companion sites.
- "Send this market profile to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following assertions in `tests/grounding-ledger.json`. Build-time `--validate` rejects unknown references.

- categories-search-resolution
- categories-performance-shape
- categories-top-brands-shape
- categories-top-keywords-shape
- top-sites-by-category-shape
- partial-access-envelope-shape
