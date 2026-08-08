---
name: sw-foundation-data
description: Background helper for the seven Similarweb recipes, loaded via their Inherits block and on sw-router dispatch, never for trivial single metric lookups (the Step 0 carve-out exits first). Carries country normalization, window resolution, and conversation context across recipe runs. Calls no MCP tools itself; pairs with sw-foundation-core and sw-foundation-render.
user-invocable: false
---
# sw-foundation-data: country, window, and conversation-context normalization

Loads via each recipe's Inherits block and via sw-router dispatch. Does NOT call MCP tools. Carries the canonical normalization patterns recipes need before any MCP call lands.

## Helper sections (recipes reference these by name)

### § country-normalization

Every tool that accepts a `country` parameter wants ISO-3166-1 alpha-2
(`"us"`, `"gb"`, `"de"`). Full country names like `"United States"` or
`"Germany"` cause `VALIDATION_ERROR`. Recipes MUST normalize before any
MCP call.

Canonical rule: ALWAYS lowercase the user-supplied value first; THEN map
full names to ISO-2. Recipes inline this bash idiom (they cannot share a
function across processes):

```bash
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # lowercase first; the map below assumes lowercase
case "$COUNTRY" in
  "united states"|"usa"|"u.s."|"u.s.a.") COUNTRY="us" ;;
  "united kingdom"|"uk"|"great britain"|"britain") COUNTRY="gb" ;;
  "germany") COUNTRY="de" ;;
  "france") COUNTRY="fr" ;;
esac
```

Extend the `case` map above when a new alias is needed; recipes inherit by re-citing this section. Pass-through: any already-ISO-2 value (two lowercase letters) is left unchanged. If the user-supplied string is not in the case map and is not a 2-letter token, the recipe asks ONE disambiguation question rather than guessing. Default when COUNTRY is unset: `us`.

### § window-resolution

Windowed tools resolve relative date keywords server-side: pass `end_date = "latest"` and `start_date = "N_months_ago"` directly to the real call; the server resolves, clamps to its latest published month, and echoes the effective window plus `meta.last_updated` in the response (no separate probe, no client-side date math, never compute and pass `today`: that 400s with "Dates not in range"). Both endpoints are inclusive, so an N-month window starts at `(N-1)_months_ago`; the default rolling 3-month window is exactly `start_date = "2_months_ago"`, `end_date = "latest"` (subtracting N instead of N-1 is the most common cause of cap 400s). Live-grounded per `window-relative-keywords`. The full rules (clamp Caveat wording, the 3-month-capped tool list, the EXACT-3-month-span subset, single-month tools, the shopper/categories family, prior-period window derivation) live in `references/window-resolution.md`; Read it before any windowed call that departs from the default 3-month pattern, and whenever deriving a prior-period window.

### § cost-models

Per-tool credit cost varies by tool FAMILY, not one global rule. The charge is in `meta.data_credits_charged` on every success envelope (the field formerly named `meta.sw_coins`); failed 4xx/403 calls are uncharged. Pick the cheapest call shape per family. Each shape below is grounded against 2+ data points (one observation cannot distinguish a cost model; see the `feedback_cost_model_grounding` discipline and the grounding ledger).

- **Metric-priced** (the lever is the `metrics` list): `get-websites-traffic-and-engagement` (~2 credits per requested metric-month), `get-lead-enrichment-website` (5 credits for 4 trimmed metrics vs 27 for the full default set). Request ONLY the metrics the output renders.
- **Row-priced by REQUESTED rows, window-independent** (the lever is `limit`; window length does not multiply because an `-agg` tool returns one row per entity): `get-website-analysis-traffic-channels-share` (exactly 2 credits per requested row: 20 / 50 / 100 / 200 charged at limits 10 / 25 / 50 / 100, four limit points on ONE window; window-independence is NOT yet grounded for this tool, and it is not an `-agg` tool, so do not assume the family rule applies), `get-keywords-latest-agg` (~1 credit per 5 rows). Bound `limit` to what the render uses.
- **Priced on TWO axes at once** (bound BOTH): `get-websites-geography-agg` charges `rows x (metrics + 1)`, window-independent. Six points across two sessions fit it: 15/75/150 at limits 5/25/50 with two metrics, then 30 at limit 10 with two metrics, 70 at limit 10 with six, and 700 at limit 100 with six. It was previously recorded here as flat 3 credits/row, which was the two-metric shape described as if it were a property of the tool; passing `limit` alone and letting the server apply all six metrics costs 2.3x what the shipped figure claims. Grounded in `geography-agg-cost-shape`. When a tool takes both a row bound and a `metrics` list, assume the axes multiply until measured otherwise.
- **Flat per call, `limit` does not move the charge** (bound it anyway for PAYLOAD, not for cost): `get-website-content-technologies-agg` charged 10 credits at limit 10 AND 10 at the server default of 100. It was previously filed as row-priced at ~1 credit/row on the strength of the limit-10 point alone, where flat-10 and 1-per-row are indistinguishable; the limit-100 point separates them and the tool is flat. Payload still scales (about 45 KB at limit 100, driven by long `description` fields), so the bound is a bytes lever here rather than a cost lever.
- **Window-priced, no limit lever** (bound the WINDOW instead; the tool either has no `limit` parameter or `limit` does not move the charge): `get-website-analysis-traffic-channels` (10 credits per month, and it has NO `limit` parameter at all: 10 for one month and 30 for three months on one domain, 10 for one month on a second), `get-website-analysis-search-spend` (1 credit per month: 1 for one month, 3 for three months), `get-websites-similar-sites-agg` (~20 credits at limits 4-5; two data points, approximate).
- **Single-point observations, cost shape NOT yet multi-point grounded.** Treat each figure below as an order of magnitude only, and re-probe at a second limit AND a second window before quoting it as a shape. The renamed referral family, which superseded the pre-rename pair the old "referral -agg tools, ~4 credits/row" row was keyed to (that row is withdrawn; one of its two tools, `get-websites-referrals-agg`, is retired outright): `get-website-analysis-traffic-referrals-incoming` ~3 credits/row (75 at limit 25), `get-website-analysis-traffic-referrals-outgoing` ~3 credits/row (30 at limit 10), `get-website-analysis-traffic-referrals-aggregated` ~3.7 credits/row at `referral_type: incoming` (96 at limit 25, 374 at limit 100) while its advertisers-on-desktop panel priced differently (32 at limit 10), so `referral_type` appears to change the rate. Also `get-website-analysis-display-networks-agg` ~2.5 credits per RETURNED row (14 for the 5 rows at limit 5, 46 for the 18 rows returned at limit 25, so it charges what it returns, not what you request), `get-website-analysis-social-traffic-sources-agg` ~3 credits/row (30 at limit 10), and `get-website-content-subdomains-agg` ~2 credits/row (10 at limit 5).
- **Free** (`*-search`: observed 0 credits; `*-describe`: unmetered, no credit field to read): the `*-search` and `*-describe` endpoints (`get-categories-search`, `get-brands-search`, `get-user-segments-describe`, `get-industry-demographics-describe`, `get-industry-unique-users-describe`, `get-custom-industries-describe`, and siblings). `get-demand-search-trends` also charged 0 on a 3-month monthly window (single observation, so not yet multi-point grounded). **Free in credits is NOT free in context.** Credits and response bytes are independent axes. `get-user-segments-describe` costs nothing and returned 23.9 MB on one account, with `length` and `chars` accepted but inert, so it is DO-NOT-CALL. `get-custom-industries-describe` is 60 B at its server default and 5.0 MB with `include_shared=true`, so never pass that flag. Check the payload before calling anything in this bucket.

