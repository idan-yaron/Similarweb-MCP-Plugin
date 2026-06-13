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
- **Row-priced, window-independent** (the lever is `limit`; window length does not multiply because an `-agg` tool returns one row per entity): `get-keywords-latest-agg` (~1 credit per 5 rows), `get-websites-geography-agg` (3 credits/row: 15/75/150 at limits 5/25/50, same at 1 and 3 months), the referral `-agg` tools (~4 credits/row), `get-website-content-technologies-agg` (~1 credit/row). Bound `limit` to what the render uses.
- **Flat / per-window** (small-`limit` changes do not visibly cut cost; bound the WINDOW instead): `get-websites-similar-sites-agg` (~20 credits at limits 4-5; two data points, approximate). Tools probed at only ONE limit are NOT classified here; mark them "cost shape not yet multi-point grounded" rather than guessing.
- **Free** (0 credits): the `*-search` and `*-describe` endpoints (`get-categories-search`, `get-brands-search`, `get-user-segments-describe`, and siblings).

This taxonomy is an empirical starting heuristic, re-grounded per tool, never a server guarantee; verify a new tool's shape at a second limit and window before asserting it.

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
