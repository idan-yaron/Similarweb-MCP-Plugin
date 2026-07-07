---
name: sw-foundation-render
description: Background helper for the seven Similarweb recipes, loaded via their Inherits block and on sw-router dispatch, never for trivial single metric lookups (the Step 0 carve-out exits first). Carries intent aware modes, insight first delivery, citations, error rendering, handoff JSON, expert heuristics, metric glossing, and Unicode bar visualizations; richer rendering ships in a separate Cowork only helper. Calls no MCP tools itself; pairs with sw-foundation-core and sw-foundation-data.
user-invocable: false
---
# sw-foundation-render: Similarweb MCP output rendering priors

Loads via each recipe's Inherits block and via sw-router dispatch. Does NOT call MCP tools. Carries the canonical render contract every user-invocable recipe delegates to.

## Intent-aware output rendering rules

Classify user intent FIRST, then render:

| Signal in user phrasing or environment | Mode |
|----------------------------------------|------|
| "table", "numbers", "list of" | `table` (tables-heavy, narrative trimmed) |
| "one-pager", "summarize", "exec read", "brief" | `narrative` (prose + key tables + collapsed sources) |
| "slide", "deck", "presentation" | `slide` (bullet structure, ready for pptx skill) |
| CSV in working directory that the recipe could enrich | `handoff` (append machine-readable JSON) |
| Default | `narrative` |

**Answer-first ordering (every mode).** The verdict or headline leads, supporting evidence (tables, charts, per-section detail) follows, and the compact closing blocks (Strategic insights, Caveats, NEXT MOVES, Sources, glossary footnotes) come last. Never open with method narration; the first content line after the header line is the answer. The early-headline contract and its supersession rule live in § insight-first delivery.

**Short form (narrow questions).** Depth is question-proportional. When the routed question is narrow (one metric, one comparison, a yes/no call), render the verdict plus compact evidence standalone: header line, verdict sentence (with its § expert-heuristics label when one applies), ONE compact table or chart, NEXT MOVES whose FIRST move offers the full report as a natural-language question, Sources line. A short form is roughly 400-800 chars total. Do NOT emit the full report by default.

Every recipe output must include:
- A single-line **Sources** rollup (per-tool counts + total data credits, status suffix appended ONLY on failure or retry; see § citation block).
- A `## Caveats` block when any tool returned null, was unavailable, or hit a freshness limit.

## Insight-first delivery

Every recipe surfaces a one-to-two line headline insight immediately after its first successful data-bearing call, BEFORE the remaining call plan executes. The user reads a real finding within one data call; the full analysis follows with no change in rigor. This section is the single owner of the headline contract: recipes cite their row in the class table below and do not restate it.

### Headline timing

- Render the headline as soon as the first successful data-bearing response arrives. Do NOT wait for the parallel batches; the headline precedes every remaining planned call.
- Format: one to two lines opening with the bold label `**First read:**`, derived ONLY from fields the response in hand actually carries.
- The headline binds to the first successful data-bearing call WHATEVER that turns out to be. After a smoke retarget (sw-foundation-core § tool-surface presence), a country pivot, or a retry, the first call that succeeds with data is the headline source; speak to what that envelope returned.
- A metrics-free response is not data-bearing for headline purposes. The disambiguation-smoke class below confirms resolution in one line at the smoke and takes its headline from the first post-smoke data call.

### Headline classes (all 7 recipes)

Two classes:

- **Metric-smoke**: the smoke returns metrics; the headline derives from the smoke response itself.
- **Disambiguation-smoke**: the smoke is a resolution lookup carrying no metrics; emit a one-line resolution confirmation when it returns, then derive the headline from the first post-smoke data call.

