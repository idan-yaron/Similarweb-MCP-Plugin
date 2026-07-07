---
name: sw-competitive-teardown
description: Competitive teardown of a target domain, with or without named rivals. Use for a teardown of one domain, competitive analysis, a head to head comparison, who is winning online, benchmarking against rivals, or a combined rank plus traffic plus channels plus overlap view of a comp set. Do not use when audience overlap is the main question (use sw-audience-overlap), for a single metric lookup (one MCP call suffices), for a vague analyze X prompt with no competitive angle (the router asks a clarifier), on Cowork when five or more rivals are named (the competitive deep dive agent handles wide sets), or when the ask explicitly chains two analyses (the router plans chains).
---
# sw-competitive-teardown

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER call N looped tools when an `-agg` batched-over-entities variant exists. The documented exception is `get-websites-audience-overlap-agg` (single batched call, 2-5 domains, 2^N-1 subset rows); every other tool here is looped per domain.
- NEVER include user-identifying info from training data; only what is in the prompt or in the MCP responses.
- NEVER skip the `## Sources` citation block (per sw-foundation-render § citation block).
- NEVER fabricate data (per sw-foundation-render § error-rendering). If a tool returns null, render `n/a` and surface in Caveats.
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize before any call.
- NEVER look for a `global_rank` field in `get-websites-website-rank` responses. Per `website-rank-no-global-field`, the response has `country_rank` only; pass `country: "ww"` to get global. The Rank + reach section's "Global rank" column maps to the `country_rank` value from the `country="ww"` call.

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke, competitor set, or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
TARGET="<first positional arg>"; COMPETITORS=("<all --vs args>")
COUNTRY="${COUNTRY:-us}"; WINDOW="${WINDOW:-last-90d}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
WITH_AMAZON_CONTEXT="${WITH_AMAZON_CONTEXT:-false}"  # default OFF; opt-in via --with-amazon-context
WITH_RANK_DELTA="${WITH_RANK_DELTA:-false}"          # default OFF; opt-in via --with-rank-delta (target only, 12-month series)
echo "$TARGET" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-competitive-teardown <domain> [--vs <c>...] [--country <iso-2>] [--window <w>] [--with-amazon-context] [--with-rank-delta]"; exit 1; }
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

- **Smoke**: `get-websites-website-rank`, target domain only, country=ww, bounded `start_date = "2_months_ago"`, `end_date = "latest"`. The smoke IS the target's `country="ww"` rank call for Call 1; reuse it, never re-issue it.
- **Secondary probe**: `get-websites-traffic-and-engagement`, target, country=us.
- **Pinned absence outcomes**: `get-websites-website-rank`: retarget the smoke and degrade rank rendering; `get-websites-traffic-and-engagement` or `get-websites-traffic-channels`: drop the dependent sections and continue (the teardown never aborts on a single tool); OPTIONAL tools: skip with one consolidated caveat line.
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED:
- get-websites-website-rank
- get-websites-traffic-and-engagement
- get-websites-traffic-channels

OPTIONAL (downgrade gracefully if absent):
- get-websites-similar-sites-agg
- get-websites-audience-overlap-agg
- get-websites-ppc-spend
- get-keywords-top-brands-agg (ONLY when `--with-amazon-context` is supplied; default skipped)

NOT CALLED by default: `get-traffic-channels-share` (~200 data credits per call) is partly redundant with `get-websites-traffic-channels` (~30 data credits, returns absolute visits per channel). The teardown derives share % client-side from absolute visits when needed: `share[ch] = visits[ch] / sum(visits)` per domain. For a 4-domain teardown that saves ~800 data credits. The long-tail-referrer rows the share tool exposes are not needed for the teardown's Channel breakdown section.

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. If a competitor-domain list is
already in conversation context and not covered by --vs args, offer enrichment.

If `--vs` was NOT supplied AND no competitor list was found in conversation
context, call `get-websites-similar-sites-agg(domain=target, limit=4)` to
auto-discover the top 4 competitors and use them as the implicit comp set.
Window rule per `similar-sites-window-constraint`: either omit start_date/end_date
entirely, or pass EXACTLY a 3-month span (`start_date = "2_months_ago"`,
`end_date = "latest"`); any other explicit span 400s.
Surface them in a one-line Caveat: "No competitors supplied; using top 4
similar sites: X, Y, Z, W. Name a different set if you want me to compare against specific competitors."
Cost: ~20 data credits at limit 4 (~5 per returned row). Call 4 would have made
this similar-sites call anyway, so the marginal cost when discovery fires
first is zero; the call is reused.

