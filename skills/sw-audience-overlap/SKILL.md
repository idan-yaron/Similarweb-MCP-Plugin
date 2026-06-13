---
name: sw-audience-overlap
description: Audience overlap deep dive for a target versus up to four competitors, five domains max per the live tool. Use when the question is about audience overlap, shared visitors, audience duplication, same pond versus different pond, demographics or geography of a shared audience, or deduplicated reach across domains. Renders subset overlap with share of union, demographics, and deduplicated reach. Do not use when overlap is one angle inside a broader competitive read (use sw-competitive-teardown) or for single domain demographics (one MCP call suffices). Never fabricates audience data.
---
# sw-audience-overlap

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER pass more than 5 domains total (target + up to 4 --against) to `get-websites-audience-overlap-agg`. The live tool returns `VALIDATION_ERROR` above 5; if the user supplied more, rank each --against and keep top 4 by global rank.
- NEVER batch `get-websites-deduplicated-audience` across domains. The live tool takes a SINGLE `domain` per call; loop per domain.
- NEVER trust server row order in the subset-overlap response. Normalize each row by splitting `domains` on comma + sorting + rejoining, then sort client-side (descending subset size, then alphabetical).
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize before any call.
- NEVER fabricate audience data (per sw-foundation-render § error-rendering). If a tool returns null, render `n/a` and surface in Caveats.
- NEVER include user-identifying info from training data; only what is in the prompt or in the MCP responses.
- NEVER look for a `global_rank` field in `get-websites-website-rank` responses. Per `website-rank-no-global-field`, the response has `country_rank` only; pass `country: "ww"` to get global. The rendered "Global rank" column maps to the `country_rank` value from the `country="ww"` call.

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke, competitor set (--against), or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
TARGET="<first positional arg>"; AGAINST=("<all --against args>")
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
echo "$TARGET" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-audience-overlap <domain> [--against <c>...] [--country <iso-2>]"; exit 1; }
# Cap --against at 4 (audience-overlap-agg max is 5 total). If user supplied more, rank each --against and keep top 4 by global rank.
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

- **Smoke**: `get-websites-website-rank`, target domain only, country=ww, bounded `start_date = "2_months_ago"`, `end_date = "latest"`. The smoke IS the target's `country="ww"` rank call for Call 1; reuse it, never re-issue it.
- **Secondary probe**: `get-websites-audience-overlap-agg`, `domains = "<target>,<first --against domain>"` (2-domain batched call), country=us.
- **Pinned absence outcomes**: `get-websites-website-rank`: retarget the smoke and degrade rank rendering; `get-websites-audience-overlap-agg`: ABORT with the caveat (this recipe IS the overlap analysis); OPTIONAL tools: drop their sections with one consolidated caveat line (similar-sites absent with no supplied competitors keeps its documented ask-once-then-abort semantics).
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED: `get-websites-website-rank`, `get-websites-audience-overlap-agg`. OPTIONAL: `get-websites-demographics-agg`, `get-websites-geography-agg`, `get-websites-audience-interests-agg` (Call 5b Persona overlap section; if not accessible, omit the Persona overlap section and note in Caveats), `get-websites-deduplicated-audience`, `get-websites-similar-sites-agg` (used by Step 3 fallback when `--against` was not supplied AND no competitor list was found in context; if not accessible, the recipe asks the user once for competitors and aborts if none provided).

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. If no --against args, check conversation context for a competitor list; cap at 4.

If `--against` was NOT supplied AND no competitor list was found in conversation
context, call `get-websites-similar-sites-agg(domain=target, limit=4)` to
auto-discover the top 4 competitors and use them as the implicit `--against`
set. Window rule per `similar-sites-window-constraint`: either omit
start_date/end_date entirely, or pass EXACTLY the 3-month span
(`start_date = "2_months_ago"`, `end_date = "latest"`); any other explicit
span 400s. Surface them in a one-line Caveat: "No competitors supplied; using top 4
similar sites: X, Y, Z, W. Name a different set if you want me to compare against specific competitors."
Cost: ~20 data credits at limit 4 (~5 per returned row).