| Recipe | Class | Headline source | Pinned headline format | Grounded in |
|--------|-------|-----------------|------------------------|-------------|
| sw-competitive-teardown | metric-smoke | rank smoke (target, country=ww) | `**First read:** {target} ranks #{country_rank} worldwide and #{category_rank} in {category}; head-to-head vs {competitors} follows.` | `website-rank-no-global-field` |
| sw-audience-overlap | metric-smoke | rank smoke (target, country=ww) | `**First read:** {target} ranks #{country_rank} worldwide and #{category_rank} in {category}; overlap across {N} domains follows.` | `website-rank-no-global-field` |
| sw-channel-mix | metric-smoke | rank smoke (target, user country, default us) | `**First read:** {target} ranks #{country_rank} in {country} and #{category_rank} in {category}; channel breakdown follows.` | `website-rank-no-global-field` |
| sw-page-mix | metric-smoke | rank smoke (target, user country, default us) | `**First read:** {target} ranks #{country_rank} in {country} and #{category_rank} in {category}; page-level mix follows.` | `website-rank-no-global-field` |
| sw-aeo-audit | metric-smoke | seo-overview smoke (seed keyword; search-click metrics) | `**First read:** "{keyword}": {unbranded_share}% of search clicks are unbranded and {informational_share}% informational, the share AI engines preferentially answer; full AEO audit of {target} follows.` | `aeo-seo-overview-shape` |
| sw-keyword-opportunity | metric-smoke | keywords-overview smoke (seed keyword) when present and accessible; else the first successful data-bearing call | `**First read:** "{keyword}" draws {volume} monthly searches at difficulty {difficulty} and ${cpc} CPC; gap scan vs {competitor} follows.` | `keywords-overview-3-month-max` |
| sw-market-size | disambiguation-smoke | categories-search smoke returns a category resolution list, no metrics; headline from the first post-smoke data call (canonically the category demand row, `get-categories-performance-agg`) | Resolution line: `Resolved "{input}" to Amazon category {category_path} (id {category_id}) on {tld}.` Headline: `**First read:** {category_name} on {tld}: {search_volume} searches and {total_clicks} category clicks over the cited window; brand concentration follows.` | `categories-search-resolution`, `categories-performance-shape` |

Class-table notes:

- **Rank-class headlines speak to standing, never scale.** The rank envelope carries `country_rank`, `category`, and `category_rank` ONLY; it has NO traffic field (per `website-rank-no-global-field`). Traffic scale enters the narrative only after the first traffic call returns. When the smoke ran at country=ww, the returned `country_rank` IS the global rank.
- **sw-keyword-opportunity fallback**: its overview smoke is an OPTIONAL tool. When it is absent or denied, the headline derives from whatever first successful data-bearing call the run produces (rank-class wording when that call is the rank tool), stating only that envelope's fields.
- **sw-market-size**: the post-smoke calls may run as a parallel batch; the headline derives from the first of them to return, with the pinned format above covering the canonical demand row. When a different call returns first, derive from its envelope under the same honesty constraints. The resolution line renders only once resolution is settled (auto-resolved or user-picked); a disambiguation question to the user is not a headline.

### Honesty constraints

The early headline obeys the same contract as the final render:

- NO fabrication: the headline states only fields present in the response it derives from. Null is null; nothing estimated, nothing recalled from training data.
- Derived metrics in a headline carry their gloss per § derived-metric glossing. Prefer raw envelope fields; a simple share of returned fields (e.g. unbranded share of clicks) carries its inline meaning as in the pinned formats.
- When the FIRST call fails, the documented error patterns fire INSTEAD of a headline: a country-coverage gap pivots per § error-rendering Pattern 6 and sw-foundation-core § Skip + pivot rule (no headline is invented from the failed call); a claims 403 follows the smoke branch ladder; absence follows Pattern 7. If a pivoted, retargeted, or retried call then succeeds, THAT response is the first successful data-bearing call and the headline derives from it, carrying the pivot context (e.g. worldwide standing instead of the requested country).

### Partial failure after the headline (precedence)

When the headline has rendered and two or more REQUIRED tools subsequently fail (403s, absences, and exhausted retries counted together):

- The final synthesis leads with a partial-data acknowledgment: the verdict opens with "Based on partial data:" followed by what the surviving data supports.
- NEXT MOVES leads with a re-run suggestion phrased per the conversational-tone rule (e.g. `"Can you re-run this analysis? Two required tools failed this run."`).
- Precedence: once the headline has rendered, this clause SUPERSEDES the aggregate-insufficiency Pattern 5 escalation (sw-foundation-core § tool-surface presence; § error-rendering Patterns 5 and 7) for that run. Data already shown is never retracted; an INSUFFICIENT SIGNAL verdict that erases an already-rendered headline is worse than an honest partial read. Pre-headline insufficiency is unchanged: when fewer than 2 REQUIRED tools are present and accessible before any headline rendered, escalate per Pattern 5 as documented.
- Every failure still gets its Caveats entry per § error-rendering, and the Sources line reflects the calls actually issued.

