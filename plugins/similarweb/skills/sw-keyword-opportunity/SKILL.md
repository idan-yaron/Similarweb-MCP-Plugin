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
- NEVER look for `volume` / `difficulty` / `CPC` fields on `get-website-analysis-keywords-agg`. Those fields live on `get-keywords-overview` only. Recipe combines both tools by looping the overview per gap keyword.
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

- **Smoke**: `get-keywords-overview` for the FIRST keyword from any user-supplied keyword list, else the target's brand term derived from the root domain; country=us. Reuse a 200 as the first enrichment row in Call 4 if the seed term ends up in the gap-keywords list.
- **Secondary probe**: `get-website-analysis-keywords-agg`, target domain, country=us, single-month window, `limit: 5`. If the smoke is denied but the secondary probe returns 200, ship the gap table without enrichment (recipe stays viable since enrichment is OPTIONAL).
- **Pinned absence outcomes**: `get-keywords-overview` (the documented smoke, itself OPTIONAL): retarget the smoke to `get-website-analysis-keywords-agg` and ship the gap table without enrichment (the claims probe is preserved; never skip the smoke); `get-website-analysis-keywords-agg`: ABORT with the caveat (it IS the gap table); `get-websites-website-rank`: degrade the headline and derive end_date from the smoke's `meta.last_updated`; `get-websites-keywords-competitors-agg`: skip Call 1 with its documented denial caveat.
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED: `get-websites-website-rank`, `get-website-analysis-keywords-agg`. OPTIONAL: `get-websites-keywords-competitors-agg` (surfaces alternative competitors; if denied the recipe still computes the gap from the explicit `--vs` competitor), `get-keywords-overview` (enriches the gap keywords with volume / difficulty / CPC; if denied the recipe ships the gap table without enrichment).

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. If `--vs` was not supplied and the conversation context contains a competitor list relevant to the target (e.g., from a prior /sw-competitive-teardown), reuse the FIRST competitor as the gap analysis target and surface in Caveats: "Competitor reused from prior /sw-<recipe>: `<competitor>`." If no prior competitor is in context and `--vs` is missing, ask one disambiguation question with explicit candidates.

## Step 4: Plan the call sequence

| Call | Tool | Purpose |
|------|------|---------|
| 0 | `get-websites-website-rank` | Headline rank for BOTH target and competitor + derive effective `end_date` from `meta.last_updated` (NOT this recipe's smoke; the Step 2 smoke is `get-keywords-overview`). Bound to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits per call (2 calls = ~12 total). |
| 1 | `get-websites-keywords-competitors-agg` | Top organic competitors of target, sanity-check that `--vs <competitor>` actually shares keywords. EXACT 3-month window required. ~3 sw_coins. |
| 2 | `get-website-analysis-keywords-agg` | Target's top organic keywords (limit=25). 3-month window. ~2 sw_coins. |
| 3 | `get-website-analysis-keywords-agg` | Competitor's top organic keywords (limit=25). 3-month window. ~2 sw_coins. |
| 4 | `get-keywords-overview` | LOOPED per top-10 gap keyword (where competitor wins but target doesn't), enriches with volume + difficulty + CPC + intent volumes. ~1 sw_coin per keyword (10 calls = ~10 sw_coins). |

Default total cost: ~30-40 data credits per run.

## Step 5: Execute

Call 0 runs first (2 parallel calls, one per domain). Derive effective `end_date` from the target's `meta.last_updated` per sw-foundation-data § window-resolution; the recipe uses the SAME EXACT 3-month window across all subsequent calls. Concretely: `end_date = 2026-04-30` (or current ceiling), `start_date = 2026-02-01`.

Calls 1, 2, and 3 are independent given the resolved window; parallelize.

Call 4 fans out per gap keyword and is itself independent across keywords; parallelize within the loop.

Client-side derivations after responses arrive:

1. **From Call 1 (competitor sanity check):** scan the response for the user-supplied `--vs` competitor. If present, the competitor is a genuine organic-keyword overlap (surface its `shared_keywords` % and `score` in the rendered output). If absent, surface in Caveats: "`<competitor>` does not appear in target's top-100 keyword competitors; gap analysis still runs but the keyword overlap with `<target>` may be thin."

2. **From Calls 2 + 3 (target vs competitor keyword sets):** intersect the keyword sets by exact-match on the `keyword` field. Build three buckets:
   - `gap_keywords`: keywords where competitor ranks (position present) but target does NOT (target absent from intersection's competitor side) -- competitor wins
   - `shared_keywords`: keywords where BOTH target and competitor rank (both present in intersection)
   - `target_wins`: keywords where target ranks but competitor does NOT

   MANDATORY caveat rendered with the Gap table: "Gap = absent from `<target>`'s top-25 organic keywords (the limit=25 pull); the target may still rank below that cutoff for these terms. Treat gaps as priority candidates, not proof of zero presence."

3. **ROI score per gap keyword** (after Call 4 enriches volume / difficulty / CPC):
   ```
   roi_score = volume_competitor_position_factor / max(difficulty, 1)
   ```
   where `volume_competitor_position_factor = volume * (1 - (competitor_position - 1) / 10)` clamped to [0, volume]. Higher = more attractive (high volume + competitor in lower position = easier to take). Sort gap keywords by ROI descending.

4. **For shared keywords (both rank):** compute `position_gap = competitor_position - target_position`. Positive = competitor outranks target on this keyword; defend by improving the target's position.

5. **For target wins:** keep these for the "DEFEND" recommendation; competitor doesn't rank.

6. **Intent clustering (optional):** group gap keywords by their `primary_intent` (Navigational / Informational / Transactional / Local / Job_Search). The Transactional cluster typically has the highest commercial value.

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, sw_coins, last_updated}`. Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

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
- `## Keyword gap (competitor wins)` (top 10 by ROI desc, after Call 4 enrichment. Columns: `Rank`, `Keyword`, `Competitor pos`, `Volume`, `Difficulty`, `Intent`, `ROI score`. Sort by ROI descending. Pair with Unicode bar visualization of ROI scores.).
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
  "gaps": [
    {
      "keyword": "<text>",
      "competitor_position": 0,
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
- `gaps` rows are sorted by `roi_score` descending. `roi_score` = `volume * (1 - (competitor_position - 1) / 10) / max(difficulty, 1)`. Higher = more attractive.
- `gaps[].volume`, `difficulty`, `cpc_low_bid`, `cpc_high_bid` come from `get-keywords-overview` (looped per top-10 gap keyword). If the overview tool was unavailable, these fields are null.
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
- keywords-competitors-shape
- keywords-analysis-shape
- keywords-competitors-exact-3-months
- keywords-overview-3-month-max
- website-rank-no-global-field
- partial-access-envelope-shape
