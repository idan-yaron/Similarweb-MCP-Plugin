---
name: sw-page-mix
description: URL and folder level content surface for one domain. Use for which pages drive traffic, top URLs, folder breakdown, content concentration, which site sections own the audience, or what a brand publishes most. Renders top URLs by traffic share and the folder hierarchy with a concentration verdict. Do not use for content or keyword gaps versus a rival (use sw-keyword-opportunity), for AI citation posture (use sw-aeo-audit), or for one URL traffic share (one MCP call suffices).
---
# sw-page-mix

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution, § conversation-context
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER pass `web_source: "desktop"` or `web_source: "mobile_web"` to either pages tool. Per `pages-tools-web-source-total` and the live tool schemas (`const: total`), only `total` is supported. Server returns HTTP 400 VALIDATION_ERROR on any other value.
- NEVER pass a full country name (`"United States"`) to either tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize per sw-foundation-data § country-normalization before any call.
- NEVER pass `end_date: <today>`. The server clamps to `meta.last_updated` (e.g. `2026-04-30` at grounding time) and rejects future dates with `VALIDATION_ERROR / Dates not in range`. Derive effective `end_date` per sw-foundation-data § window-resolution from the Call 0 rank smoke's `meta.last_updated`.
- NEVER fabricate a traffic_share for a folder or page when the response row's `share` is null or absent. Render `n/a` per sw-foundation-render § error-rendering pattern 1 (null payload; pattern 4 is reserved for structural-zero `0.0` values).
- NEVER sum top-N folder shares as if they were disjoint when parent/child folders both appear in the response. Per `pages-leading-folders-shape`, the server does NOT dedupe (`nike.com/launch` and `nike.com/launch/t` coexist). The recipe computes HHI on the returned rows AS-IS for the concentration verdict but documents the nesting in the strategic insights, not by quietly collapsing rows.
- NEVER call `get-pages-popular-pages-agg` with the `page` parameter set when summarizing the surface; that filters the response to a single page only, which is a per-page drill-in, not a top-page survey.

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
DOMAIN="<first positional arg>"
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
FOLDER_DEPTH="${FOLDER_DEPTH:-2}"  # optional max folder depth to surface in strategic-insights commentary (NOT a tool param)
echo "$DOMAIN" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-page-mix <domain> [--country <iso-2>] [--folder-depth <N>]"; exit 1; }
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

- **Smoke**: `get-websites-website-rank`, target domain only, country=`$COUNTRY` (user-supplied or default `us`), bounded `start_date = "2_months_ago"`, `end_date = "latest"`. The smoke IS the Call 0 rank call; reuse it, never re-issue it.
- **Secondary probe**: `get-pages-popular-pages-agg`, target, country=`$COUNTRY`, single-month window, `web_source: total`, `limit: 5`.
- **Pinned absence outcomes**: `get-websites-website-rank`: retarget the smoke and degrade rank rendering; ONE pages tool: drop its section (the DEGRADABLE semantics below, same as denial); BOTH pages tools: abort with the caveat (nothing to render).
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED: `get-websites-website-rank`. DEGRADABLE: `get-pages-popular-pages-agg`, `get-pages-leading-folders-agg` (if ONE pages tool returns access-denied at runtime, the recipe drops that section and notes the skip in Caveats rather than aborting; if BOTH pages tools are denied there is nothing to render, so abort per sw-foundation-render § error-rendering Pattern 5 semantics with a clear Caveat).

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. sw-page-mix is single-domain. If the conversation contains a list of domains and the user did not pin one, ask which domain to page-mix (single confirmation).

## Step 4: Plan the call sequence

| Call | Tool | Purpose |
|------|------|---------|
| 0 | `get-websites-website-rank` | The Step 2 smoke (reused, not re-called) + headline rank + derive effective `end_date` from `meta.last_updated`. Bound to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits vs ~74 for the default 36-month series. Per `website-rank-no-global-field`, the response has NO `global_rank` field; render the in-country rank from this single call. |
| 1 | `get-pages-popular-pages-agg` | Top URLs by traffic share. `web_source: total` (HARD CONSTRAINT). `limit: 25`. 3-month window with `granularity: monthly` (omitting granularity defaults the endpoint to daily, which rejects any window past 28 days). ~75 sw_coins. |
| 2 | `get-pages-leading-folders-agg` | Top folders by traffic share. `web_source: total` (HARD CONSTRAINT). `limit: 15`. 3-month window with `granularity: monthly` (same daily-default rejection). ~45 sw_coins. |