### Supersession

The final answer-first verdict supersedes the early headline:

- When the full data contradicts the headline (e.g. the standing read suggested parity but traffic shows a 3x gap), the synthesis states the corrected verdict; one clause may acknowledge the revision.
- The prior headline is NOT repeated verbatim in the synthesis, whether confirmed or contradicted; the synthesis re-derives its verdict from the complete picture.

## Helper sections (recipes reference these by name)

### § citation block

Every recipe ends its output with a single-line Sources rollup; when intent classifies as `handoff`, the § handoff-json-schema appendix follows it, otherwise Sources is the LAST element. Sources format: `**Sources:** <total> data credits across <N> calls (<per-tool-rollup>).<optional-status-suffix>` where total sums each response's `meta.data_credits_charged` (the live field, legacy fallback `meta.sw_coins`, renamed to data credits at render time; a call missing both is unknown not 0, see § citation block reference), the rollup is comma-separated `<count> <tool-suffix>` pairs (tool prefixes and `-agg` dropped; descending count then alphabetical), and the status suffix appears ONLY on failure or retry (no "All 200" noise).

**Output-render targets:** competitive-teardown ~2000-3000 chars, channel-mix ~2000-3000, market-size ~3000-4000, audience-overlap ~1500-2500, aeo-audit ~2500-3500, page-mix ~2000-3000, keyword-opportunity ~2000-3000; short form (narrow questions, any recipe) ~400-800, with the full report offered as a NEXT MOVES question instead of emitted. Single-line Sources + Unicode-first visualizations keep total render ~30-40% smaller than pre-compression iterations.

Conversational tone: NEXT MOVES, Caveat unblock-suggestions, and "you could also" hints are the natural-language QUESTIONS the user might ask, never slash-commands or `--flag` syntax (flags live in `argument-hint`). The full token-compression rules (header line, Executive read, Caveats discipline, Strategic insights shape, NEXT MOVES composition), the Sources field definitions with examples, and the BAD/GOOD tone table live in `references/citation-block.md`; Read it before rendering any recipe output.

### § error-rendering

Seven canonical patterns; the full pattern text (exact cell values, Caveats wording, escalation steps) lives in `references/error-rendering.md`. Read it the FIRST time any tool call in the run fails, returns empty, or is skipped, then apply consistently. Index: Pattern 1 null/empty payload (render `n/a`, never fabricate). Pattern 2 non-2xx (retry once after 2s, then "unavailable this run"). Pattern 3 capability-gate skip ("not accessible on this plan"). Pattern 4 structural-zero (`n/a` plus classifier footnote). Pattern 5 systemic auth failure (first 2 REQUIRED tools 403: stop, INSUFFICIENT SIGNAL verdict, capability-refresh question as the first NEXT MOVE). Pattern 6 country-coverage gap (message-gated, evaluated BEFORE Pattern 2: pivot to ww, ONE consolidated caveat, header renders the pivoted country). Pattern 7 not exposed on this connector (planning-time absence or message-gated unknown-tool error, evaluated BEFORE Pattern 2: zero retries, consolidated caveat naming connector-setting and plan-module causes; aggregate insufficiency escalates per Pattern 5 semantics). A `## Caveats` block appears at the bottom of the recipe output if and only if a pattern fired; no errors, no Caveats block.

### § handoff-json-schema

When intent classifies as `handoff`, recipes emit this canonical envelope as
a final JSON code block in the output:

```json
{
  "plugin": "similarweb",
  "version": "0.1.20",
  "recipe": "sw-<name>",
  "generated_at": "<ISO 8601 timestamp>",
  "inputs": {
    "target": "<domain | keyword | brand>",
    "competitors": ["..."],
    "country": "<country code or name>",
    "window": "<window descriptor>",
    "extra": {}
  },
  "data": {
    "<recipe-specific payload; each recipe documents its data schema in its own SKILL.md>"
  },
  "sources": [
    {"tool": "get-...", "params": {...}, "data_credits": N, "last_updated": "YYYY-MM-DD"}
  ],
  "caveats": ["..."]
}
```

The `version` literal `0.1.20` MUST match `.claude-plugin/plugin.json`. `sources[].data_credits` is filled from MCP `meta.data_credits_charged` (the live field), falling back to the legacy `meta.sw_coins`; a call missing both is recorded with `data_credits: null` (unknown, never 0). See § citation block.