## Step 4: Plan the call sequence

| Call | Tool | Per-call scope |
|------|------|----------------|
| 1 | `get-websites-website-rank` | Looped per domain (target + each --against), TWO calls per domain per `website-rank-no-global-field`: once with `country: "ww"` for global rank and once with `country: "<user-country>"` for country rank. The TARGET's ww call is the Step 2 smoke; reuse it and issue only the user-country call for the target. Bound each call to `start_date = "2_months_ago"`, `end_date = "latest"` per sw-foundation-data § window-resolution; ~6 data credits per call (~12 per domain, ~6 for the target). When the user-supplied country is `ww`, make only one call per domain (none for the target) and set the Country rank column to `n/a`. |
| 2 | `get-websites-audience-overlap-agg` | Single batched call, `domains` comma-joined (2-5 total). Returns 2^N - 1 rows |
| 3 | `get-websites-demographics-agg` | Single call for target, `country` is ISO-2 |
| 4 | `get-websites-geography-agg` | Single call for target. ALWAYS pass `limit: 10` (the render uses top 10 only); the unbounded call costs ~699 data credits, the limit-10 form is estimated ~10x cheaper (estimate not yet re-grounded; treat surprises per § citation block cost note). Omit the limit ONLY if the user explicitly asks for full country coverage. |
| 5 | `get-websites-deduplicated-audience` | **Looped per domain** (one call per target + each --against); live tool takes a SINGLE `domain`. BUDGET GATE: ~259 data credits per domain (`deduplicated-audience-shape`), the dominant cost of this recipe. Run by default only when the analysis set is 2 domains; for 3+ domains, skip by default and offer in ONE line ("Deduplicated reach for N domains adds ~259xN data credits; want it?"), running it only on user consent. When skipped, render the section per the budget-skip edge case. |
| 5b | `get-websites-audience-interests-agg` | **Looped per domain** (one call per target + each --against); `limit: 15`. ~60 data credits per call per `audience-interests-shape`. Feeds the Persona overlap (Jaccard) section. Skipped if not accessible; omit section + note in Caveats. |

Calls 1-4 are independent; parallelize. Call 5 loops; parallelize within the loop. Call 5b also loops; parallelize within the loop and parallel with Call 5.