## Step 4: Plan the call sequence

Always-included (filter against capabilities):

- **Call 1**: `get-websites-website-rank` TWICE per domain: once with `country: "ww"` to populate the Global rank column (no `global_rank` field exists in the response; use `country_rank` from the `ww` call per `website-rank-no-global-field`), and once with `country: "<user-country>"` to populate the Country rank column. For the TARGET, the Step 2 smoke already IS the `ww` call; reuse its cached result and issue only the user-country call. Bound EACH call to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits per bounded call (~2 per month of window). Total: ~12 data credits per domain (~6 for the target thanks to smoke reuse). When the user-supplied country IS `ww`, make only ONE call per domain (none for the target) and use that response for both the Global and Country columns (the Country rank column collapses to "n/a" in that case; surface in Caveats).
- **Call 2**: `get-websites-traffic-and-engagement` per domain.
- **Call 3**: `get-websites-traffic-channels` per domain (absolute visits per channel). If a share % view is needed for the Channel breakdown table, derive client-side from these visits: `share[ch] = visits[ch] / sum(visits)`. Do NOT call `get-traffic-channels-share` for the rollup; ~200 data credits per call avoided, ~800 data credits for a 4-domain teardown.
- **Call 4**: `get-websites-similar-sites-agg` for target, `limit: 4` (the only limit this recipe documents for the call, matching the Step 3 discovery shape; omit dates, or pass exactly the 3-month `2_months_ago`/`latest` span per `similar-sites-window-constraint`; reuse the Step 3 result if discovery already ran).

Opt-in only when `--with-rank-delta` is supplied (default false):

- **Call 1b**: `get-websites-website-rank` for the TARGET ONLY with `country: "ww"` and a 12-month window (`start_date = <12 months before effective end_date>`, `end_date = <effective end_date from the Step 2 smoke>`). The `country="ww"` scope locks the YoY comparison to global rank (the only "true" global figure; see `website-rank-no-global-field`). Surfaces a YoY delta in the Rank row of the Rank + reach table. Cost: ~25 data credits for one extra year of data on the target. Competitors stay at the single-month bounded calls from Call 1; only the target gets the 12-month series. When `--with-rank-delta` is absent, only the latest rank shows and no delta column is rendered.

Optional, only if accessible:

- **Call 5**: `get-websites-audience-overlap-agg` for [target, ...competitors] (batched, 2-5 domains max).
- **Call 6**: `get-websites-ppc-spend` per domain.

Opt-in only when `--with-amazon-context` was supplied:

- **Call 7**: `get-keywords-top-brands-agg` for target's primary category keyword. Off by default because most DTC comp sets don't sell on Amazon at scale, and the call returns generic mass brands (Amazon Essentials, Hanes, Carhartt) that have nothing to do with the target's competitive set. Cost is ~120 data credits per teardown; supply `--with-amazon-context` only when the target IS a major Amazon seller.

## Step 5: Execute calls

Parallelize independent calls when supported. Per sw-foundation-core tool-call
economy rule #1, loop the non-agg tools (Calls 1, 2, 3, 6) across domains; only
Call 5 batches entities. Call 1 makes two calls per domain (one with
`country: "ww"` for global rank, one with the user country for in-country
rank) per `website-rank-no-global-field`; parallelize both within the
per-domain loop (the target needs only the user-country call; its ww data
is the Step 2 smoke). Per sw-foundation-core § Country-coverage gap
detection, the (tool, $country) batch is skipped if a prior call for any
tool in this turn detected the country-coverage gap envelope for $country;
fall back to the ww-only data for those domains. Call 7 (`get-keywords-top-brands-agg`) is the opt-in
`--with-amazon-context` call and runs once for the target's primary
category keyword when supplied; otherwise skipped entirely. Call 1b
(`--with-rank-delta`) runs once for the TARGET ONLY with `country: "ww"`
and a 12-month window; competitors stay at the single-month bounded
calls. Compute `delta_yoy = current_country_rank - country_rank_12_months_ago`
client-side from the two `country="ww"` responses for the target
(positive = lost ground, negative = gained ground in global rank; the
field name is `country_rank` since the response has no `global_rank` field,
but because the call passes `country="ww"` the value IS the global rank).
Per sw-foundation-render § error-rendering for transient failures. The teardown
does not abort on a single tool's failure.