The outer envelope is shared across all recipes; the inner `data` object is recipe-specific (documented in each recipe's SKILL.md). When intent does NOT classify as `handoff`, recipes skip this block entirely; the Sources line is the last element of the output.

Persistent export (platforms without Anthropic Cowork's rich-render tiers). On platforms without those tiers (Codex, Claude Code, Cursor, Claude.ai, Microsoft Copilot) the conversation is the only default surface, so there is no saved artifact. When the user asks for a persistent or shareable deliverable (a file, a saved report, an export), write one to the working directory with the `Write` tool: either this handoff JSON as `similarweb-<recipe>-<target>.json`, or a markdown copy of the rendered output as `similarweb-<recipe>-<target>.md`, then cite the saved path. Do this only on request, never write files unprompted, and when no export was asked for, offer it as one NEXT MOVES option.

### § expert-heuristics

Quantified verdict thresholds, calibrated against real Similarweb behavior; never soften one without grounding. Recipes that surface a derived verdict, a confidence label, or a strategic recommendation MUST cite the relevant heuristic instead of inventing a threshold. The full ladders (engagement profile, channel-mix red flags, period-over-period WITHIN NOISE / MATERIAL / MAJOR, audience-overlap SAME POND through DISJOINT, HHI concentration, derived-metric formulas, HIGH / MEDIUM / LOW hypothesis calibration, refusal-as-feature with the INSUFFICIENT SIGNAL block) live in `references/expert-heuristics.md`; Read it before computing any verdict, confidence label, or recommendation.

### § derived-metric glossing

Any metric the plugin DERIVES (computed client-side, not returned verbatim by the MCP) MUST carry a plain-language gloss every place it is surfaced; raw MCP metrics (visits, bounce_rate, country_rank, revenue_share) are self-explanatory and need none. NEVER render a derived score as a bare number anywhere a human reads it; a superlative label names the WINNER, not the metric, so the gloss is still required beside it. The canonical gloss table (engagement quality, PPC cost per visit, HHI, share of union, persona Jaccard, affinity) and the placement rules (markdown footnote on first appearance; no gloss in handoff JSON) live in `references/derived-metric-glossing.md`; Read it before rendering any derived metric.

- Tier 2 / Tier 3 artifacts (Cowork-only): every KPI card, ladder section, or chart axis that shows a derived metric carries the gloss as a caption directly under the label AND in the chart tooltip; a KPI card titled "Best engagement" with a bare `3.23` is the exact failure this rule prevents.

### § visualizations

Unicode-first: the primary target is Claude Code, which does NOT render Mermaid, so recipes emit Unicode block-character charts BY DEFAULT (`█▉▊▋▌▍▎▏` plus `▶◀░` only), ALWAYS paired with the underlying table, never for trivial single-comparison or 2-point data, one chart preferred over many; Mermaid is an OPTIONAL appendix for renderer-aware callers. The chart-type selection rules and the canonical formats with worked examples (channel mix, period-over-period delta bars, overlap asymmetry, overlap absolute breakdown, top-N share, HHI threshold position) live in `references/visualizations.md`; Read it before rendering any chart.

## Cowork rich-rendering tiers (separate skill)

Tier 1 (markdown + Unicode bars, defined in section visualizations above) is the universal baseline and renders on every platform. Tier 2 (chat-side `.jsx` panels via the `Write` tool) and Tier 3 (persistent HTML artifacts via `mcp__cowork__create_artifact`) are Cowork-only and live in the separate `sw-foundation-render-cowork` skill, which loads only when the user asks for a dashboard or persistent view, or when a recipe's high-dimensionality trigger fires. Recipes that emit Tier 2 or Tier 3 cite that skill's sections by name.

## What this skill does NOT do

It does not call MCP tools, produce visible output, or override sw-config / any recipe's hard rules. Tool-catalog priors, capability-gating, and bulk-input-from-context live in sw-foundation-core. Country / window / conversation-context normalization live in sw-foundation-data. Recipe and router skills load all three sub-foundations and act on them.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- response-field-name-lookup
- country-coverage-gap-shape
- audience-geography-shape
- unknown-tool-error-shape
- unknown-tool-error-shape-other-platforms
- website-rank-no-global-field
- categories-search-resolution
- categories-performance-shape
- aeo-seo-overview-shape
- keywords-overview-3-month-max
