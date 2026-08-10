---
name: sw-keyword-opportunity
description: Keyword gap analysis for a target domain, against a named competitor or auto discovering the closest organic rival when none is named. Use for keyword gaps, keyword or SEO opportunities for a domain, content gaps versus a rival, terms competitors win that the target loses, or ROI ranked keyword targets. Returns gaps, shared territory, wins, and ranked opportunities with volume, difficulty and CPC. Do not use for a whole domain SEO or AI visibility audit (use sw-aeo-audit), for page and folder mix (use sw-page-mix), or for plain keyword volume (one MCP call suffices).
---
# sw-keyword-opportunity

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution, § conversation-context
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER pass a window other than EXACTLY 3 months to `get-websites-keywords-competitors-agg`. Per `keywords-competitors-exact-3-months` and the live probe, the server returns HTTP 400 `VALIDATION_ERROR / Currently, this endpoint supports only an interval of 3 month(s) of data. Hence, start_date and end_date must span exactly 3 month(s).` 2- or 4-month windows are rejected.
- NEVER pass `traffic_source: "all"` to `get-websites-keywords-competitors-agg`. Per `keywords-competitors-shape`, only `organic` or `paid` is accepted; `all` is rejected.
- NEVER pass `web_source: "total"` to `get-websites-keywords-competitors-agg`. Only `desktop` or `mobile_web` is accepted. The recipe defaults to `desktop`.
- NEVER pass a window wider than 3 months to `get-website-analysis-keywords-agg` or `get-keywords-overview`. Both cap at 3 months per `keywords-overview-3-month-max`. The server returns HTTP 400 `VALIDATION_ERROR / Dates not in range` (probe confirmed for 4-month windows on `get-keywords-overview`).
- The PRIMARY enrichment path uses `get-keywords-latest-agg`, which carries `volume` / `difficulty` / `cpc` / `cpc_low_bid` / `cpc_high_bid` / `zero_clicks` INLINE on every keyword row (per `keywords-latest-agg-shape`), so the gap list is enriched WITHOUT a per-keyword loop. `get-website-analysis-keywords-agg` does NOT carry those fields; it is used only on the FALLBACK path, where `get-keywords-overview` is looped per gap keyword to supply them.
- `get-keywords-latest-agg` is LATEST-PERIOD-ONLY (last month, or last 28 days daily); NEVER pass it a multi-month window. `position` comes back null from it, so NEVER promise a keyword position on the primary path. `difficulty` is occasionally null per row (render n/a, never 0). `branded_type: non_branded` is a LOOSE filter, and loose in a specific way: the split is a literal SUBSTRING match on the domain's brand token, so it strips only keywords containing that string. On this tool that shows up as athlete / event / sponsorship proper nouns surviving (a competitor's gap list can include `alcaraz` or `uefa champions league`), so treat the gap list as candidate terms to scan, not a clean product-only set. The SAME mechanism is more damaging on `get-website-analysis-keywords-agg`, where a brand's own non-eponymous product line and third-party brand navigation both land in `non_branded`; see sw-foundation-core references/websites-catalog.md and `branded-flag-semantics` before reading any non-branded set as category demand.
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize per sw-foundation-data § country-normalization before any call.
- NEVER pass `end_date: <today>`. The server clamps to `meta.last_updated` and rejects future dates. Derive effective `end_date` per sw-foundation-data § window-resolution from the Call 0 rank smoke.
- NEVER treat the `url` field of `get-websites-keywords-competitors-agg` as a URL. Per `keywords-competitors-shape`, it is a DOMAIN despite the misleading name. Recipe renders it as a domain.
- NEVER treat `shared_keywords` from `get-websites-keywords-competitors-agg` as an integer count. Per `keywords-competitors-shape`, it is a FLOAT 0..1 (Jaccard-like overlap fraction). Recipe renders as percent.
- NEVER skip the competitor positional/flag input. Both `<domain>` AND `--vs <competitor>` are required; if missing, ask one disambiguation question.

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
TARGET="<first positional arg>"
COMPETITOR="${COMPETITOR:-}"  # required via --vs
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
echo "$TARGET" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-keyword-opportunity <domain> --vs <competitor> [--country <iso-2>]"; exit 1; }
if [ -z "$COMPETITOR" ]; then
  echo "Missing --vs <competitor>. Usage: /sw-keyword-opportunity <domain> --vs <competitor>"; exit 1
