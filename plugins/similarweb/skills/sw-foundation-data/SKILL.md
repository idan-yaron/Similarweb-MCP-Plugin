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

### § conversation-context

When a recipe runs in a conversation that already contains output from a prior recipe (this turn or earlier), the model SHOULD detect and reuse that output to (a) skip redundant tool calls, (b) reference prior findings in the new output, (c) tighten NEXT MOVES bullets to build on what's already known.

**Detection pattern.** Scan recent assistant turns for the standard recipe header `*<target> | <country> | <window> | last_updated <date>*` (the italic context line from § citation block). Each header tags an upstream recipe run. Also scan for the bold Sources line `**Sources:** N data credits across M calls (...)` which marks a completed recipe.

**Reuse rules:**

1. **Window and freshness.** If a prior recipe this session resolved a window for the SAME target AND country AND its `last_updated` matches today's expected publish boundary, reuse that window and `last_updated` rather than re-resolving on the current recipe's first call. Surface a single-line Caveat: "Window reused from prior /sw-<recipe> for <target>." Recipes that render rank (sw-competitive-teardown) may also reuse a prior rank value when present.

2. **Competitor set.** If a prior recipe surfaced a competitor list (similar-sites discovery in /sw-competitive-teardown, --against in /sw-audience-overlap, --vs in /sw-competitive-teardown), and the current recipe needs competitors without explicit args supplied, reuse the prior set. Surface in a Caveat: "Competitor set reused from prior /sw-<recipe>: <list>." If explicit competitors are supplied this turn, ignore the prior set.

3. **Effective end_date.** A prior recipe's resolved effective `end_date` (the server's latest published month) is target-independent; reuse it for the current recipe regardless of target, unless the user explicitly asks for a different window. Full window-plus-freshness reuse with the Caveat line still requires the SAME target and country per rule 1; this rule covers only the publish-boundary date itself.

**Cross-reference rules.** When the current recipe surfaces a finding that materially relates to a prior recipe's verdict, prepend ONE optional sentence under the Executive read:

> "Connecting back to your earlier /sw-<recipe> for <target>: <one sentence linking findings>."

OPTIONAL; include only when the linkage is substantive (a SAME POND label connecting to a channel-mix overlap; a rank shift explaining a market-size finding; an AEO recommendation linking to a content gap surfaced in /sw-page-mix). Do NOT cross-reference trivial connections. If the model is unsure whether a linkage is substantive, OMIT.

**Hard rules:**
- NEVER fabricate a prior-recipe finding. Only reference what literally appears in conversation context.
- NEVER reuse window or rank data if the prior `last_updated` is older than the current expected last-published-month boundary.
- NEVER reference a prior recipe without naming it by slash-command form (e.g., "your earlier /sw-channel-mix run for adidas.com").
- FAIL-SAFE: when in doubt, re-resolve via a fresh first call (or re-run the smoke for recipes that keep one). A redundant call is cheaper than a stale figure.
- When no prior recipe ran in this session, skip this entire helper silently. Do NOT mention it.

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