## Step 5: Execute

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, data_credits, last_updated}` (data_credits per sw-foundation-render § citation block: meta.data_credits_charged, fallback meta.sw_coins, null if both absent). Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped. Tolerate unknown meta keys as informational (e.g. `geography-agg` returns an extra `meta.query`).

### Call 5b derivations: Persona overlap (Jaccard) + Incremental reach decay

**Persona overlap (Jaccard).** After Call 5b returns, for each domain D in the analysis set (target + each --against), build:

```
interests[D] = {row.domain for row in response_for_D.data}   # top-15 by affinity
```

Then compute pairwise Jaccard for every pair (i, j) where i < j:

```
J(i, j) = |interests[i] ∩ interests[j]| / |interests[i] ∪ interests[j]|
shared_top5(i, j) = sorted(interests[i] ∩ interests[j])[:5]   # first 5 alphabetically for stable render
```

Label per pair per `audience-interests-shape`:
- `J >= 0.40` -> INTEREST TWIN
- `0.15 <= J < 0.40` -> ADJACENT
- `J < 0.15` -> DISTINCT

Sort pairs by Jaccard descending for the rendered table and bar chart.

**Incremental reach decay.** Pure client-side analysis of the existing Call 5 `get-websites-deduplicated-audience` output + Call 2 `get-websites-audience-overlap-agg` subset rows. No new MCP calls.

Algorithm (greedy by traffic size):
1. Sort the N domains by latest `total_deduplicated_audience` (from Call 5) descending. Call them `d_1, d_2, ..., d_N`.
2. `cum_reach[1] = audience[d_1]` (the largest domain's unique users).
3. For k in 2..N: `cum_reach[k] = union_unique_users` for the subset `{d_1, ..., d_k}` (lookup the matching subset row in Call 2's response after the alphabetical-sort normalization per the existing recipe rules; if the row is missing for any k, mark `cum_reach[k] = null` and render `n/a` for that step).
4. `marginal[k] = cum_reach[k] - cum_reach[k-1]` (the incremental unique users added by domain k).
5. `marginal_pct[k] = marginal[k] / cum_reach[k]` (the percentage incremental contribution).

Render rows for each k in order. If `marginal_pct[k] < 0.02`, append a "near zero" annotation to that row. The Step 7 render shows the decay as a Unicode bar chart per sw-foundation-render § visualizations.

## Step 6: Classify output intent

Per sw-foundation-render intent-aware output rendering rules. Default: narrative. Narrow questions render the short form per sw-foundation-render's short-form rule.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} vs {against_set} | {country} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Audience overlap, N=2 (the common case):** Unicode asymmetry bars (e.g., "27.7% of adidas visits nike; 13.6% of nike visits adidas") PLUS a Unicode absolute-breakdown bar (A-only / B-only / shared, with the shared slice labeled per § expert-heuristics: SAME POND / ADJACENT / COMPLEMENTARY / DISJOINT).
- **Audience overlap, N>=3:** Unicode horizontal bars over the pairwise overlaps (top 6 by share_of_union). Mermaid sankey-beta is renderer-aware appendix per § visualizations for callers whose renderer supports it.

Sections in order (answer-first per sw-foundation-render):

- `## Executive read` (numbers-LIGHT, max 3 sentences. LEDE on the MOST DISTINCT pair AND the MOST SIMILAR pair in one sentence with the audience-overlap label for each pair per sw-foundation-render § expert-heuristics (e.g., "Nike <-> Adidas = 10.9% COMPLEMENTARY tier; Nike <-> ASICS = 2.9% DISJOINT"). Demographic asymmetry, geographic concentration, and deduplicated reach delta land in subsequent sentences only if material. When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Rank + reach` (table: domain, global rank, country rank).
- `## Subset overlap`. NORMALIZE every row by splitting `domains` on comma, sorting, rejoining as canonical key. Server row order is NOT trusted; **derive `share_of_union`** as `overlap_unique_visitors / union_unique_users` (server does NOT supply it). **Apply the audience-overlap label per sw-foundation-render § expert-heuristics** to EVERY pairwise (2-element) row: `share_of_union >= 40%` -> `SAME POND`; `15% <= share_of_union < 40%` -> `ADJACENT`; `5% <= share_of_union < 15%` -> `COMPLEMENTARY`; `share_of_union < 5%` -> `DISJOINT`. The label is added as a column on the Pairwise subsets table. Then organize rows into visual subsection groups (instead of one flat table) in this fixed order:
  - `### All-N intersection` (the single row covering all input domains)
  - `### N-1 way subsets` (rows that drop exactly one domain; for N=4, that is 4 rows)
  - `### Pairwise subsets` (rows of exactly 2 domains; for N=4, that is 6 rows). Columns: `Domains in subset`, `Overlap unique visitors`, `Union unique users`, `Share of union`, `Label`. Label values are from the § expert-heuristics enum.
  - `### Singletons (for reference)` (1-element subsets, one per input domain)
  Within each subsection, sort rows alphabetically by the canonical subset key. The All-N, N-1 way, and Singletons subsections render their tables WITHOUT the `Label` column (the audience-overlap label is defined for pairwise overlaps only). For N=2 or N=3 input domains, some subsection groups will be empty; omit those subsections entirely. At N=2 the all-N row IS the pairwise row: render it ONCE under Pairwise with its Label column, omitting the All-N and N-1 way subsections as empty. For singletons, append the `[*]` footnote to the `Share of union` cell; the value will always be `100%` by definition. After the last subsection, render the footnote: "[*] Singleton subset rows render `share_of_union = 100%` by definition (overlap of a 1-element set is the set itself). This is correct math; the meaningful comparison is across 2+ element subsets." Plus a second footnote: "Label thresholds come from sw-foundation-render § expert-heuristics. SAME POND = duplicative audiences (>=40%); ADJACENT = meaningful overlap with distinct audiences (15-39%); COMPLEMENTARY = efficient incremental reach (5-14%); DISJOINT = essentially independent (<5%)."
