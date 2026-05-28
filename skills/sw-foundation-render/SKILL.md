---
name: sw-foundation-render
description: Expert priors for Similarweb MCP server output rendering: intent-aware modes, citation block, error rendering, handoff JSON, expert heuristics, visualizations. Auto-loads on any Similarweb-shaped turn (web traffic, web rank, traffic-and-engagement, keywords overview, app downloads, brand sales, category performance, audience overlap, AEO audit, similar sites, PPC spend, channel mix, market size, or any specific Similarweb MCP tool name). Recipes cite its helper sections § citation block, § error-rendering, § handoff-json-schema, § expert-heuristics, § visualizations. Does not call MCP tools itself; pairs with sw-foundation-core and sw-foundation-data.
user-invocable: false
---
# sw-foundation-render: Similarweb MCP output rendering priors

Loads on every Similarweb-shaped turn. Does NOT call MCP tools. Carries the canonical render contract every user-invocable recipe delegates to.

## Intent-aware output rendering rules

Classify user intent FIRST, then render:

| Signal in user phrasing or environment | Mode |
|----------------------------------------|------|
| "table", "numbers", "list of" | `table` (tables-heavy, narrative trimmed) |
| "one-pager", "summarize", "exec read", "brief" | `narrative` (prose + key tables + collapsed sources) |
| "slide", "deck", "presentation" | `slide` (bullet structure, ready for pptx skill) |
| CSV in working directory that the recipe could enrich | `handoff` (append machine-readable JSON) |
| Default | `narrative` |

Every recipe output must include:
- A single-line **Sources** rollup (per-tool counts + total data credits, status suffix appended ONLY on failure or retry; see § citation block).
- A `## Caveats` block when any tool returned null, was unavailable, or hit a freshness limit.

## Helper sections (recipes reference these by name)

### § citation block

Every recipe ends its output with a single-line Sources rollup. When intent classifies as `handoff`, the Handoff JSON appendix follows; otherwise the Sources line is the last element.

**Token compression rules (apply across every recipe output):**

- **Header line.** ONE italic context line: `*{domain} | {country} | {window} | last_updated {date}*`. Drop duplicate parentheticals from every subsequent section header.
- **Executive read.** Numbers-LIGHT. Lead with a verdict label (MAJOR / MATERIAL / NOISE / CONCENTRATED / SAME POND / etc.) + ONE most-important finding. Max 3 sentences. Do NOT recap numbers from tables below.
- **Sources.** SINGLE LINE per-tool rollup (see part 1). No per-call table.
- **Caveats.** One bullet per real caveat (clamped windows, access denials, structural-zero rollups, brand absence, fallback modes). Drop duplicated context (window, country) the header already states. Drop "opt-in flag X not supplied" promotional lines: users see opt-in flags via `argument-hint` completion. Caveats are not for advertising features.
- **Strategic insights (DEFEND / EXPOSE / PLAY).** 3 bullets, ~25 words each, `(confidence: HIGH | MEDIUM | LOW)` at end.
- **NEXT MOVES.** 2 backtick-quoted natural-language questions, one-sentence rationale max each. See § conversational-tone below. Do NOT emit slash-commands or `--flag` syntax in NEXT MOVES.
- **Output-render targets (v0.1.1):** competitive-teardown ~2000-3000 chars, channel-mix ~2000-3000, market-size ~3000-4000, audience-overlap ~1500-2500, aeo-audit ~2500-3500, page-mix ~2000-3000, keyword-opportunity ~2000-3000. Single-line Sources + Unicode-first visualizations keep total render ~30-40% smaller than pre-compression iterations.

**1. Sources (single line, NOT a table, NOT collapsible).** Format:

`**Sources:** <total> data credits across <N> calls (<per-tool-rollup>).<optional-status-suffix>`

