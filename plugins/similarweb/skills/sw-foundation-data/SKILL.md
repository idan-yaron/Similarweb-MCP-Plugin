---
name: sw-foundation-data
description: Helper utility loaded by the seven user-invocable Similarweb recipes (sw-competitive-teardown, sw-audience-overlap, sw-channel-mix, sw-market-size, sw-aeo-audit, sw-page-mix, sw-keyword-opportunity) and by sw-router when it dispatches to a recipe or plans a direct-MCP fallback. Carries Similarweb MCP data-handling priors: country normalization, window resolution, conversation context across recipe runs. Helper sections cited by recipes are section country-normalization, section window-resolution, section conversation-context. NOT loaded for trivial single-domain single-metric lookups; the sw-router Step 0 carve-out exits before reaching the foundations. Does not call MCP tools itself; pairs with sw-foundation-core and sw-foundation-render.
user-invocable: false
---
# sw-foundation-data: country, window, and conversation-context normalization

Loads on every Similarweb-shaped turn. Does NOT call MCP tools. Carries the canonical normalization patterns recipes need before any MCP call lands.

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

The Similarweb server clamps every date range to its most recent `meta.last_updated` (the latest published month). Passing `end_date: <today>` returns `VALIDATION_ERROR / Dates not in range`. Recipes that need a window MUST derive effective `end_date` from a cheap probe BEFORE issuing any windowed call.

Canonical probe: `get-websites-website-rank` with the target domain and ISO-2 country. Doubles as a smoke test (null rank means abort) and returns `meta.last_updated` in YYYY-MM-DD. The probe is the cheapest tool in the catalog; recipes need it as Step 0 / 1 anyway.

**Bound the rank smoke to a known-safe window.** Default rank call returns a 36-month series at ~74 data credits. Only `meta.last_updated` is needed. Canonical pattern:

```bash
START_DATE=$(date -d "$(date +%Y-%m-01) -3 month" +%Y-%m-%d)   # first day of current_month - 3
END_DATE="latest"                                                # server resolves to meta.last_updated
```

`end_date="latest"` is the cleanest contract (~2-4 data credits per smoke call). If `"latest"` is ever rejected, fall back to `END_DATE=$(date -d "$(date +%Y-%m-01) -1 day" +%Y-%m-%d)` (last day of prior month). NEVER use `today`, first day of current month, or any value beyond the prior month's last day. The server 4xxs.

Rules:

1. Set `end_date = meta.last_updated` from the rank smoke. Never `<today>`. Never a user-supplied future date.
2. If the user supplied an explicit `end_date`, clamp to `meta.last_updated` (`end_date = min(user_end_date, meta.last_updated)`) and add a Caveat: "end_date clamped from <requested> to <meta.last_updated>; the server's latest published month is the ceiling."
3. Default window length is rolling 3 months. Compute `start_date = end_date - 3 months` in YYYY-MM granularity. Recipes may override (e.g. 90 days) when they have a documented reason.
4. Some tools (e.g. `get-keywords-seo-overview`, `get-websites-serp-players-agg`) reject windows wider than rolling 3 months with `VALIDATION_ERROR`. Do NOT widen past 3 months for those tools.
5. **Single-month tools:** `get-websites-landing-pages-agg` with `granularity: "monthly"` accepts ONLY a one-calendar-month window (the most recent month). Pass `start_date = first day of effective_end_date's month`, `end_date = effective_end_date`. Use `granularity: "daily"` for the last 28 days when a finer window is needed. See `landing-pages-window-constraint`.

Recipes without a date-range surface (e.g. sw-audience-overlap, sw-competitive-teardown, sw-market-size's Amazon flow) ignore this section.

### § conversation-context

When a recipe runs in a conversation that already contains output from a prior recipe (this turn or earlier), the model SHOULD detect and reuse that output to (a) skip redundant tool calls, (b) reference prior findings in the new output, (c) tighten NEXT MOVES bullets to build on what's already known.

**Detection pattern.** Scan recent assistant turns for the standard recipe header `*<target> | <country> | <window> | last_updated <date>*` (the italic context line from § citation block). Each header tags an upstream recipe run. Also scan for the bold Sources line `**Sources:** N data credits across M calls (...)` which marks a completed recipe.

**Reuse rules:**

1. **Rank smoke.** If a prior recipe was for the SAME target AND country AND its `last_updated` matches today's expected value (within the same monthly publish boundary), skip the `get-websites-website-rank` smoke call; reuse the cached rank from the prior recipe's output. Surface as a single-line Caveat: "Rank smoke skipped; reused from prior /sw-<recipe> for <target>."

2. **Competitor set.** If a prior recipe surfaced a competitor list (similar-sites discovery in /sw-competitive-teardown, --against in /sw-audience-overlap, --vs in /sw-competitive-teardown), and the current recipe needs competitors without explicit args supplied, reuse the prior set. Surface in a Caveat: "Competitor set reused from prior /sw-<recipe>: <list>." If explicit competitors are supplied this turn, ignore the prior set.

3. **Window.** If a prior recipe resolved an effective `end_date`, reuse it for the current recipe unless the user explicitly asks for a different window.

**Cross-reference rules.** When the current recipe surfaces a finding that materially relates to a prior recipe's verdict, prepend ONE optional sentence under the Executive read:

> "Connecting back to your earlier /sw-<recipe> for <target>: <one sentence linking findings>."

OPTIONAL; include only when the linkage is substantive (a SAME POND label connecting to a channel-mix overlap; a rank shift explaining a market-size finding; an AEO recommendation linking to a content gap surfaced in /sw-page-mix). Do NOT cross-reference trivial connections. If the model is unsure whether a linkage is substantive, OMIT.

**Hard rules:**
- NEVER fabricate a prior-recipe finding. Only reference what literally appears in conversation context.
- NEVER reuse rank data if the prior `last_updated` is older than the current expected last-published-month boundary.
- NEVER reference a prior recipe without naming it by slash-command form (e.g., "your earlier /sw-channel-mix run for adidas.com").
- FAIL-SAFE: when in doubt, re-run the smoke. A redundant call is cheaper than a stale figure.
- When no prior recipe ran in this session, skip this entire helper silently. Do NOT mention it.

## What this skill does NOT do

It does not call MCP tools, produce visible output, or override sw-config / any recipe's hard rules. Tool-catalog priors, capability-gating, and bulk-input-from-context live in sw-foundation-core. Rendering, citation block, error rendering, expert heuristics, visualizations, and handoff JSON live in sw-foundation-render. Recipe and router skills load all three sub-foundations and act on them.

## Grounded assertions

This skill's behavior is live-validated against the following assertions in `tests/grounding-ledger.json`. Build-time `--validate` rejects unknown references.

- website-rank-no-global-field