- `## Target audience demographics`. TWO adjacent tables: age (6 buckets) and gender (male + female). NOT a crossed matrix; age and gender are independent dimensions in the server response. Shares as % to 1 decimal.
- `## Target audience geography`. Top 10 countries by `share` (defensively re-sort descending before slicing). Aggregate the remainder into one "Rest of world" row. Render `country_name` as label. Render `rank: 0` as `n/a` (server sentinel for "not ranked", not a true zero).
- `## Deduplicated audience`. Per-domain latest-row headline (since looped). For each domain: latest-month `total_deduplicated_audience` and the three device-mix shares (desktop-only, mobile-only, cross-device). If section skipped: "Deduplicated audience not accessible on this plan."
- `## Persona overlap`. ONLY if Call 5b returned data for at least 2 domains AND N >= 2 input domains. Top-15 audience interests per domain, pairwise Jaccard score per the Call 5b derivations (`J(A, B) = |interests_A ∩ interests_B| / |interests_A ∪ interests_B|`). Render in this order:
  - Subtitle: "Top-15 audience interests per domain, pairwise Jaccard score (set membership, no affinity threshold):"
  - Table. Columns: `Pair`, `Jaccard`, `Shared interests (top 5)`, `Label`. Rows are every unordered pair `(i, j)` where `i < j`, sorted by Jaccard descending. `Pair` rendered as `<domain_i> <-> <domain_j>`. `Jaccard` rendered to 2 decimals. `Shared interests` rendered as the first 5 alphabetical from the intersection, comma-separated; suffix `, ...` if more than 5 in the intersection; render `n/a` if the intersection is empty. `Label` from the § expert-heuristics-style enum: INTEREST TWIN (`J >= 0.40`), ADJACENT (`0.15 <= J < 0.40`), DISTINCT (`J < 0.15`).
  - Unicode bar chart (sw-foundation-render § visualizations). One row per pair, sorted by Jaccard desc. Bar width: round(`J * 16`) full blocks (`█`) + partial block from the fractional remainder; max bar width 16. Pad bars with `░` (light shade) to width 16 for column alignment. Format: `{pair_left_padded_to_24}  {jaccard_to_2_dp}  {bar}  {label}`.
  - Footnote: "Jaccard label thresholds: INTEREST TWIN >= 0.40 (heavily duplicative audience interests); ADJACENT 0.15-0.40 (meaningful overlap, distinct edges); DISTINCT < 0.15 (essentially independent interest pools). Top-15 interest set per domain comes from get-websites-audience-interests-agg pre-sorted by affinity desc (affinity scale 0-100); for typical high-traffic domains every top-15 row exceeds affinity 90, so the recipe uses raw set membership (no threshold) for Jaccard. Per audience-interests-shape, ~60 data credits per domain at limit=15."
  - If Call 5b was skipped entirely (capability denied), render as one line: "Persona overlap skipped: get-websites-audience-interests-agg not accessible on this plan." and surface in Caveats.