- `<total>` = sum of `data_credits` (mapped from each response's `meta.sw_coins`; missing/null = 0). Always emit even if 0. MCP-side field is `sw_coins`; the rename to "data credits" / `data_credits` happens at render/serialization time.
- `<N>` = total call count.
- `<per-tool-rollup>` = comma-separated `<count> <tool-suffix>` pairs. Drop the `get-` / `get-websites-` / `get-keywords-` / `get-categories-` / `get-apps-` / `get-brands-` / `get-traffic-` prefix and the `-agg` suffix (e.g., `4 rank`, `2 traffic-and-engagement`). Sort by descending count then alphabetical.
- `<optional-status-suffix>` = appended ONLY when something interesting happened. On FULL success (every call 2xx on first attempt, no retries) the line ENDS after the per-tool-rollup's closing period. No "All 200" noise.
  - Failure: ` <failed-count> failed: <tool-1>, <tool-2>.`
  - Retry-and-success: ` <retried-count> retried after rate-limit.` (or `... after transient error.` for non-429).
  - Both: failures first, then retries.
- If costs varied surprisingly within a tool group (e.g., one rank call ran the 36-month series at ~74 data credits), append one optional `*Note:* ...` line below.

Examples (full success / failure / retry):

```
**Sources:** 158 data credits across 12 calls (4 rank, 2 traffic-and-engagement, 2 channels, 1 similar-sites, 1 audience-overlap, 2 ppc-spend).
**Sources:** 84 data credits across 8 calls (2 rank, 2 traffic-and-engagement, 2 channels, 2 ppc-spend). 1 failed: get-websites-audience-overlap-agg.
**Sources:** ... 1 retried after rate-limit.
```

Per-call audit trail NOT pre-rendered; the AI client logs each call.

**2. Handoff JSON appendix.** Only when intent classifies as `handoff` (CSV in cwd that drove the input, downstream chaining detected, or explicit `--out json`). Format per § handoff-json-schema. The full per-call list ships in the handoff `sources` array. When intent is NOT `handoff`, the Sources line is the LAST element of the recipe output.

**Conversational tone, NEXT MOVES and recommendations are natural-language questions, NOT slash-commands or flags.** Users type free-form; the router auto-dispatches. All NEXT MOVES, Caveat unblock-suggestions, and "you could also" hints MUST be the QUESTION the user might ask. Flags live in `argument-hint` for users who want them; rendered output never promotes flag syntax.

- BAD: `/sw-channel-mix adidas.com --window 90d --vs-period previous-quarter`. GOOD: `"How did adidas's channel mix shift over the last quarter?"` Confirms whether the surge is sustained or a campaign blip.
- BAD: Pass `--with-rank-delta` for a 12-month YoY view. GOOD: (omit; the user asks for YoY if they want it.)
- BAD: Add `--campaign-id <uuid>` to lift from proxy to direct. GOOD: If you have an AI Tracker campaign UUID, share it and I'll lift this to direct measurement.
- BAD: Use `--country ww` for global. GOOD: I defaulted to US. Ask if you want a global view.

Composing a NEXT MOVES bullet: derive from data findings in the render. Phrase as the question the user might ask in chat. Reference specific domains, metrics, time windows, brands, or keywords from the current run. Each bullet: backtick-quoted question first, then ONE sentence on "why this next." 2 bullets max.

### § error-rendering

Four canonical patterns. Apply consistently:

1. **Tool returned null or empty payload:** render `n/a` in the affected
   cell. NEVER fabricate. NEVER infer from training data. The cell stays
   `n/a` and gets a one-line entry in the Caveats block:
   "no data for `<tool>` on `<target>` (window=<window>, country=<country>)".

2. **Tool returned non-2xx (5xx, timeout, validation error):** retry once
   with a 2-second pause. On second failure, render
   "unavailable this run" in the affected cell, add to Caveats:
   "`<tool>` was unavailable this run; rerun to retry."

3. **Tool skipped due to capability gate (per § capability-gating):**
   render "not accessible on this plan" in the affected cell, add to
   Caveats: "`<tool>` not in your plan; this row is best-effort without it."

4. **Tool returned a structural-zero (classifier limitation, not actual zero):**
   render `n/a` in the affected cell with a footnote `[1]` linking to the
   Caveats block where the classifier limitation is explained. Apply to any
   cell where the API returns exactly `0.0` AND the corresponding metric is
   known to suffer from a classifier-rollup limitation (e.g., Paid Social
   often rolls into Display Ads in Similarweb's `get-traffic-channels-share`).
   The Caveats entry explains the rollup: "Paid Social returned `0.0%` from
   `get-traffic-channels-share`; Similarweb's classifier often rolls paid
   social into Display Ads. Treat as structural-zero, not measured-zero."

5. **Systemic auth failure.** Trigger: when the FIRST 2 required tools called
   both return 403 with "missing the required claims" wording on the FIRST
   domain attempted. This indicates an account-level claims problem, not a
   per-domain restriction or transient error.

   **Action:**
   1. Stop the recipe immediately. Do NOT continue with subsequent required tools.
   2. Optional tools may be attempted ONCE each to detect partial access (e.g.,
      a PPC-spend tool can succeed while rank, traffic, and channels all fail).
      Cap at 1 attempt per optional tool.
   3. Render INSUFFICIENT SIGNAL verdict in the Executive read.
   4. The FIRST NEXT MOVE bullet MUST be a natural-language question that
      triggers a capability refresh, phrased as: `"Can you check which
      Similarweb tools I currently have access to and refresh the capability
      map?"` followed by one sentence explaining that the recipe could not
      proceed because the user's account appears to be missing claims for the
      required tools.
   5. The SECOND NEXT MOVE is optional and should be derived from any data
      that DID come back (e.g., if PPC spend succeeded for one domain, suggest
      extending that single-domain analysis).
   6. Caveats block lists EVERY tool that returned 403, distinguishing
      required vs optional.
   7. Sources block reflects the actual call count (only the calls that were
      actually issued before the short-circuit took effect, not the full
      pre-planned call count).

6. **Tool returned country-coverage gap (200 + empty data + "no data for requested country" envelope):** detect once per (tool, country) pair on the FIRST domain attempted. Render `n/a` in the affected country cells. Mark country-unavailable_this_run for this tool per § capability-gating. Pivot the recipe's country to ww for subsequent calls. Add ONE consolidated Caveats line: "Country `<X>` not on this plan; rendered worldwide. Affected tools: `<comma-separated list>`."

   If 2 or more required tools report country-coverage gap for the same country in this turn, ALSO add a higher-level header-line modifier: the recipe's header line context drops the country to `worldwide` instead of the user-supplied country, and the Executive read opens with a one-sentence acknowledgment that the country requested is not on this plan ("US data is not on your plan for the websites tools; this read is worldwide; reach out to your CSM if a country-specific view matters for the decision.").

A `## Caveats` block appears at the bottom of the recipe output if and only
if any of these fired. If no errors, no Caveats block.

### § handoff-json-schema

When intent classifies as `handoff`, recipes emit this canonical envelope as
a final JSON code block in the output:

```json
{
  "plugin": "similarweb",
  "version": "0.1.1",
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

The `version` literal `0.1.1` MUST match `.claude-plugin/plugin.json`. `sources[].data_credits` is the rename of MCP `meta.sw_coins` (see § citation block).

The outer envelope is shared across all recipes; the inner `data` object is recipe-specific (documented in each recipe's SKILL.md). When intent does NOT classify as `handoff`, recipes skip this block entirely; the Sources line is the last element of the output.

### § expert-heuristics

Quantified thresholds recipes can cite when interpreting raw data. These are
calibrated against real Similarweb behavior; do not soften without grounding.
Recipes that surface a derived verdict, a confidence label, or a strategic
recommendation MUST cite the relevant heuristic from this section instead of
inventing a threshold.

**Engagement profile heuristics:**
- Bounce <30% + pages/visit >5 = utility / login pattern (power-user site).
- Bounce 30-50% + duration >3min = engaged content / research site.
- Bounce >65% + duration <60s = intent mismatch (often paid landing pages or low-quality traffic).
- Bounce >65% + duration <1min = single-purpose entry.

**Channel mix red flags:**
- Direct >50% = strong brand OR bot / dark-traffic noise (sanity check).
- Paid Search >35% = margin-sensitive (cost shock will tank traffic).
- Organic Search <20% on a content-heavy site = SEO underinvestment.
- Any single channel >40% = concentration risk.

**Derived metrics:**
- Engagement quality score = `(1 - bounce_rate) * pages_per_visit` (higher = better).
- Cost per visit (CAC proxy) = `ppc_spend / visits` (cross-domain comparable; not cross-category).

**Period-over-period verdict ladder (use on every delta computation):**
- `|delta_pct| < 5%` -> WITHIN NOISE (do not invent root causes; report and stop).
- `5% <= |delta_pct| < 15%` -> MATERIAL CHANGE.
- `|delta_pct| >= 15%` -> MAJOR CHANGE (high stakes).

**Audience-overlap labels (use whenever computing pairwise overlap %):**
- `overlap >= 40%` -> SAME POND (heavy duplication; buying both = paying twice for many of the same eyeballs).
- `15% <= overlap < 40%` -> ADJACENT (meaningful overlap, distinct audiences).
- `5% <= overlap < 15%` -> COMPLEMENTARY (extends reach efficiently).
- `overlap < 5%` -> DISJOINT (essentially independent audiences).

**Market concentration (HHI from top-N revenue shares):**
- `HHI < 1500` = FRAGMENTED / competitive (room to enter).
- `1500 <= HHI < 2500` = MODERATE.
- `HHI >= 2500` = CONCENTRATED (entrenched incumbents).
- HHI from top-N only is an underestimate; absolute HHI rises when the long tail is added.

**Hypothesis calibration:** when a recipe surfaces a hypothesis, label `HIGH` / `MEDIUM` / `LOW` confidence based on evidence weight. NEVER deliver an uncalibrated hypothesis.
- HIGH = simplest explanation fitting ALL the data the recipe pulled (no contradicting signal).
- MEDIUM = fits the headline signal but has at least one ambiguity / alternative not ruled out by the data in hand.
- LOW = consistent with the data but other explanations fit equally well; or signal-to-noise is poor.
- DO NOT introduce external-world speculation (algorithm-update dates, news events) unless the user supplied that context. If you must, label `UNCONFIRMED EXTERNAL HYPOTHESIS` and put it LAST.

**Refusal-as-feature:** if signal is thin (no defensible hook, no recent data, no meaningful delta), REFUSE to render the recommendation section. A generic recommendation is worse than no recommendation. Render an `INSUFFICIENT SIGNAL` block with the explicit reason (e.g., "no winning SERP positions across audited keywords; no answer-box-adjacent features on any landing page; recommend re-run after domain accumulates SERP presence"). Sources line still ships.

### § visualizations

Render a chart when the data shape benefits from one, ALWAYS paired with the underlying table. Skip trivial 2-point or single-cell data.

**Unicode-first.** Primary target is Claude Code, which does NOT render Mermaid (users see raw `mermaid` code blocks: worse than no chart). Recipes emit Unicode block-character charts BY DEFAULT; Mermaid is an OPTIONAL appendix for renderer-aware callers (Cursor, Claude.ai artifacts). Use the block set `█▉▊▋▌▍▎▏` (full through 1/8); one full block ≈ 2 percentage points; cap at ~16-char width.

**Chart-type selection:**
- Ratios across 3+ categories (channel mix, top brands, market share): Unicode horizontal bars.
- Period-over-period deltas: Unicode bars with `▶`/`◀` caps + verdict label.
- Audience overlap N=2: Unicode asymmetry bars + a Unicode absolute-breakdown bar.
- Concentration / threshold (HHI 0-10000): Unicode bar with marker.
- Time series 3+ points: table only by default.
- Single-value / 2-point: NO chart.

**Channel mix (replaces Mermaid pie).** Group cumulative <15% slices as `(N more)`. Side-by-side per domain.

```
adidas.com (April 2026)
  Organic Search  33.6% ████████████████▏
  Direct          24.3% ███████████▋
  Paid Search     15.4% ███████▍
  Display Ads      9.4% ████▌
  Affiliates       6.6% ███▏
  Mail             4.5% ██▎
  (4 more)         6.7% ███▎
```

**Period-over-period delta bars.** Bar width = `|delta_pct| / 3` capped at 20 chars. Positive: full blocks + `▶`. Negative: `◀` + full blocks. Append verdict per § expert-heuristics.

```
Display Ads    +54.4%  ████████████████████▶  (MAJOR)
Direct         +12.1%  █████▶                 (MATERIAL)
Affiliates      -8.0%  ◀███                   (MATERIAL)
Referrals       -0.4%  ░                      (NOISE)
```

**Audience overlap asymmetry (N=2).**

```
27.7% of adidas visits also go to nike   ███████████████▏░░░░░░░░░░░
13.6% of nike visits also go to adidas   ███████▏░░░░░░░░░░░░░░░░░░░
```

**Audience overlap absolute breakdown (replaces Mermaid sankey, N=2).** Shared slice carries its audience-overlap label per § expert-heuristics.

```
Audience map (US, April 2026, total 30.68M)
  Nike-only     19.57M ████████████████████████████████
  Adidas-only    8.03M █████████████
  Shared         3.08M ████ (10.0% of union, ADJACENT)
```

**Top-N by share (replaces Mermaid pie for top brands / top sites).** Bar width scales to leader.

```
Top brands by revenue_share (Electronics, amazon.com)
1. Apple     28.6%  ██████████████▎
2. Beats     13.7%  ██████▉
3. Sony       5.7%  ██▉
(top-5 = 56.4% of revenue)
```

**HHI threshold position.**

```
HHI: 1,101  ████░░░░░░░░░░░░░░░░  FRAGMENTED
                                  ↑ 1500 MODERATE
                                  ↑ 2500 CONCENTRATED
```

**Hard rules:** always pair the chart with the underlying table; never visualize trivial single-comparison data; Unicode bars use `█▉▊▋▌▍▎▏` + `▶◀░` only; prefer one chart over many; do NOT default to Mermaid (Claude Code does not render it).

**Mermaid appendix (OPTIONAL).** For Cursor / Claude.ai artifacts: `pie`, `xychart-beta`, `sankey-beta`. Recipes do NOT emit Mermaid by default.

## Rich rendering tiers (Cowork-only)

Cowork supports three distinct render surfaces. Markdown is the primary contract everywhere; the two richer tiers are SUPPLEMENTAL and OPT-IN. The markdown answer renders unchanged across all three.

| Tier | Surface | Persistence | Tool | When |
|------|---------|-------------|------|------|
| 1 | Markdown + Unicode bars | Per-message | (none) | Default for every recipe. |
| 2 | Chat-side `.jsx` panel | Per-message (ephemeral) | `Write` (one `.jsx` file) | Recipe output has comparison shape but the user did not ask for a dashboard. |
| 3 | Persistent HTML artifact | Saved at `~/Documents/Claude/Artifacts/<slug>/index.html`, versioned (cap 100), shareable, `cowork-artifact://local/<slug>/index.html` URI | `mcp__cowork__create_artifact` (TWO-STEP: Write the HTML file, then call the tool with the absolute path) | User asks for a dashboard, persistent view, or recipe-specific high-dimensionality trigger fired. |

The three subsections below define each tier's contract.

### Tier 1: monospace + Unicode bars (baseline)

Already documented in § visualizations above. Every recipe emits this by default. Skip the richer tiers when the data is trivial (2-point, single-cell) or the user did not ask for an interactive view.

### Tier 2: chat-side .jsx panels (inline, ephemeral)

**Trigger.** One of:
- Recipe's intent classifier returns `interactive view` / `explore` / `dashboard` AND the user did NOT ask for a persistent artifact (they want a richer view inline, not a saved page).
- A comparison gets richer than 5 rows (e.g., a 10-channel period-over-period table) and a chart would carry the signal better than a Unicode bar.
- The recipe-specific trigger listed in that recipe's `## Cowork chat-side panel` section fired.

**How.** Use the `Write` tool to emit a SINGLE `.jsx` file with the path under `~/` (Cowork renders any file whose extension is `.md`, `.html`, `.jsx`, `.mermaid`, `.svg`, or `.pdf` inline as a chat panel). The runtime auto-loads these libraries before evaluating the file (no install / import map needed):

`lucide-react`, `recharts`, `d3`, `plotly`, `three`, `mathjs`, `lodash`, `papaparse`, `sheetjs`, `chart.js`, `tone`, `mammoth`, `tensorflow`, `shadcn/ui`.

Tailwind core utility classes work (the base set only; the JIT compiler is not running so arbitrary values like `w-[37px]` fail silently). Hand-roll any custom utility class as inline `style={{ }}`.

**Constraints.** No `localStorage` (chat-side artifacts are scoped to the message). No external scripts (the `.jsx` runtime is sandboxed). Component must default-export.

**Pattern.** One default-exported React component with `props.data` set at the top of the file as a literal object (the runtime LLM inlines MCP result values into the literal). Recharts is simplest for bar / line / area. `chart.js` for stacked bars. `plotly` for sankey / heatmap. No imports needed; the runtime resolves these from the auto-loaded module set.

Skeleton (Recharts bar chart, 30 lines):

```jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

const data = [
  { channel: 'Direct',        current: 24.3, prior: 22.0 },
  { channel: 'Organic Search', current: 33.6, prior: 38.2 },
  { channel: 'Paid Search',    current: 15.4, prior: 12.1 }
];

export default function Panel() {
  return (
    <div style={{ padding: 16, background: '#fff', color: '#111', fontFamily: 'system-ui' }}>
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Channel mix shift (current vs prior)</h2>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="channel" />
          <YAxis label={{ value: 'Share %', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="prior"   fill="#9ca3af" name="Prior" />
          <Bar dataKey="current" fill="#2563eb" name="Current" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

Write the file to `~/sw-<recipe>-panel.jsx`. Cowork renders it inline in the chat the moment the file is written; no separate tool call.

### Tier 3: persistent HTML artifacts via `mcp__cowork__create_artifact`

**Trigger.** One of:
- User asks for a dashboard, persistent view, interactive view, or "give me a dashboard".
- Intent classifier returns `mode=dashboard`.
- Recipe-specific high-dimensionality trigger fired (see each recipe's `## Cowork persistent artifact` section: 3+ competitors, 3+ overlap domains, 10+ market brands, etc.).
- Analysis the user is likely to return to (weekly competitive review, ongoing market tracker, recurring audit).

**How.** TWO-STEP:

1. Use `Write` to emit a self-contained HTML file. Recommended path: `~/sw-<recipe>-<target>-<yyyymm>.html`.
2. Call `mcp__cowork__create_artifact` with the file's absolute path.

Tool schema (the REAL schema, not the legacy `{title, content_type, content}` shape):

```
mcp__cowork__create_artifact({
  id:          "sw-<recipe>-<target-slug>-<yyyymm>",
  html_path:   "/absolute/path/to/the/file.html",
  description: "<one-line description shown to the user>",
  mcp_tools:   ["mcp__<server>__<tool>", "..."]
})
```

Field rules:
- `id` is a kebab-case slug; must contain at least one letter or digit. Use the slug pattern `sw-<recipe>-<target>-<yyyymm>` so repeat invocations REUSE the same artifact via `mcp__cowork__update_artifact` instead of creating duplicates. Call `mcp__cowork__list_artifacts` first to detect an existing slug.
- `html_path` is the absolute path the `Write` tool wrote. Do NOT pass content inline.
- `description` is visible in the artifact panel header. Keep it under one line.
- `mcp_tools` is the fully-qualified list of MCP tools the page will call via the JS bridge (see below). Cowork uses this for permission gating; missing tools fail at runtime.

**CSP that the iframe enforces (verbatim):**

```
default-src 'self'; script-src 'self' 'unsafe-inline' <whitelist>; style-src 'self' 'unsafe-inline' <whitelist-css>; img-src 'self' data:; font-src 'self' data:; connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'self'; webrtc 'block'
```

The script / style whitelist is exactly these three CDNs (SRI-pinned; do NOT change versions):

- `https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js`
- `https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js` + `https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css`
- `https://cdn.jsdelivr.net/npm/mermaid@11.10.0/dist/mermaid.min.js`

**JS bridge available inside the iframe (Cowork injects `window.cowork`):**

- `window.cowork.callMcpTool(name, args)` returns a Promise resolving to the MCP tool's response payload. Cowork enforces a 5-minute read cache (identical args = cached) and a 30-call-per-minute rate cap per artifact. All data flows through this bridge; `fetch` / `XHR` / `WebSocket` / `EventSource` are blocked by `connect-src 'none'`.
- `window.cowork.askClaude(prompt, data?)` runs a single-turn Haiku 4.5 inference (no tools, no system prompt). Use for natural-language summaries the user can ask for in-panel.
- `window.cowork.runScheduledTask(taskId)` triggers a scheduled task; requires a user click + native confirm dialog. Do NOT call from page load.

`localStorage` IS available and persists across reloads of the artifact. Use it to remember the user's filter and sort choices.

**Constraints persistent artifacts MUST respect:**
- No `fetch`, `XHR`, `WebSocket`, `EventSource`. All data goes through `window.cowork.callMcpTool`.
- No `<iframe>`, no `<object>`, no Tailwind CDN. Hand-roll utility CSS inline.
- HTML must be self-contained: inline CSS + JS, base64 or `data:` URIs for fonts and images. Max 10 MiB. Max 1M chars when sharing.
- `:root { color-scheme: light }` is mandated.
- Reload button is built into the panel header. Do NOT add your own.
- Slug pattern `sw-<recipe>-<target>-<yyyymm>` so monthly refreshes update the same artifact via `mcp__cowork__update_artifact`. Check via `mcp__cowork__list_artifacts` first; if the slug exists, prefer `update_artifact` over `create_artifact`.

Skeleton (~60 lines, Chart.js + Grid.js + one MCP call on load):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>sw-teardown-target-202605</title>
  <style>
    :root { color-scheme: light; }
    body { font: 14px/1.4 system-ui; margin: 0; padding: 16px; background: #fff; color: #111; }
    header { display: flex; gap: 12px; align-items: baseline; margin-bottom: 12px; }
    h1 { font-size: 16px; margin: 0; }
    .meta { color: #6b7280; }
    .grid-wrap { margin-top: 16px; }
    .toolbar button { padding: 4px 10px; margin-right: 6px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
    .toolbar button[aria-pressed="true"] { background: #2563eb; color: #fff; border-color: #2563eb; }
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" integrity="sha384-..." crossorigin="anonymous">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
</head>
<body>
  <header>
    <h1>Competitive teardown: target.com</h1>
    <span class="meta">US | last 90 days | last_updated 2026-04-30</span>
  </header>
  <div class="toolbar" id="toolbar"></div>
  <canvas id="channel-chart" height="200"></canvas>
  <div class="grid-wrap" id="comp-grid"></div>
  <script>
    const COMPETITORS = ['target.com', 'rival-a.com', 'rival-b.com'];
    const SORT_KEY = localStorage.getItem('sw-teardown-sort') || 'visits';
    async function load() {
      const ranks = await Promise.all(COMPETITORS.map(d =>
        window.cowork.callMcpTool('mcp__b2421424-145a-4829-8eea-9a34e56b8ade__get-websites-website-rank',
          { domain: d, country: 'ww', start_date: '2026-01-01', end_date: 'latest' })));
      const rows = COMPETITORS.map((d, i) => ({ domain: d, rank: ranks[i]?.data?.[0]?.country_rank ?? null }));
      new gridjs.Grid({ columns: ['Domain', 'Global rank'], data: rows.map(r => [r.domain, r.rank]), sort: true })
        .render(document.getElementById('comp-grid'));
    }
    load().catch(e => { document.body.insertAdjacentHTML('beforeend', `<pre>${e.message}</pre>`); });
  </script>
</body>
</html>
```

The runtime LLM fills in the actual SRI hashes (Cowork provides them in the iframe's CSP `integrity` directives), the real domain list, and the real call chain. The skeleton fixes the page STRUCTURE: head with three SRI-pinned CDN script tags, body with a toolbar + a Chart.js canvas + a Grid.js container, an async `load()` that pulls data via `window.cowork.callMcpTool`, and `localStorage` for user preferences.

### Failure handling

If `mcp__cowork__create_artifact` is unavailable (non-Cowork runtime, or the tool returns an error), emit a one-line note in the markdown `## Caveats` block: "Persistent dashboard skipped: artifact tool unavailable." The markdown answer continues unchanged. NEVER block the markdown delivery on artifact failures.

If the Tier 2 `.jsx` write fails (no `Write` permission on the path, disk error), drop to Tier 1 silently; the recipe's markdown render is identical with or without the panel.

### Hard rules

- Markdown output ALWAYS renders. Tier 2 and Tier 3 are SUPPLEMENTAL.
- NEVER include user-identifying or PII content in artifacts (CLAUDE.md global rule).
- Persistent artifacts MUST self-contain: no external network calls beyond the 3 whitelisted CDNs, no localhost references, no Tailwind CDN.
- Persistent artifacts MUST route all data through `window.cowork.callMcpTool`. `fetch` / `XHR` are blocked by CSP.
- Slug pattern is `sw-<recipe>-<target-slug>-<yyyymm>`. Check existing artifacts via `mcp__cowork__list_artifacts` before creating; prefer `update_artifact` for refreshes.

## What this skill does NOT do

It does not call MCP tools, produce visible output, or override sw-config / any recipe's hard rules. Tool-catalog priors, capability-gating, and bulk-input-from-context live in sw-foundation-core. Country / window / conversation-context normalization live in sw-foundation-data. Recipe and router skills load all three sub-foundations and act on them.

## Grounded assertions

This skill's behavior is live-validated against the following assertions in `tests/grounding-ledger.json`. Build-time `--validate` rejects unknown references.

- response-field-name-lookup
