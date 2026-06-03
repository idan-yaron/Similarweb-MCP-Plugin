---
name: sw-channel-mix
description: Channel mix breakdown for a target domain with optional period over period deltas, top inbound referrers, PPC investment, and ad network share. Use when the user asks about traffic channels, channel breakdown, paid versus organic split, PPC spend, ad network share, or channel mix shift over time on a single domain. Renders the live ten channel taxonomy from the traffic channels MCP tool. When the user asks for a period over period view the recipe runs two sequential calls because the flat time series cannot separate current from prior. Uses incoming referrals as the referrer source, renders PPC spend as a monthly scalar with no per channel split. Derives end date from a rank smoke. Delegates capability gating, citations, error rendering, and handoff JSON to sw foundation. Never fabricates per channel PPC attribution.
---
# sw-channel-mix

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations
- sw-foundation-render: § handoff-json-schema (when intent=handoff)

## Hard rules (NEVER violate)

- NEVER call `get-segments-traffic-sources` for the "top referral sources" section. That tool requires a `segment` ID (a user-defined audience segment), NOT a `domain`, and returns per-segment marketing-channel mix, NOT a referrer list. The right tool is `get-traffic-referrals-incoming`. See `tests/grounded/traffic-sources-shape.md`.
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize before any call.
- NEVER pass `end_date: <today>`. The server rejects future dates with `VALIDATION_ERROR / Dates not in range`. Derive effective `end_date` per sw-foundation-data § window-resolution (Step 0 rank smoke's `meta.last_updated`; currently `2026-04-30`).
- NEVER fabricate a per-channel breakdown of PPC spend from `get-websites-ppc-spend` output alone. The tool returns ONE `ppc_spend` scalar per month with NO Paid Search vs Paid Social vs Display split. If per-channel paid attribution is required, compose with `get-websites-traffic-channels` Paid Search + Paid Social + Display Ads visits and qualify the result as "estimated allocation by paid-channel visit share."
- NEVER label the referrals `share` column as "share of all traffic". `share` is fraction-of-inbound-referrals only; label the column "Share of referrals".
- NEVER assume `get-traffic-referrals-incoming` rows are pre-sorted by `share`. Sort client-side (or pass `sort=share&asc=false`).
- NEVER substitute one `get-websites-traffic-channels` call with a union date range for two calls when `--vs-period` is supplied. The tool returns a flat time series and cannot separate current from prior in one response.
- NEVER look for a `global_rank` field in `get-websites-website-rank` responses. Per `website-rank-no-global-field`, the response has `country_rank` only; pass `country: "ww"` to get global. When the Rank + reach section's "Global rank" column is required, make a separate `country: "ww"` call.
- NEVER pass `web_source: "mobile_web"` to `get-websites-ppc-spend`. Per spec Appendix C the constraint is `total` or `desktop` (the recipe relies on the server's default `total`, but if the call is explicit, do not pass `mobile_web`).
- NEVER pass `web_source: "total"` or `web_source: "mobile_web"` to `get-website-analysis-ad-networks-agg`. Per spec Appendix C the constraint is `desktop` only (the recipe relies on the server's default `desktop`, but if the call is explicit, do not pass any other value).

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
TARGET="<first positional arg>"; WINDOW="${WINDOW:-last-90d}"; VS_PERIOD="${VS_PERIOD:-}"
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
CURRENCY="${CURRENCY:-usd}" # one of {usd, eur, gbp, aud, jpy}; passed to ppc-spend
CURRENCY="${CURRENCY,,}"
WITH_SHARE_TOOL="${WITH_SHARE_TOOL:-false}"  # opt-in for get-traffic-channels-share long-tail referrer rows
echo "$TARGET" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-channel-mix <domain> [--window <range>] [--vs-period <previous>] [--country <iso-2>] [--currency <usd|eur|gbp|aud|jpy>] [--with-share-tool]"; exit 1; }
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

Apply sw-foundation-core § smoke-first sequencing AND § capability-gating in this exact order:

1. **Smoke probe (single call, sequential)**: Issue exactly ONE call to `get-websites-website-rank` for the target domain only, country=`$COUNTRY` (user-supplied or default `us`). Wait synchronously for the response. Do NOT issue any other call yet.
2. **Branch**:
   - 200: cache the rank result; this becomes the Step 0 "rank smoke" data Step 4 references for end_date derivation. Proceed to Step 2A.
   - 403 with "missing the required claims": issue ONE secondary probe to `get-websites-traffic-channels` for the target, country=`$COUNTRY`, single-month window. If that is also 403, render § error-rendering Pattern 5 (systemic auth failure) and STOP. If 200, mark website-rank as inaccessible_this_run, proceed to Step 2A with degraded rank rendering.
   - Country-coverage gap (a 400 `client_error` or a 200-empty response carrying a country-coverage message, per sw-foundation-core § Country-coverage gap detection): do NOT retry or mark fragile; pivot to `country=ww`, re-smoke ONCE at `ww`, and surface the worldwide caveat.
   - Other error: retry once. If still failing, mark website-rank as fragile-this-run and proceed.
3. **Step 2A**: apply lazy capability gating per sw-foundation-core § capability-gating using the smoke probe result plus any previously persisted ~/.similarweb-plugin/capabilities.json entries. Per-call access denial is handled inline via § error-rendering pattern 3 and appended to `tools_inaccessible` at the end of the run.

REQUIRED: `get-websites-website-rank`, `get-websites-traffic-channels`. OPTIONAL: `get-traffic-referrals-incoming`, `get-websites-ppc-spend`, `get-website-analysis-ad-networks-agg`. OPT-IN ONLY (when `--with-share-tool` supplied): `get-traffic-channels-share`.

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. sw-channel-mix is single-domain, so this rarely fires. If the conversation contains a list of domains and the user did not pin one, ask which domain to mix-analyze (single confirmation).

## Step 4: Plan the call sequence

| Step | Tool | Purpose |
|------|------|---------|
| 0 | `get-websites-website-rank` | Smoke + headline rank + derive effective `end_date` from `meta.last_updated`. Bound to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~2-4 data credits vs ~74 for the default 36-month series. Per `website-rank-no-global-field`, the response has NO `global_rank` field; render the in-country rank from this single call. If the Rank + reach section needs an explicit global rank column too, make a SECOND call with `country: "ww"` (also bounded the same way). |
| 1 | `get-websites-traffic-channels` | Current window |
| 2 | `get-websites-traffic-channels` | Prior window (only if `--vs-period`) |
| 3 | `get-traffic-channels-share` | OPT-IN ONLY (when `--with-share-tool` supplied). Long-tail referrer rows the traffic-channels tool does not surface. Default OFF: ~200 data credits per call avoided; for a typical single-domain run that's ~200 data credits saved. Share % view of the 10 channels is derived client-side from Step 1 visits (see Step 5 derivation). The long-tail-referrer data is partially recovered from Step 4 (`get-traffic-referrals-incoming`) which this recipe already calls, so skipping it does not lose unique signal. |
| 4 | `get-traffic-referrals-incoming` | Top referral sources by domain (only if accessible; `limit: 20`, sort client-side) |
| 5 | `get-websites-ppc-spend` | Paid investment (only if accessible; single `ppc_spend` scalar per month, NO channel split) |
| 6 | `get-website-analysis-ad-networks-agg` | Ad network breakdown (only if accessible; defaults: `ad_network_type: incoming, limit: 10`, 3-month window to cap cost at ~20 data credits) |

## Step 5: Execute

Step 0 runs first; derive effective `end_date` from its `meta.last_updated` per sw-foundation-data § window-resolution (`start_date = end_date - window_length`). Steps 1, 4, 5, 6 are independent given the resolved date range; parallelize. Step 2 only runs if `--vs-period`; can parallelize with Steps 4-6 since its params are independent. Step 3 only runs if `--with-share-tool` was supplied.

Compute period-over-period deltas client-side:
1. From Step 1 (current window): aggregate `data` into `dict[source_type] -> sum(visits)` across all returned month rows.
2. From Step 2 (prior window): same aggregation.
3. For each channel in the 10-channel taxonomy: `delta_visits = current[ch] - prior[ch]`, `pct_change = (current[ch] - prior[ch]) / prior[ch]` (guard division by zero, render `n/a` if `prior[ch]` is zero or null).
4. **Apply the verdict ladder per sw-foundation-render § expert-heuristics to the OVERALL traffic delta** (sum across channels): `|delta_pct| < 5%` -> `WITHIN NOISE`; `5% <= |delta_pct| < 15%` -> `MATERIAL`; `|delta_pct| >= 15%` -> `MAJOR`. The verdict label becomes the first word of the Executive read lede. When the verdict is WITHIN NOISE, the recipe outputs ONLY the headline + Sources block and STOPS rendering downstream narrative sections; do NOT invent root causes for noise. The data tables (channel breakdown, share, referrals, PPC) still render at the user's request, but the Strategic insights / NEXT MOVES sections are replaced by a one-line "Within-noise verdict; no root-cause hypothesis warranted at this delta."
5. If user supplies asymmetric windows (e.g. `--window quarter --vs-period previous-month`), normalize to average-visits-per-month per window and compare those, not raw sums.
6. Suppress channels below a visit-count floor (1% of total target traffic) from "biggest mover" candidacy in the executive read; % changes on small-base channels are not interesting.

Compute channel share % client-side from Step 1 visits (no separate tool call needed by default):
- `total_visits = sum(visits[ch] for ch in 10-channel taxonomy)` for the target's current window.
- For each channel: `share[ch] = visits[ch] / total_visits` (guard division by zero; render `n/a` when `total_visits` is zero or null).
- This replaces the default `get-traffic-channels-share` call (saves ~200 data credits per call). The derived share is mathematically identical to what the share tool would return for the 10-channel rollup. The share tool is only needed for its long-tail-referrer rows, which Step 4 (`get-traffic-referrals-incoming`) already surfaces.

Sort `get-traffic-referrals-incoming` rows client-side by `share` descending before rendering.

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, sw_coins, last_updated}`. Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

## Step 6: Classify output intent

Per sw-foundation intent-aware output rendering rules. Default: narrative.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Body output target ~2000-3000 chars.

**Header (FIRST line of output, ONE italic line):** `*{target} | {country} | {window} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Channel breakdown:** Unicode horizontal bars over the 10-channel taxonomy (group cumulative <15% slices as `(N more)`). Replaces Mermaid pie. Pair with the table.
- **Period-over-period deltas (when `--vs-period`):** Unicode delta bars per channel with `▶`/`◀` direction caps + verdict label (MAJOR / MATERIAL / NOISE).
- **PPC monthly trend:** table only by default (Mermaid xychart-beta is renderer-aware appendix per § visualizations).

Sections in order:

- `## Executive read` (numbers-LIGHT, max 3 sentences. When `--vs-period`: FIRST WORD is the overall verdict label per sw-foundation-render § expert-heuristics (`WITHIN NOISE`, `MATERIAL CHANGE`, `MAJOR CHANGE`); name the biggest mover (channel + delta + %) in one sentence. When no `--vs-period`: lede on the dominant channel AND a § expert-heuristics red flag if applicable (e.g., "Paid Search 38% = margin-sensitive"; "Direct 67% = strong brand OR bot noise"; "Organic Search 11% on a content-heavy site = SEO underinvestment"). If engagement metrics are present, cite the matching § expert-heuristics engagement profile in the second sentence. When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Rank + reach` (table: global rank, country rank, from Step 0). The Global rank column maps to the `country_rank` value from a `country="ww"` call (no `global_rank` field exists per `website-rank-no-global-field`). The Country rank column maps to the `country_rank` value from the `country="<user-country>"` call. When the user country IS `ww`, the Country rank column collapses to `n/a` and only one call is made.
- `## Channel breakdown`. 10-channel taxonomy table from Step 1, columns: `Channel`, `Visits (window)`. Values are ABSOLUTE visits aggregated across the window's months. Rows sorted descending by visits. The 10 channels (alphabetical for reference): Affiliates, Direct, Display Ads, Gen AI, Mail, Organic Search, Organic Social, Paid Search, Paid Social, Referrals. Apply sw-foundation-render § error-rendering pattern 4 (structural-zero) specifically when Paid Social returns exactly `0.0`: render `n/a [1]` and surface the classifier-rollup Caveat. Similarweb's classifier often rolls paid social into Display Ads, so a literal `0.0%` is structural-zero, not measured-zero.
- `## Period-over-period deltas` (only if `--vs-period`). Columns: `Channel`, `Current visits`, `Prior visits`, `Delta visits`, `% change`. Sorted by `abs(delta_visits)` descending.
- `## Channel share %`. Same 10-channel taxonomy, columns: `Channel`, `Share %`. By default, derived client-side from Step 1 visits per Step 5 (`share[ch] = visits[ch] / sum(visits)`) so no separate tool call is needed; saves ~200 data credits per run. If `--with-share-tool` was supplied AND Step 3 returned data, use Step 3 server-side values instead (only worth it for the long-tail-referrer rows the share tool surfaces). Apply sw-foundation-render § error-rendering pattern 4 (structural-zero) specifically when Paid Social returns exactly `0.0`: render `n/a [1]` and surface the classifier-rollup Caveat. Similarweb's classifier often rolls paid social into Display Ads, so a literal `0.0%` is structural-zero, not measured-zero.
- `## Top referral sources` (only if Step 4 accessible). Top 20 rows sorted client-side by `share` descending. Columns: `Referring domain`, `Share of referrals`, `Change vs prior period`. Context line: "Out of {{meta.total_count}} total referrers." `change` field rendered as % when present, `n/a` when null.
- `## PPC investment` (only if Step 5 accessible). Monthly time series table from Step 5. Columns: `Month`, `PPC spend`, `Currency`. Headline value above the table: "Total over window: {{sum(ppc_spend)}} {{currency}}." If `--vs-period`, render an adjacent "Prior window total: {{sum(prior)}} {{currency}}, delta = {{current - prior}}." (NO per-channel breakdown is rendered; the tool does not supply one.)
- `## Ad networks` (only if Step 6 accessible). Top 10 rows from Step 6, pre-sorted server-side. Columns: `Ad network`, `Share`, `Change`. Render `share` as % (0..1 -> %.1f). Render `change` as `n/a` when null.
- `## Root-cause hypotheses` (only if `--vs-period` AND the overall verdict was MATERIAL or MAJOR; SKIPPED entirely under WITHIN NOISE per Step 5 derivation #4). 2-3 ranked hypotheses for the biggest channel mover, each labeled `HIGH | MEDIUM | LOW` confidence per sw-foundation-render § expert-heuristics hypothesis calibration. Each hypothesis cites the SPECIFIC NUMBER from the data and a natural-language confirmation question the user might ask in chat (per sw-foundation-render § citation block conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax). For example: "Organic Search dropped 18%; HIGH confidence; could be algorithm update, ranking loss, or seasonality; confirm by asking 'Is `<target>` showing up in AI answers for its top keywords?'". NEVER ship without confidence labels. NEVER introduce external-world speculation (algorithm-update dates, news events) the user did not supply; if you must, label it `UNCONFIRMED EXTERNAL HYPOTHESIS` and put it LAST.
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the strongest signal in the render:
  - **Competitive teardown** when a competitor (e.g. top inbound referrer or
    dominant SERP player surfaced via referrals) is the natural next drill-in:
    `"How does <target> stack up against <top-competitor-list>?"` followed by
    one sentence on who shares the channel-mix shift.
  - **Audience overlap** when a referral relationship looks exploitable:
    `"What's <target>'s audience overlap with <biggest-non-target-traffic-source>?"`
    followed by one sentence on testing whether the partnership is duplicative or incremental.
  - **AEO audit** when Organic Search is the dominant channel or moved materially:
    `"Is <target> showing up in AI answers for its top keywords?"`
    followed by one sentence on connecting AEO posture to the organic-search dependency.

  Reference specific domains and channels surfaced in THIS run.

  Under WITHIN NOISE verdict, replace with: "NEXT MOVES skipped under WITHIN NOISE; re-run later if a trend matters.")
- `## Caveats` (per sw-foundation-render § error-rendering, only if any tool returned null / was unavailable / was skipped / `end_date` was clamped).
- `## Sources` (collapsible). Last element of the output unless `intent=handoff`.
- `[optional] ## Handoff` (JSON, only when intent=handoff).

## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-channel-mix handoff

```json
{
  "rank": {"global": 0, "country": 0, "country_param_global": "ww", "country_param_country": "us"},
  "window": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "channels_current": {"Direct": 0, "Organic Search": 0, "Paid Search": 0, "Paid Social": 0, "Organic Social": 0, "Display Ads": 0, "Mail": 0, "Affiliates": 0, "Referrals": 0, "Gen AI": 0},
  "channels_prior": null,
  "channel_deltas": [{"channel": "<name>", "delta_visits": 0, "delta_pct": 0.0}],
  "channels_share_pct": null,
  "referrals_top": [{"domain": "<domain>", "share_of_referrals": 0.0, "change": 0.0}],
  "ppc": {"monthly": [{"date": "YYYY-MM-DD", "ppc_spend": 0.0, "currency": "usd"}]},
  "ad_networks": [{"network": "<name>", "share": 0.0, "change": 0.0}]
}
```

Field semantics:
- `channels_prior` is `null` unless `--vs-period` was supplied.
- `channels_share_pct` is populated by default from the client-side derivation (`share[ch] = visits[ch] / sum(visits)` from Step 1). If `--with-share-tool` was supplied AND Step 3 returned data, it is populated from the server response instead. The values are mathematically identical for the 10-channel rollup; the server tool only adds value for the long-tail-referrer rows (which sw-channel-mix surfaces via Step 4 `get-traffic-referrals-incoming` anyway).
- `referrals_top` rows are sorted client-side by `share_of_referrals` descending. `share_of_referrals` is fraction-of-inbound-referrals (0..1), NOT fraction-of-all-visits.
- `ppc.monthly` rows are one per month; NO per-channel decomposition. If composing with traffic-channels for "estimated allocation by paid-channel visit share", emit a separate `ppc.estimated_by_channel` block and qualify it in the rendered output.
- `ad_networks` rows: `share` is fraction-of-incoming-ad-network-traffic (0..1). `change` may be null.

## Edge cases

- **Target has no Similarweb coverage** (Step 0 rank returns null): print "Similarweb has no coverage for {{target}}. Aborting." Exit.
- **No `--vs-period`**: skip Step 2; skip the `## Period-over-period deltas` section; `channels_prior` and `channel_deltas` are null in handoff.
- **`get-websites-ppc-spend` access-denied at runtime**: skip Step 5; skip the `## PPC investment` section; note in Caveats: "PPC investment not accessible on this plan." `ppc` key is null in handoff.
- **`get-website-analysis-ad-networks-agg` access-denied at runtime**: skip Step 6; skip the `## Ad networks` section; note in Caveats: "Ad networks not accessible on this plan." `ad_networks` key is null in handoff.
- **`get-traffic-referrals-incoming` access-denied at runtime**: skip Step 4; skip the `## Top referral sources` section; note in Caveats. `referrals_top` key is null in handoff.
- **`get-traffic-channels-share` access-denied at runtime AND `--with-share-tool` was supplied**: skip Step 3; the `## Channel share %` section still renders from the client-side derivation (Step 1 visits); note the opt-in tool skip in Caveats. `channels_share_pct` is populated from the derivation, not null.
- **User-supplied `end_date` is beyond `meta.last_updated`**: clamp per sw-foundation-data § window-resolution and note in Caveats with the canonical "end_date clamped from <requested> to <meta.last_updated>" wording.
- **Full country name passed**: normalize per sw-foundation-data § country-normalization before any call. If not resolvable, ask one disambiguation question.
- **A channel absent in prior window but present in current** (rare; only on taxonomy revisions): render `delta = current[ch]`, `pct_change = new` (NOT `+inf` or division-by-zero error).
- **`meta.last_updated` differs between Step 1 and Step 2 calls** (e.g. month-end roll happened mid-recipe): unlikely in a single invocation; recipe records `last_updated` once from Step 1 and asserts Step 2 matches, else flag with `[!gap]` in the rendered output.

## Cowork chat-side panel (when --vs-period set)

Per sw-foundation-render-cowork § Tier 2. SUPPLEMENTAL to the markdown answer; the markdown answer ALWAYS renders unchanged.

**Trigger.** `--vs-period` was supplied (single domain, two time periods). The 10-channel period-over-period table is the recipe's signature output; a Recharts grouped-bar chart carries the delta direction + magnitude per channel more cleanly than 10 rows of Unicode delta bars.

**How.** Use the `Write` tool to emit a SINGLE `.jsx` file at `~/sw-channel-mix-vs-panel.jsx`. Cowork renders it inline in the chat the moment the file is written. NO `create_artifact` call needed; chat-side panels are ephemeral per message.

**Constraints.** No `localStorage` (chat-side artifacts cannot use it). No external scripts. Recharts is auto-loaded by the chat-side runtime; do not import from a CDN.

**Page structure (one Recharts `BarChart`):**

- 10 channels on the X axis (one bar group per channel: Direct, Organic Search, Paid Search, Paid Social, Organic Social, Display Ads, Mail, Affiliates, Referrals, Gen AI).
- Two bars per channel: `current` (the Step 1 window) and `prior` (the Step 2 window). Y axis is share % (derived client-side from visits per sw-channel-mix Step 5 derivation).
- Delta-direction color coding (applied to the `current` bar via the `fill` prop on each cell):
  - `delta_pct_points >= +1.0` (current up by at least one percentage point) -> green (`#10b981`).
  - `delta_pct_points <= -1.0` (down by at least one) -> red (`#ef4444`).
  - else -> gray (`#9ca3af`).
- Hover tooltip per channel: channel name, current %, prior %, `delta_pct_points` (the absolute percentage-point shift), `pct_change` (the relative % change), and the MAJOR / MATERIAL / WITHIN-NOISE classification per sw-foundation-render § expert-heuristics period-over-period verdict ladder (applied to `pct_change`, not `delta_pct_points`).

**Skeleton .jsx (the runtime LLM inlines the actual data values):**

```jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

// Inlined from Step 1 + Step 2 of sw-channel-mix execution.
// percent_share derived client-side per sw-channel-mix Step 5.
const data = [
  { channel: 'Direct',         current: 24.3, prior: 22.0 },
  { channel: 'Organic Search', current: 33.6, prior: 38.2 },
  { channel: 'Paid Search',    current: 15.4, prior: 12.1 },
  { channel: 'Paid Social',    current:  0.0, prior:  0.0 },
  { channel: 'Organic Social', current:  3.2, prior:  2.8 },
  { channel: 'Display Ads',    current:  9.4, prior:  6.1 },
  { channel: 'Mail',           current:  4.5, prior:  4.7 },
  { channel: 'Affiliates',     current:  6.6, prior:  7.2 },
  { channel: 'Referrals',      current:  2.4, prior:  6.4 },
  { channel: 'Gen AI',         current:  0.6, prior:  0.5 }
];

const enriched = data.map(d => {
  const deltaPp = d.current - d.prior;
  const pctChange = d.prior === 0 ? null : ((d.current - d.prior) / d.prior) * 100;
  let verdict = 'WITHIN NOISE';
  if (pctChange !== null) {
    const abs = Math.abs(pctChange);
    if (abs >= 15) verdict = 'MAJOR';
    else if (abs >= 5) verdict = 'MATERIAL';
  }
  return { ...d, deltaPp, pctChange, verdict };
});

const colorFor = d => (d.deltaPp >= 1.0 ? '#10b981' : d.deltaPp <= -1.0 ? '#ef4444' : '#9ca3af');

function TipBody({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{ background: '#fff', border: '1px solid #d1d5db', padding: 8, fontFamily: 'system-ui', fontSize: 12 }}>
      <div style={{ fontWeight: 600 }}>{row.channel}</div>
      <div>current: {row.current.toFixed(1)}%</div>
      <div>prior:   {row.prior.toFixed(1)}%</div>
      <div>delta:   {row.deltaPp >= 0 ? '+' : ''}{row.deltaPp.toFixed(1)} pp</div>
      <div>change:  {row.pctChange === null ? 'n/a' : `${row.pctChange >= 0 ? '+' : ''}${row.pctChange.toFixed(1)}%`}</div>
      <div style={{ marginTop: 4, fontWeight: 600 }}>{row.verdict}</div>
    </div>
  );
}

export default function Panel() {
  return (
    <div style={{ padding: 16, background: '#fff', color: '#111', fontFamily: 'system-ui' }}>
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Channel mix: current vs prior period</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={enriched}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="channel" angle={-30} textAnchor="end" interval={0} height={70} />
          <YAxis label={{ value: 'Share %', angle: -90, position: 'insideLeft' }} />
          <Tooltip content={<TipBody />} />
          <Legend />
          <Bar dataKey="prior"   fill="#9ca3af" name="Prior" />
          <Bar dataKey="current" name="Current">
            {enriched.map((d, i) => <Cell key={i} fill={colorFor(d)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

The runtime LLM replaces the `data` array values with the actual per-channel current + prior share % derived from the recipe's Step 1 and Step 2 responses. The skeleton fixes: Recharts component imports, color logic per § expert-heuristics, delta-direction `Cell` coloring on the current-period bar, and a custom tooltip body that names current / prior / delta-pp / pct-change / verdict.

**Failure handling.** Per sw-foundation-render-cowork § Failure handling. If the `Write` tool errors (no permission on the path, disk error), the recipe drops to Tier 1 silently; the markdown render is identical with or without the panel.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this channel-mix shift" -> `~~deck` (pptx by default). Layouts: title slide, Current channel share, Period-over-period deltas, Top referral sources, PPC investment, Ad networks, Strategic insights.
- "Export the channel-share table to a spreadsheet" -> `~~spreadsheet` (xlsx by default). Tabs: channel shares (current + prior), deltas, referrals, ppc, ad networks.
- "Send this channel-mix brief to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following assertions in `tests/grounding-ledger.json`. Build-time `--validate` rejects unknown references.

- traffic-channels-tool-shape
- channel-mix-period-comparison
- traffic-sources-shape
- ppc-spend-shape
- ad-networks-shape
- website-rank-no-global-field
- response-field-name-lookup
- partial-access-envelope-shape