- `## Incremental reach decay`. ONLY if Call 2 returned data AND Call 5 returned data for at least 2 domains. Pure client-side analysis of the existing deduplicated-audience output (Call 5) plus audience-overlap-agg subset rows (Call 2). NO new MCP calls.
  - Subtitle: "Adding each next-largest domain to the deduplicated audience pool:"
  - Unicode bar chart (sw-foundation-render § visualizations). One row per domain in greedy traffic order (largest first per the Call 5b derivations). First row is the baseline; subsequent rows show marginal addition. Bar width: scale `marginal[k] / cum_reach[k_max]` to 20 blocks max; the first (baseline) row uses width 20 (full); subsequent rows use proportional width. Format: `{domain_label_padded_to_28}  {marginal_or_baseline_M}  {bar}  ({sign}{marginal_pct_to_1_dp}% {qualifier})`. Where `qualifier` is `baseline` for k=1, `incremental` for `marginal_pct >= 0.10`, `saturated` for `0.02 <= marginal_pct < 0.10`, `near zero` for `marginal_pct < 0.02`.
  - Saturation observation. One sentence inferring whether the set hits diminishing returns. Examples: "Diminishing returns kick in after <domain_k>; <domain_k+1> adds essentially no incremental unique reach." Or: "Every domain in the set contributes meaningful incremental reach (no saturation observed)." Or: "Saturation is severe: the second domain already adds < 10% incremental reach."
  - If any `cum_reach[k]` is null (subset row missing from Call 2's response after normalization), render the row as `n/a` and append: "Incremental row for {domain} unavailable: subset row missing from audience-overlap-agg response." to Caveats.
- `## Media-planning verdict`. Three sentences max, derived from the labels in Subset overlap:
  - If the goal is REACH MAXIMIZATION: name the DISJOINT and COMPLEMENTARY pairs (incremental-reach buys).
  - If the goal is FREQUENCY against a defined target: name the SAME POND pairs (hit the same humans repeatedly).
  - One-line caveat: "Overlap measures who VISITS both, not who CONVERTS on both. If the campaign targets a narrower segment (e.g. 25-34 women), the actual overlap on that segment is unknown from this data and may be higher."
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the labels surfaced in the Subset overlap section:
  - **Competitive teardown of a SAME POND pair**:
    `"How does <pair[0]> stack up against <pair[1]>?"`
    followed by one sentence on drilling into who wins inside the heavily-duplicated shared pool.
  - **Channel-mix on each member of the most-COMPLEMENTARY pair**:
    `"Where is <pair[0]>'s traffic coming from?"`
    followed by one sentence on comparing acquisition strategies of efficiently-additive sites.

  Reference the specific domain pairs labeled in THIS run's Subset overlap table.

  If no SAME POND pair, swap the first bullet for a competitive-teardown question
  on the target against the tightest non-target pair: `"How does <target> stack up against <tightest-non-target-pair>?"`)

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-audience-overlap handoff

```json
{
  "rank_table": {"<domain>": {"global_rank": 0, "country_rank": 0, "country_param_global": "ww", "country_param_country": "us"}},
  "subset_overlap_rows": [
    {"subset": ["<domain>", "<domain>"], "overlap_unique_visitors": 0, "union_unique_users": 0, "share_of_union": 0.0, "label": "SAME POND|ADJACENT|COMPLEMENTARY|DISJOINT"}
  ],
  "target_demographics": {
    "age": {"age_18_to_24_share": 0.0, "age_25_to_34_share": 0.0, "age_35_to_44_share": 0.0, "age_45_to_54_share": 0.0, "age_55_to_64_share": 0.0, "age_65_plus_share": 0.0},
    "gender": {"male_share": 0.0, "female_share": 0.0}
  },
  "target_geography": [{"country": "<alpha-2>", "country_name": "<name>", "rank": 0, "share": 0.0, "visits": 0.0}],
  "deduplicated_audience": {
    "<domain>": {
      "latest_total_unique_users": 0,
      "latest_date": "YYYY-MM-DD",
      "device_mix": {"desktop_only_share": 0.0, "mobile_web_only_share": 0.0, "desktop_and_mobile_web_share": 0.0},
      "time_series": [{"date": "YYYY-MM-DD", "total_deduplicated_audience": 0}]
    }
  },
  "persona_overlap": {
    "interests_by_domain": {"<domain>": ["<interest_domain>"]},
    "pairwise_jaccard": [
      {"pair": ["<domain>", "<domain>"], "jaccard": 0.0, "shared_interests_top5": ["<interest_domain>"], "label": "INTEREST TWIN|ADJACENT|DISTINCT"}
    ]
  },
  "incremental_reach_decay": [
    {"step": 1, "domain": "<largest_domain>", "cum_reach": 0, "marginal": null, "marginal_pct": null, "qualifier": "baseline"}
  ]
}
```