fi
echo "$COMPETITOR" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Invalid competitor domain"; exit 1; }
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

- **Smoke**: `get-keywords-latest-agg` for the target domain, country=`$COUNTRY` (resolved per sw-foundation-core § default-country resolution; documented default `us`), `branded_type: non_branded`, `limit: 5`. This IS the primary keyword+enrichment tool (Call 2); a 200 confirms the fast path and is reused, never re-called.
- **Secondary probe**: `get-website-analysis-keywords-agg`, target domain, country=`$COUNTRY`, single-month window, `limit: 5` (the FALLBACK path's gap-discovery tool). If the smoke is denied or absent but the secondary probe returns 200, run the fallback path (website-analysis-keywords-agg for the keyword sets, `get-keywords-overview` looped for enrichment).
- **Pinned absence outcomes**: `get-keywords-latest-agg` absent or denied: fall back to `get-website-analysis-keywords-agg` (gap sets) + `get-keywords-overview` (looped enrichment); record `enrichment_source: keywords_overview_loop`. BOTH `get-keywords-latest-agg` AND `get-website-analysis-keywords-agg` absent: ABORT with the caveat (no gap table possible). `get-websites-website-rank`: degrade the headline and derive end_date from the smoke's `meta.last_updated`. `get-websites-keywords-competitors-agg`: skip Call 1 with its documented denial caveat.
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED: `get-websites-website-rank`, and EITHER `get-keywords-latest-agg` (primary) OR `get-website-analysis-keywords-agg` (fallback gap source). OPTIONAL: `get-websites-keywords-competitors-agg` (surfaces alternative competitors; if denied the recipe still computes the gap from the explicit `--vs` competitor), `get-keywords-overview` (fallback-only enrichment, looped per gap keyword when the primary tool is unavailable).

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. If `--vs` was not supplied and the conversation context contains a competitor list relevant to the target (e.g., from a prior /sw-competitive-teardown), reuse the FIRST competitor as the gap analysis target and surface in Caveats: "Competitor reused from prior /sw-<recipe>: `<competitor>`." If no prior competitor is in context and `--vs` is missing, ask one disambiguation question with explicit candidates.

## Step 4: Plan the call sequence

PRIMARY path (`get-keywords-latest-agg` present):

| Call | Tool | Purpose |
|------|------|---------|
| 0 | `get-websites-website-rank` | Headline rank for BOTH target and competitor + derive effective `end_date` from `meta.last_updated`. Bound per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits per call (2 calls = ~12 total). |
| 1 | `get-websites-keywords-competitors-agg` | Confirm `--vs <competitor>` actually shares organic keywords with the target. EXACT 3-month window. ~3 data credits. |
| 2 | `get-keywords-latest-agg` | Target's top non-branded keywords WITH inline volume / difficulty / cpc / intent. `branded_type: non_branded`, `limit: 50`, latest month. ~5 data credits. |
| 3 | `get-keywords-latest-agg` | Competitor's top non-branded keywords WITH the same inline enrichment. `branded_type: non_branded`, `limit: 50`, latest month. ~5 data credits. |

Default total cost: ~15-25 data credits per run, ~5-6 MCP calls. No per-keyword enrichment loop: each gap keyword already carries its enrichment from Call 3.

FALLBACK path (`get-keywords-latest-agg` absent or denied): Calls 2 and 3 become `get-website-analysis-keywords-agg` (target, competitor; keywords + clicks + position, NO volume/difficulty/cpc), and a Call 4 loops `get-keywords-overview` per top-10 gap keyword for volume / difficulty / cpc (~1 data credit each). Record `enrichment_source: keywords_overview_loop`. Total ~30-40 data credits, as the pre-rework recipe.

## Step 5: Execute

Call 0 runs first (2 parallel calls, one per domain). Derive effective `end_date` from the target's `meta.last_updated` per sw-foundation-data § window-resolution. The keywords-competitors-agg call (Call 1) uses the EXACT 3-month window it requires; the primary keyword calls (Calls 2, 3) are latest-month-only (`get-keywords-latest-agg` ignores a multi-month window). Calls 1, 2, and 3 are independent; parallelize. On the fallback path, Call 4 fans out per gap keyword; parallelize within the loop.

Client-side derivations after responses arrive:

1. **From Call 1 (competitor sanity check):** scan the response for the user-supplied `--vs` competitor. If present, surface its `shared_keywords` % and `score`. If absent, surface in Caveats: "`<competitor>` does not appear in target's top-100 keyword competitors; gap analysis still runs but the keyword overlap with `<target>` may be thin."

2. **Gap, shared, and wins from Calls 2 + 3.** Match the two keyword lists by exact `keyword` string:
   - `gap_keywords`: keywords in the COMPETITOR's list (Call 3) absent from the TARGET's list (Call 2) -- competitor wins. On the PRIMARY path each gap row already carries `volume`, `difficulty`, `cpc`, `primary_intent`, and the competitor's `clicks` inline (no enrichment loop).
   - `shared_keywords`: keywords present in BOTH lists.
   - `target_wins`: keywords in the target's list absent from the competitor's.

   MANDATORY caveat with the Gap table: "Gap = absent from `<target>`'s top-50 non-branded keywords (the limit=50 pull) for the latest month; the target may rank below that cutoff or in another period. Treat gaps as priority candidates, not proof of zero presence." On the primary path, ALSO state the latest-month basis next to the recipe header window, and never render a keyword `position` (the primary tool returns it null).

3. **ROI score per gap keyword.**
   - PRIMARY path (clicks-based, position unavailable): `roi_score = competitor_clicks / max(difficulty, 1)`, where `competitor_clicks` is the gap keyword's `clicks` from Call 3 and `difficulty` its inline value; rows with null difficulty use `difficulty = 1` and render `n/a` in the Difficulty column. This uses the competitor's OBSERVED traffic for the term as the prize, a stronger signal than a position heuristic.
   - FALLBACK path (position-based, after the Call 4 overview loop): `roi_score = volume * (1 - (competitor_position - 1) / 10) / max(difficulty, 1)`, clamped to `[0, volume]`, using the competitor `position` from `get-website-analysis-keywords-agg` and `volume`/`difficulty` from the looped `get-keywords-overview`.
   Sort gap keywords by `roi_score` descending on both paths.

4. **For shared keywords:** PRIMARY path compares the competitor's vs the target's `clicks` for the term (leader = higher clicks; flag terms where the competitor leads by more than 2x as defensive priorities). FALLBACK path computes `position_gap = competitor_position - target_position` (positive = competitor outranks).

5. **For target wins:** keep these for the DEFEND recommendation; the competitor doesn't rank for them.

6. **Intent clustering (optional):** group gap keywords by `primary_intent` (Transactional usually carries the highest commercial value). Because `non_branded` is a loose filter, drop or label obvious athlete / event / sponsorship proper nouns rather than presenting them as product-category opportunities.

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, data_credits, last_updated}` (data_credits per sw-foundation-render § citation block: meta.data_credits_charged, fallback meta.sw_coins, null if both absent). Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

## Step 6: Classify output intent

Per sw-foundation-render intent-aware output rendering rules. Default: narrative. Narrow questions render the short form per sw-foundation-render's short-form rule.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} vs {competitor} | {country} | {window} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Gap keyword ROI bars:** Unicode horizontal bars over top-10 gap keywords sorted by ROI desc (cap width 16). Pair with the table.
- **Target vs competitor traffic-share split:** Unicode bar pair showing target's vs competitor's total share of clicks in this country.

Sections in order (answer-first per sw-foundation-render):

- `## Executive read` (numbers-LIGHT, max 3 sentences. Name the SIZE of the gap (count of gap_keywords + their total competitor volume), the BIGGEST gap keyword, and the verdict on opportunity. Use § expert-heuristics calibration: HIGH = clear gap with monetizable volume; MEDIUM = some gap but mixed; LOW = mostly shared territory with thin gaps. When the current recipe builds materially on a prior recipe in this conversation, prepend with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Rank + reach` (table with target and competitor country rank from Call 0; if user country is `ww`, render as one column).
- `## Keyword gap (competitor wins)` (top 10 by ROI desc. Columns: `Rank`, `Keyword`, `Competitor clicks`, `Volume`, `Difficulty`, `Intent`, `ROI score`. On the PRIMARY path `Competitor clicks` is the gap keyword's observed clicks from the competitor's keywords-latest-agg row, ROI is clicks/difficulty, and no keyword position is rendered (the tool returns it null). On the FALLBACK path the column shows the competitor's clicks from website-analysis-keywords-agg and ROI is the position-based formula. Render `Difficulty` as n/a where null. Sort by ROI descending. Pair with the Unicode bar visualization of ROI scores.).
- `## Shared territory` (table of keywords both rank for; columns: `Keyword`, `Target pos`, `Competitor pos`, `Position gap`. Highlight position gaps > 5 as defensive priorities. Top 10 by competitor traffic_share. If empty, skip with one-line note.).
- `## Target wins` (keywords where target ranks but competitor doesn't; columns: `Keyword`, `Target pos`, `Traffic share`. Top 10 by traffic_share. If empty, render a single line "No outright wins detected in top-25; target's strength is in shared territory, not exclusive keywords.").
- `## Strategic insights` (3 bullets per § expert-heuristics, labeled `DEFEND` / `EXPOSE` / `PLAY`, each ending with `(confidence: HIGH | MEDIUM | LOW)`. DEFEND = shared territory where target leads; EXPOSE = gap keywords with high ROI; PLAY = an intent cluster or content angle the data implies.).
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the strongest signal in the render:
  - **AEO audit** when the gap keywords lean informational / featured-snippet-worthy:
    `"Is <target> showing up in AI answers for <top-gap-keyword-or-cluster>?"` followed by one sentence on whether the gap is AI-engine-driven (AI Overview taking the traffic) or competitor-driven (competitor's ranking).
  - **Competitive teardown** when the competitor is a clearly bigger / different surface than expected:
    `"How does <target> stack up against <competitor> on traffic and audience?"` followed by one sentence on whether the keyword gap is the symptom of a larger competitive gap.
  - **Page-mix** when the target's gap concentrates in a specific content type:
    `"What's the content surface of <competitor> that <target> doesn't have?"` followed by one sentence on whether the competitor's anchor pages explain the gap.

  Reference specific gap keywords, intent clusters, or competitor names surfaced in THIS run.)
- `## Caveats` (per sw-foundation-render § error-rendering, only if any tool returned null / was unavailable / was skipped / the `--vs` competitor doesn't appear in target's keyword competitors / overview enrichment was partial / nested issues).
- Sources line per sw-foundation-render § citation block (single line, NOT a table, NOT collapsible). Last element of the output unless `intent=handoff`.
- `[optional] ## Handoff` (JSON, only when intent=handoff).

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-keyword-opportunity handoff

```json
{
  "target": "<domain>",
  "competitor": "<domain>",
  "rank": {
    "target_country": 0,
    "competitor_country": 0,
    "country_param": "us"
  },
  "window": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "competitor_relationship": {
    "shared_keywords_fraction": 0.0,
    "competitiveness_score": 0.0,
    "competitor_in_target_top100": true
  },
  "enrichment_source": "keywords_latest_agg | keywords_overview_loop",
  "gaps": [
    {
      "keyword": "<text>",
      "competitor_clicks": 0,
      "competitor_position": null,
      "volume": 0,
      "difficulty": 0,
      "cpc_low_bid": 0,
      "cpc_high_bid": 0,
      "primary_intent": "<intent>",
      "roi_score": 0.0
    }
  ],
  "shared": [
    {
      "keyword": "<text>",
      "target_position": 0,
      "competitor_position": 0,
      "position_gap": 0,
      "target_traffic_share": 0.0,
      "competitor_traffic_share": 0.0
    }
  ],
  "wins": [
    {"keyword": "<text>", "target_position": 0, "traffic_share": 0.0}
  ],
  "roi_score_top10": [
    {"keyword": "<text>", "roi_score": 0.0}
  ]
}
```

Field semantics:
- `competitor_relationship.shared_keywords_fraction` is the float 0..1 from `get-websites-keywords-competitors-agg` (Jaccard-like overlap coefficient; per `keywords-competitors-shape`, this is NOT an integer count).
- `competitor_relationship.competitiveness_score` is the `score` field from `get-websites-keywords-competitors-agg` (unbounded float).
- `competitor_relationship.competitor_in_target_top100` is `false` when the user-supplied `--vs` competitor does NOT appear in the top-100 returned by Call 1; signals a thin overlap.
- `enrichment_source` is `keywords_latest_agg` (PRIMARY path: enrichment inline, `competitor_clicks` populated, `competitor_position` null) or `keywords_overview_loop` (FALLBACK: `competitor_position` populated, enrichment from the looped overview).
- `gaps` rows are sorted by `roi_score` descending. PRIMARY: `roi_score = competitor_clicks / max(difficulty, 1)`. FALLBACK: `roi_score = volume * (1 - (competitor_position - 1) / 10) / max(difficulty, 1)`. Higher = more attractive.
- `gaps[].volume`, `difficulty`, `cpc_low_bid`, `cpc_high_bid` come INLINE from `get-keywords-latest-agg` on the primary path, or from the looped `get-keywords-overview` on the fallback. `difficulty` may be null per keyword (render n/a). `competitor_position` is null on the primary path.
- `shared` rows are sorted by competitor `traffic_share` descending. `position_gap` = `competitor_position - target_position` (positive = competitor outranks).
- `wins` rows are sorted by target `traffic_share` descending; up to 10 rows.
- `roi_score_top10` is a compact projection of the top 10 gaps, useful for downstream consumers that only need the ranking.

## Edge cases

- **Target has no Similarweb coverage** (Call 0 rank returns null): print "Similarweb has no coverage for `<target>`. Aborting." Exit.
- **Competitor has no Similarweb coverage**: print "Similarweb has no coverage for `<competitor>`. Aborting." Exit.
- **`get-websites-keywords-competitors-agg` access-denied at runtime**: skip Call 1; `competitor_in_target_top100` is null in handoff; note in Caveats: "Competitor-relationship sanity check skipped (tool unavailable); gap analysis runs but overlap context is missing."
- **`get-keywords-overview` access-denied at runtime**: skip Call 4; `gaps[].volume`, `difficulty`, `cpc_*` are null in handoff; render the gap table without enrichment; sort by competitor traffic_share instead of ROI; note in Caveats.
- **No gap keywords detected** (target and competitor have identical top-25 keyword sets, rare but possible for very tight competitors): render "No keyword gaps detected in top-25; both domains rank for the same head terms. Consider expanding the limit or comparing on a different country." Skip the gap table; render shared + wins only.
- **`--vs` competitor doesn't appear in target's top-100 keyword competitors** (Call 1 result): surface in Caveats: "`<competitor>` does not appear in `<target>`'s top-100 organic keyword competitors; gap analysis still runs but the overlap may be thin." Continue with the gap analysis.
- **User-supplied `end_date` is beyond `meta.last_updated`**: clamp per sw-foundation-data § window-resolution and note in Caveats with the canonical "end_date clamped from <requested> to <meta.last_updated>" wording.
- **Full country name passed**: normalize per sw-foundation-data § country-normalization before any call.
- **User supplies 2-month window via --window**: ignore the override and use exactly 3 months (the keywords-competitors-agg constraint forces it); note in Caveats: "Window forced to exactly 3 months because keywords-competitors-agg requires it."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- keywords-latest-agg-shape
- branded-flag-semantics
- keywords-competitors-shape
- keywords-analysis-shape
- keywords-competitors-exact-3-months
- keywords-overview-3-month-max
- website-rank-no-global-field
- partial-access-envelope-shape