Default total cost: ~125 sw_coins (rank smoke + 25 pages + 15 folders).

## Step 5: Execute

Call 0 runs first; derive the effective window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`, so 3 calendar months) and read `meta.last_updated` from its response. Calls 1 and 2 are independent given the resolved window; parallelize.

Client-side derivations after responses arrive:

1. **From Call 1 (top URLs):**
   - Recipe surfaces top 10 in the rendered table (server returned 25; bottom 15 are kept in handoff JSON).
   - Sum top-10 shares to compute "top-10 page concentration" (the head's share of all traffic).
   - Identify the top-3 "anchor pages" (highest `share` rows) for the strategic-insights commentary.
   - For each URL row, retain `change` for the period-over-period column.

2. **From Call 2 (top folders):**
   - Compute folder HHI: `hhi = sum((share_i * 100) ** 2 for i in returned_rows)`. Note this uses the partial-tail subset, NOT the full domain; per § expert-heuristics it's an underestimate of true folder HHI.
   - Apply the § expert-heuristics threshold verdict: `hhi < 1500` -> `FRAGMENTED`; `1500 <= hhi < 2500` -> `MODERATE`; `hhi >= 2500` -> `CONCENTRATED`.
   - Compute "concentration in top-5 folders" = sum of first 5 folder shares.
   - Classify each folder by depth (count slashes after the domain); surface parent vs child structure in the strategic-insights commentary, capped at `--folder-depth` (default 2).

3. **Strategic insights (DEFEND / EXPOSE / PLAY):** per § expert-heuristics, three bullets sized to the data:
   - `DEFEND`: the anchor pages (top-3 URLs) that hold disproportionate share; render the actual share number.
   - `EXPOSE`: a content gap that the data implies (e.g., a folder with declining `change` that the top-3 URLs ignore; or the dominant folder concentrating risk).
   - `PLAY`: a follow-up question the user can ask the next recipe (e.g., "How does <target> compare to <competitor> on this folder?").

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, sw_coins, last_updated}`. Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

## Step 6: Classify output intent

Per sw-foundation-render intent-aware output rendering rules. Default: narrative.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} | {country} | {window} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Top URLs table:** Unicode horizontal bars over top-10 URL shares (cap width 16). Pair with the table.
- **Folder hierarchy:** Unicode horizontal bars over the returned folder shares (cap width 16). Pair with the table.
- **HHI threshold position:** Unicode threshold bar showing where the folder HHI lands relative to the 1500 / 2500 thresholds.

Sections in order:

- `## Executive read` (numbers-LIGHT, max 3 sentences. FIRST WORD is the folder-concentration verdict (`FRAGMENTED`, `MODERATE`, `CONCENTRATED`) per § expert-heuristics. Name the top-1 anchor page (URL + share) and the dominant folder (folder + share) in the same paragraph. If concentration is `CONCENTRATED`, note the risk of overdependence; if `FRAGMENTED`, note the spread. When the current recipe builds materially on a prior recipe in this conversation, prepend with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Rank + reach` (table: country rank, from Call 0; if the user country IS `ww`, the table collapses to one row).
- `## Top URLs` (table from Call 1, top 10 rows sorted by `share` descending. Columns: `Rank`, `URL`, `Traffic share`, `Change vs prior`. `share` rendered as percent to 2 decimals; `change` rendered as `+X%` / `-X%`, `n/a` when null. Pair with Unicode bar visualization.).
- `## Folder hierarchy` (table from Call 2, all returned rows sorted server-side by `share` descending. Columns: `Rank`, `Folder`, `Traffic share`, `Change vs prior`. Pair with Unicode bar visualization. Sub-line below the table: "Folders nest; parent and child paths both appear when the server returns them. The top-5 folder concentration is X%.").
- `## Concentration` (Unicode HHI threshold bar per § visualizations. Headline: `HHI: <value>  <bar>  <VERDICT>`. Sub-line citing the 1500 / 2500 thresholds. Sub-line: "HHI computed on the top-N folder subset; absolute HHI rises when the long tail is added.").
- `## Strategic insights` (3 bullets per § expert-heuristics, each labeled `DEFEND` / `EXPOSE` / `PLAY` and ending with `(confidence: HIGH | MEDIUM | LOW)`. Reference the SPECIFIC numbers and URLs surfaced in this run.).
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the strongest signal in the render:
  - **Competitive teardown** when concentration is high and the top anchor page is a category landing:
    `"How does <target> stack up against <relevant-competitor-or-known-rival>?"` followed by one sentence on whether the anchor pages translate into actual win-rate vs the rival.
  - **Audience overlap** when the dominant folder is content-heavy (e.g., editorial or product detail):
    `"What's <target>'s audience overlap with <natural-content-neighbor>?"` followed by one sentence on whether the audience visits a related site for similar content.
  - **Keyword opportunity** when the anchor pages are clearly query-driven (PDP pages, category listings):
    `"What keywords is <competitor> winning that <target> isn't?"` followed by one sentence on whether the anchor-page traffic depends on a small keyword set.

  Reference specific URLs, folders, or concentration numbers surfaced in THIS run.)