This taxonomy is an empirical starting heuristic, re-grounded per tool, never a server guarantee; verify a new tool's shape at a second limit and window before asserting it. Two live distinctions are load-bearing when estimating a call before issuing it: requested-rows vs returned-rows pricing (channels-share charges for every row you ASK for even when the panel is shorter, while display-networks-agg charged for the 18 rows it RETURNED at limit 25), and the fact that a tool with no `limit` parameter is not therefore cheap, it is simply window-priced.

**Every cost figure names the parameter shape it was measured at.** A bare number ("about 30 credits") reads as a property of the tool and is almost always a property of one call: `get-websites-geography-agg` shipped as "3 credits per row" for months, which was true only of a two-metric call and understated the recipe's own default by 2.3x. Write "N credits at limit L with M metrics", or "N credits per month", and never a figure whose shape a reader has to guess. The same applies when RECORDING a new observation: `meta.query` and `meta.request` echo the shape the server actually applied, including bounds you did not pass, so the shape is always recoverable from the response itself.

**"Free" on a describe means unmetered, not measured-and-zero.** The `*-describe` endpoints return no `meta` block at all, so there is no `data_credits_charged` field to read; the claim is that nothing was billed, which is weaker than the explicit `0` the `*-search` endpoints do return. Do not cite a describe's cost as an observed zero.

### § category-vocabulary

The category string returned by `get-websites-website-rank` and `get-websites-similar-sites-agg` (e.g. `Lifestyle/Fashion_and_Apparel`) is DISPLAY taxonomy; it is NOT the slug vocabulary `get-websites-top-sites-by-category-agg` accepts (a transferred string 400s with "Selected category is not supported.") NOR the numeric Amazon category IDs the shopper tools use. Never transfer a category identifier across these families; each has its own vocabulary, and top-sites slugs come only from the hardcoded list a recipe pins. Per `categories-search-resolution` and `top-sites-by-category-shape`.

### § conversation-context

When the conversation already contains a prior recipe's output (detected by the standard recipe header line and the bold Sources line), reuse it: skip redundant tool calls, reference prior findings, tighten NEXT MOVES. The detection pattern, the three reuse rules (window and freshness, competitor set, effective end_date), and the cross-reference sentence live in `references/conversation-context.md`; Read it when a prior recipe header is present in context. Hard floor kept inline: NEVER fabricate a prior-recipe finding (only what literally appears in context); when in doubt re-resolve with a fresh call (a redundant call is cheaper than a stale figure); when no prior recipe ran this session, skip this helper silently.

## What this skill does NOT do

It does not call MCP tools, produce visible output, or override sw-config / any recipe's hard rules. Tool-catalog priors, capability-gating, and bulk-input-from-context live in sw-foundation-core. Rendering, citation block, error rendering, expert heuristics, visualizations, and handoff JSON live in sw-foundation-render. Recipe and router skills load all three sub-foundations and act on them.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- website-rank-no-global-field
- window-relative-keywords
- keywords-overview-3-month-max
- keywords-competitors-exact-3-months
- landing-pages-window-constraint
- similar-sites-window-constraint
- agg-variant-cost-savings
- keywords-latest-agg-shape
- audience-geography-shape
- referral-pipelines-divergence
- geography-agg-cost-shape
- payload-measurements