## Step 6: Classify output intent

Use sw-foundation-render's intent-aware rules table; the result drives whether
§ citation block emits the handoff JSON appendix. Narrow questions render the short form.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} vs {competitors} | {country} | {window} | last_updated {meta.last_updated}*`. Drop duplicated parentheticals like `(US, Feb-Apr 2026)` from every subsequent section header.

Sections, answer-first per sw-foundation-render: Executive read, Rank + reach, Traffic + engagement, Channel breakdown (table + Unicode horizontal bars per domain), Audience overlap (table + Unicode asymmetry bars), PPC investment (table only by default), Similar sites discovered, Strategic insights (DEFEND / EXPOSE / PLAY), NEXT MOVES.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Channel breakdown:** Unicode horizontal bars per domain (group cumulative <15% slices as `(N more)`); render side-by-side. Replaces Mermaid pie.
- **Period-over-period visits / channel deltas (when available):** Unicode delta bars per channel with `▶`/`◀` direction caps + verdict label.
- **Audience overlap pair (when computed):** Unicode asymmetry bars (e.g., "27.7% of adidas visits nike; 13.6% of nike visits adidas").
- **PPC monthly trend:** table only by default (Mermaid xychart-beta is renderer-aware appendix per § visualizations).

Each visualization ALWAYS paired with the underlying data table.

### Executive read

Numbers-LIGHT. Maximum 3 sentences. Lead with the verdict label (MAJOR / MATERIAL / NOISE / etc.) and name ONE most-important finding in one sentence. Do NOT recapitulate every number that appears in tables below.

When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.

LEDE: the BIGGEST DELTA across the comp set when any period-over-period data is available in THIS run (the multi-month window already fetched, `--with-rank-delta`, or figures reused via § conversation-context; the teardown plans no extra prior-window calls). Label it `WITHIN NOISE` / `MATERIAL CHANGE` / `MAJOR CHANGE` per sw-foundation-render § expert-heuristics. If no PoP data, lede on the biggest current asymmetry. Static volume rank is the second sentence, NOT the lede.

Engagement quality score (`(1 - bounce_rate) * pages_per_visit`) renders as a per-domain line BELOW the executive read, not inside it.

For the Rank + reach section: when `--with-rank-delta` was supplied AND
Call 1b returned a 12-month series for the target, add a `YoY delta`
column to the Rank row. The target row carries the computed delta; every
competitor row renders `n/a` for that column (competitors stayed at the
single-month smoke). Footnote: "YoY delta is target-only; positive = lost
ground, negative = gained ground."
When the flag is absent, omit the column entirely.

For the Channel breakdown section: apply sw-foundation-render § error-rendering
pattern 4 (structural-zero) specifically when Paid Social returns exactly
`0.0` (the SPECIFIC case to watch for). Render `n/a [1]` and surface the
classifier-rollup Caveat. Similarweb's classifier often rolls paid social
into Display Ads, so a literal `0.0%` is structural-zero, not measured-zero.

For the PPC investment section: add a derived `$ / visit` column to the
PPC table when Call 6 (`get-websites-ppc-spend`) returned data AND Call 2
(`get-websites-traffic-and-engagement`) returned visits for the same
period. Compute per domain per period: `cost_per_visit = ppc_spend / visits_in_period`
(guard division by zero; render `n/a` when visits is zero or null).
This is the CAC-proxy metric defined in sw-foundation-render § expert-heuristics.
Footnote: "$/visit is a CAC proxy per sw-foundation-render § expert-heuristics.
Lower is more cost-efficient. Useful for cross-domain comparison within
this teardown; should NOT be compared across categories (different
category economics yield different baselines)."

### Strategic insights (DEFEND / EXPOSE / PLAY)

EXACTLY 3 bullets. Each bullet maxes at ~25 words, references a SPECIFIC NUMBER, and ends with a verb (`defend` / `steal` / `invest` / `cut` / `monitor`) plus `(confidence: HIGH | MEDIUM | LOW)` per sw-foundation-render § expert-heuristics.

- **THE EDGE** (target outperforms; rec verb: defend / invest).
- **THE EXPOSURE** (target most vulnerable; rec verb: defend / cut / monitor).
- **THE PLAY** (most copyable competitor move; rec verb: steal / invest).

If the data is too thin for any of the 3 buckets (target has < 30 days of
coverage, fewer than 2 requested competitors returned data (a deliberate 1v1 with data does not trigger), or every channel mix
returned `n/a`), trigger sw-foundation-render § expert-heuristics refusal-as-feature:
render `INSUFFICIENT SIGNAL` with the specific reason instead of the 3
bullets. NEVER ship a generic recommendation.

### NEXT MOVES

EXACTLY 2 bullets, each a backtick-quoted natural-language question the
user might ask in chat, derived from THIS run's findings. Per sw-foundation-render
§ citation block conversational-tone rule, NEVER emit `/sw-X` slash-commands
or `--flag` syntax here. The router auto-dispatches free-form questions.

Format each bullet: a backtick-quoted question first, then ONE sentence
explaining why this next move is relevant given the data above. Reference
specific domains, channels, time windows, or audience pairs discovered in
THIS teardown.

Question types to suggest, picked by the strongest signal in the render:

- **Channel-mix delta** when a competitor showed material PoP traffic shift:
  `"How did <competitor>'s channel mix shift over the last quarter?"`
  followed by one sentence on confirming whether the shift is sustained or a campaign blip.
- **Audience overlap** when more competitors look relevant than the user supplied:
  `"What's <target>'s audience overlap with <competitor-list>?"`
  followed by one sentence on testing duplication vs incremental reach.
- **Market size** when the target operates in a defined category:
  `"How big is the <category> market on Amazon?"` (or similar) followed by one sentence
  on sizing the addressable demand.
- **AEO audit** when the target has poor SERP visibility or rank shifted materially:
  `"Is <target> showing up in AI answers for <topic>?"`
  followed by one sentence on testing whether AEO posture matches the traffic / rank picture.

If `--with-rank-delta` was supplied AND the YoY delta on the target was MATERIAL
or MAJOR, prefer the AEO-audit question for the second bullet (rank shifts often
correlate with SEO/AEO posture changes).

Example output for an adidas-vs-nike teardown where the channel mix shifted +27% and nike was the strongest overlap candidate:

```
NEXT MOVES
- "How did adidas's channel mix shift over the last quarter?" Confirms whether the +27% Feb-Apr surge is sustained or a campaign blip.
- "What's adidas's audience overlap with nike, footlocker, dicks sporting goods, and new balance?" Tests whether nike is the dominant duplication or if footlocker / dicks shadow even more of adidas's audience.
```

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5).
Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when
intent classifies as `handoff`.

### data schema for sw-competitive-teardown handoff

```json
{
  "rank_table": {"<domain>": {"global": N, "country": M, "delta_yoy": null, "country_param_global": "ww", "country_param_country": "us"}},
  "traffic_engagement": {"<domain>": {"visits": N, "pages_per_visit": M, "avg_visit_duration": "...", "bounce": 0.0}},
  "channels": {"<domain>": {"Direct": N, "Organic Search": N}},
  "similar_sites": [{"domain": "...", "similarity_score": 0.0}],
  "audience_overlap_rows": [{"subset": ["..."], "overlap_unique_visitors": N, "union_unique_users": N}],
  "ppc_spend": {"<domain>": {"monthly": [{"date": "YYYY-MM-DD", "ppc_spend": N, "currency": "usd", "cost_per_visit": null}]}},
  "category_top_brands": null
}
```

`rank_table.<domain>.global` maps to the `country_rank` value from the
`country="ww"` call (no `global_rank` field exists in the response per
`website-rank-no-global-field`). `rank_table.<domain>.country` maps to
the `country_rank` value from the user-country call. When the user-supplied
country is `ww`, only one call is made and `country` is set to `null`.
`country_param_global` and `country_param_country` echo the country
parameters passed (always `"ww"` for global; the user country for
country, or `null` when collapsed).

`similar_sites[].similarity_score` maps from the live response field
`affinity` (0..1 scale; the response has NO `similarity_score` field, per
`response-field-name-lookup` and `similar-sites-window-constraint`).

`rank_table.<domain>.delta_yoy` is optional. It is `null` by default and
only populated for the TARGET when `--with-rank-delta` was supplied AND
Call 1b returned a 12-month series. Competitors always have
`delta_yoy: null`. Value semantics: positive = lost ground (global rank
worsened over 12 months), negative = gained ground. Computed as
`current_country_rank - country_rank_12_months_ago` from the two
`country="ww"` responses (the field name is `country_rank` even though
the value is the global rank, because the call passed `country="ww"`).

`ppc_spend.<domain>.monthly[].cost_per_visit` is the CAC-proxy ratio
derived client-side: `ppc_spend / visits_in_period`. Populated per period
when both PPC spend (Call 6) and traffic-and-engagement visits (Call 2)
are available for the same period. `null` when either is missing or
visits is zero. Lower = more cost-efficient; comparable across domains
within this teardown, NOT across categories.

`category_top_brands` is `null` by default. It is populated ONLY when
`--with-amazon-context` was supplied AND `get-keywords-top-brands-agg`
returned data. Shape when populated:

```json
{
  "primary_keyword": "<text>",
  "top_brands": [{"rank": 0, "brand": "<name>", "traffic_share": 0.0}]
}
```

## Edge cases

- **Target has no Similarweb coverage** (rank returns null): print "Similarweb has no coverage for {{target}}. Aborting teardown." Exit.
- **All competitors fail to resolve**: continue with target only; note in Caveats.
- **>4 --vs competitors supplied**: audience-overlap-agg accepts max 5 domains total. Run on the top-4-by-rank subset and note truncation in Caveats. Other (looped) tools run for the full set, capped at 10 with a top-N warning.

## Cowork persistent artifact (when 3+ competitors)

Per sw-foundation-render-cowork § Tier 3. SUPPLEMENTAL to the markdown answer; the markdown answer ALWAYS renders unchanged.

**Trigger.** One of:
- The comp set is target + 3 or more competitors (4+ total domains).
- The user prompt contains "dashboard", "interactive view", "explore", or "drill down".

**Slug.** `sw-teardown-<target-slug>-<yyyymm>`. Call `mcp__cowork__list_artifacts` first; if the slug exists, prefer `mcp__cowork__update_artifact` to refresh the page rather than creating a duplicate.

**Two-step usage.** Write the HTML to `~/sw-teardown-<target-slug>-<yyyymm>.html` with the `Write` tool, then call `mcp__cowork__create_artifact({id, html_path, description, mcp_tools})` with the absolute path. See sw-foundation-render-cowork § Tier 3 for the full call shape and CSP whitelist.

**Page structure (sections, in order):**

1. Header. Target + comp set + country + window + `meta.last_updated`. One line, matches the markdown header's identity columns.
2. Toolbar. Two button groups: "filter by rank threshold" (`< 1000`, `< 10k`, `< 100k`, all) and "sort by" (visits, overlap, channel-mix-lead). Buttons toggle `aria-pressed`; click handlers re-render the chart + grid. NOT a `<form>`; `form-action` is `'none'` in CSP.
3. Chart.js stacked bar of channel mix. One stacked bar per competitor; segments are the 10-channel taxonomy. Colors fixed per channel (Direct = gray, Organic Search = green, Paid Search = blue, Display Ads = orange, etc.).
4. Grid.js sortable comp-set table. Columns: `domain`, `global_rank`, `monthly_visits`, `channel_mix_lead` (the dominant channel + its share %), `audience_overlap_pct` (vs target; `n/a` for the target row). Sort persists via `localStorage` key `sort-by-column`.
5. Chart.js horizontal bar of `audience_overlap_pct` (each competitor against the target). Same color per competitor as the stacked bar above.
6. Mermaid `sankey-beta` diagram. ONLY rendered when `get-websites-audience-overlap-agg` returned subset rows: top-3 source-to-target flows (e.g., "rival-a -> target: 12.4M shared", "rival-b -> target: 8.1M shared"). Skip this section if the audience-overlap tool was inaccessible.

**Data binding contract (page calls these tools via `window.cowork.callMcpTool`):**

The Similarweb MCP server prefix is environment-specific (`mcp__similarweb__` for a standard `.mcp.json` install; a connector-specific id on Cowork). Substitute the prefix your session actually exposes for the Similarweb tools. Presence-filter the list per sw-foundation-core § tool-surface presence BEFORE substituting the prefix: drop any tool absent from the connector (the OPTIONAL overlap tool is the most commonly absent; its section then renders the "not exposed on this connector" placeholder); if `get-websites-website-rank` or `get-websites-traffic-and-engagement` is absent, skip the artifact entirely (stay Tier 1 with the skip caveat). Sections load independently (allSettled per sw-foundation-render-cowork). The page passes the surviving fully-qualified tool names in the `mcp_tools` array of the `create_artifact` call (Cowork uses this for permission gating):

- `mcp__similarweb__get-websites-website-rank`
- `mcp__similarweb__get-websites-traffic-and-engagement`
- `mcp__similarweb__get-websites-traffic-channels`
- `mcp__similarweb__get-websites-audience-overlap-agg`

The page derives channel share client-side from the absolute visits (`share[ch] = visits[ch] / sum(visits)` per domain), same as the markdown path; binding `get-traffic-channels-share` here would re-spend the ~200 credits per domain per page load that the markdown path deliberately avoids.

Call pattern on page load: loop the per-domain tools in parallel (`Promise.all` over the comp set) and single-call the `-agg` tool. Cache results in `localStorage` (5-minute TTL; matches Cowork's read cache).

**localStorage keys (persisted user preferences):**

- `sw-teardown-filter-min-rank` ("1000" | "10000" | "100000" | "all"; default "all").
- `sw-teardown-sort-by-column` ("visits" | "overlap" | "channel-mix-lead"; default "visits").
- `sw-teardown-sort-order` ("asc" | "desc"; default "desc").

**Rendering rules:**

- Apply the verdict ladder from sw-foundation-render § expert-heuristics to derived deltas in the page (engagement quality, channel-mix concentration). The labels MAJOR / MATERIAL / WITHIN-NOISE appear in the tooltip text on the Chart.js bars.
- Pair every chart with a Grid.js table beneath it (matches the markdown § visualizations pairing rule).
- `n/a` cells render exactly as `n/a` (not blank, not `--`, not `0`).
- Empty audience-overlap response: omit the section; render a note: "Audience overlap not accessible on this plan; section omitted."

**Skeleton HTML.** The artifact skeleton lives at `references/cowork/teardown-artifact.html`; Read it and substitute the data slots (the SRI hashes from Cowork's CSP, the comp set, country, window, and the actual data values).

The runtime LLM fills in the SRI hashes (Cowork provides them in the iframe's CSP `integrity` directives), the actual channel-mix dataset shape, and the renderOverlapBars / renderSankey bodies. The skeleton fixes the CONTRACT: head with three SRI-pinned CDN script tags, an async `load()` calling the four MCP tools via `window.cowork.callMcpTool`, and four render functions stitched together.

**Failure handling.** Per sw-foundation-render-cowork § Failure handling. If `mcp__cowork__create_artifact` is unavailable, emit one line in the `## Caveats` block ("Persistent dashboard skipped: artifact tool unavailable.") and continue with markdown-only.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this competitive teardown" -> `~~deck` (pptx by default). Layouts: title slide, Rank + reach, Traffic + engagement, Channel breakdown, Audience overlap, Strategic insights (DEFEND / EXPOSE / PLAY).
- "Export the comp-set table to a spreadsheet" -> `~~spreadsheet` (xlsx by default). One tab per section (rank, traffic, channels, overlap, ppc).
- "Send this teardown to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- mcp-tool-catalog-v1
- agg-variant-cost-savings
- partial-access-envelope-shape
- audience-overlap-tool-shape
- traffic-channels-tool-shape
- website-rank-no-global-field
- ppc-spend-shape
- response-field-name-lookup
- similar-sites-window-constraint