`deduplicated_audience` is keyed by domain (not flat) because the live tool loops per domain.

`persona_overlap` is `null` when Call 5b was skipped (capability denied) or when N < 2 input domains. `interests_by_domain` is keyed by domain; each value is the top-15 interest-domain set from `get-websites-audience-interests-agg`. `pairwise_jaccard` rows are sorted by `jaccard` descending; `shared_interests_top5` is the first 5 alphabetical entries from the pair's interest intersection (full intersection may be longer). `label` from the enum: INTEREST TWIN (>=0.40), ADJACENT (0.15-0.40), DISTINCT (<0.15) per `audience-interests-shape`.

`incremental_reach_decay` is `null` when fewer than 2 deduplicated-audience rows are available. Rows are ordered by greedy traffic size descending (step 1 = largest domain = baseline; subsequent steps are marginal additions). `marginal` and `marginal_pct` are `null` for the baseline row (step 1). `qualifier` enum: `baseline` (step 1), `incremental` (marginal_pct >= 0.10), `saturated` (0.02-0.10), `near zero` (< 0.02).

## Edge cases

- **Target has no Similarweb coverage** (rank null): print "Similarweb has no coverage for {{target}}. Aborting." Exit.
- **>4 --against supplied**: drop to top 4 by global rank (Step 1); note in Caveats.
- **Full country name passed**: normalize per sw-foundation-data § country-normalization before any call. If not resolvable, ask one disambiguation question.
- **`audience-overlap-agg` returns access-denied at runtime**: treat as runtime capability mismatch; suggest refreshing the capability map (a `/sw-config --refresh` run) in Caveats so the next session pre-filters this tool.
- **`deduplicated-audience` skipped for budget** (default for 3+ domains per the Call 5 budget gate, until the user consents): render section as "Deduplicated audience skipped (~259 data credits per domain x {{N}} domains). Say the word and I'll run it."; note in Caveats.
- **`audience-interests-agg` access-denied at runtime**: skip Call 5b; OMIT the `## Persona overlap` section; render a single-line note: "Persona overlap skipped: get-websites-audience-interests-agg not accessible on this plan." Add to Caveats. `persona_overlap` is `null` in handoff.
- **N=1 (target only, no --against supplied AND no auto-discovered set)**: skip Call 5b entirely; omit the `## Persona overlap` and `## Incremental reach decay` sections (pairwise Jaccard and marginal-reach are undefined for a single domain). The recipe still renders the rest.
- **Call 2 subset row missing for a (d_1, ..., d_k) combination**: render `marginal[k] = n/a` for that row in the Incremental reach decay section; surface in Caveats. Continue rendering subsequent rows (they consume the next subset row).

## Cowork persistent artifact (when 3+ domains)

Persistent artifact per sw-foundation-render-cowork § Tier 3. SUPPLEMENTAL; markdown ALWAYS renders unchanged.

**Trigger.** Target + 2 or more competitors (3+ total domains). N=2 renders better in markdown (asymmetry bars + absolute-breakdown bar).

**Slug.** `sw-overlap-<target-slug>-<yyyymm>`. Call `mcp__cowork__list_artifacts` first; if exists, prefer `update_artifact`.