- `## Caveats` (per sw-foundation-render § error-rendering, only if any tool returned null / was unavailable / was skipped / `end_date` was clamped / pages tool returned fewer than `limit` rows for a domain with thin coverage / nested-folder rows present).
- Sources line per sw-foundation-render § citation block (single line, NOT a table, NOT collapsible). Last element of the output unless `intent=handoff`.
- `[optional] ## Handoff` (JSON, only when intent=handoff).

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-page-mix handoff

```json
{
  "rank": {"country": 0, "country_param": "us"},
  "window": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "top_urls": [
    {"rank": 1, "url": "<url>", "share": 0.0, "change": 0.0}
  ],
  "folders": [
    {"rank": 1, "folder": "<folder>", "share": 0.0, "change": 0.0, "depth": 0}
  ],
  "hhi": 0,
  "hhi_verdict": "FRAGMENTED | MODERATE | CONCENTRATED",
  "concentration_top5": 0.0,
  "concentration_top10_pages": 0.0,
  "anchor_pages": [
    {"rank": 1, "url": "<url>", "share": 0.0}
  ]
}
```

Field semantics:
- `top_urls` rows: 25 returned by the server; rendered table shows top 10, handoff carries the full 25.
- `folders` rows: 15 returned by the server. `depth` = count of slashes after the domain (`nike.com/w` is depth 1; `nike.com/launch/t` is depth 2).
- `hhi` is computed on returned rows only; it is an underestimate of true folder HHI per § expert-heuristics.
- `hhi_verdict` follows the § expert-heuristics threshold ladder: <1500 FRAGMENTED, 1500-2499 MODERATE, >=2500 CONCENTRATED.
- `concentration_top5` is the sum of the first 5 returned folder shares (0..1). May exceed 1.0 IF nested parent/child rows both appear in the top 5 (rare but possible; surfaced in Caveats).
- `concentration_top10_pages` is the sum of the first 10 page shares (0..1).
- `anchor_pages` is the top 3 URLs by share.

## Edge cases

- **Target has no Similarweb coverage** (Call 0 rank returns null): print "Similarweb has no coverage for `<target>`. Aborting." Exit.
- **`get-pages-popular-pages-agg` access-denied at runtime**: skip Call 1; skip the `## Top URLs` section; note in Caveats. `top_urls` and `anchor_pages` are empty in handoff. Folder section still ships.
- **`get-pages-leading-folders-agg` access-denied at runtime**: skip Call 2; skip the `## Folder hierarchy` and `## Concentration` sections; note in Caveats. `folders`, `hhi`, `hhi_verdict`, `concentration_top5` are null in handoff. Top URLs section still ships.
- **Both pages tools access-denied at runtime**: print "Neither pages tool is accessible on this plan; the page-mix recipe needs at least one. Aborting." Exit.
- **Server returns fewer rows than requested limit** (thin coverage): surface in Caveats ("server returned N rows for limit=M; domain has thin coverage on country=X"); render what was returned.
- **All returned page rows have `share = 0.0`** (silent zero-fill artifact): treat as missing data; surface in Caveats and skip the URL bars but render the table.
- **User-supplied `end_date` is beyond `meta.last_updated`**: clamp per sw-foundation-data § window-resolution and note in Caveats with the canonical "end_date clamped from <requested> to <meta.last_updated>" wording.
- **Full country name passed**: normalize per sw-foundation-data § country-normalization before any call.
- **Nested folder rows in top 5 (parent + child both appear)**: render both rows; surface in Caveats: "Folder hierarchy contains nested rows (parent + child both surfaced); top-5 concentration may double-count parent traffic."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- pages-popular-pages-shape
- pages-leading-folders-shape
- pages-tools-web-source-total
- website-rank-no-global-field
- partial-access-envelope-shape