**Two-step.** `Write` HTML to `~/sw-overlap-<target-slug>-<yyyymm>.html`, then `mcp__cowork__create_artifact({id, html_path, description, mcp_tools})`. See sw-foundation-render-cowork § Tier 3 for call shape + CSP whitelist. Presence-filter `mcp_tools` per sw-foundation-core § tool-surface presence: if `get-websites-audience-overlap-agg` is absent, skip the artifact (Tier 1 + skip caveat); the budget-gated deduplicated-audience tool absent just drops its section to the "not exposed on this connector" placeholder; sections load independently (allSettled).

**Page:**

1. Header (target + against-set + country + `meta.last_updated`).
2. Tier badge, computed from the HIGHEST pairwise `share_of_union` across all pairs (the worst case drives the buying decision): `SAME POND` (>=40%, red), `ADJACENT` (15-40%, amber), `COMPLEMENTARY` (5-15%, green), `DISJOINT` (<5%, gray). Per sw-foundation-render § expert-heuristics.
3. Mermaid `sankey-beta` of subset overlap. Top-N rows from `get-websites-audience-overlap-agg` ordered by descending `overlap_unique_visitors`. Each flow is `<domain_i> -> <domain_j>: <overlap_unique_visitors> shared`. Skip when agg returned < 3 subset rows.
4. Grid.js sortable matrix. Target as rows, competitors as columns, cell = `share_of_union %`. Diagonal renders `--` (a domain's overlap with itself is 100% by definition; uninteresting). Cell background colored by tier.
5. Chart.js horizontal bars of `total_deduplicated_audience` per domain. Sorted descending; bars labeled with absolute audience count.
6. Toolbar: "view mode" (matrix / sankey / dedup-bars), "sort by" (dedup / overlap-with-target). State in `localStorage`.

**MCP tools (prefix `mcp__similarweb__`; substitute the prefix your session exposes for the Similarweb tools, which is connector-specific on Cowork):** `get-websites-audience-overlap-agg` (single batched call; `domains` is the comma-joined set), `get-websites-deduplicated-audience` (looped per domain; live tool takes a single `domain`).

Page derives `share_of_union = overlap_unique_visitors / union_unique_users` client-side (server does NOT supply it; same rule as markdown render).

**localStorage:** `sw-overlap-view-mode`, `sw-overlap-sort-by`, `sw-overlap-sort-order`.

**Rules.** Diagonal renders `--`, never `100%`. `n/a` cells render `n/a` (not `0`, not blank). Sankey skipped when agg returned < 3 subset rows.

**Skeleton.** The artifact skeleton lives at `references/cowork/overlap-artifact.html`; Read it and substitute the data slots (the SRI hashes from Cowork's CSP, the domain set, country, window, and the actual data values).

Runtime LLM fills in SRI hashes (from Cowork's CSP `integrity` directives) and the three render functions. Skeleton fixes the contract: three SRI-pinned CDN scripts, async `load()` calling the two MCP tools, client-side `share_of_union` derivation, tier-class assignment via `tier()` per sw-foundation-render § expert-heuristics.

**Failure handling.** Per sw-foundation-render-cowork § Failure handling. If `create_artifact` is unavailable, one line in `## Caveats` and continue markdown-only.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this audience-overlap profile" -> `~~deck` (pptx by default). Layouts: title slide, Pairwise overlap, Persona overlap, Incremental reach decay, Demographics + geography, Strategic insights.
- "Export the overlap matrix to a spreadsheet" -> `~~spreadsheet` (xlsx by default). Tabs: pairwise overlap, subset rows, demographics, interests.
- "Send this overlap profile to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- similar-sites-window-constraint
- audience-overlap-tool-shape
- audience-overlap-recipe-shape
- audience-demographics-shape
- audience-geography-shape
- audience-interests-shape
- deduplicated-audience-shape
- website-rank-no-global-field
- response-field-name-lookup
- partial-access-envelope-shape
