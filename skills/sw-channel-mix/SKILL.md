---
name: sw-channel-mix
description: Channel mix breakdown for a single domain with optional period over period deltas, top referrers, PPC spend, and ad network share. Use for traffic channels, channel breakdown, paid versus organic split, where traffic comes from, or whether paid or organic shifted over time. Renders the live ten channel taxonomy with period comparison on request. Do not use for multi domain channel comparisons (use sw-competitive-teardown) or keyword level paid analysis (use sw-keyword-opportunity).
---
# sw-channel-mix

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER call `get-segments-traffic-sources` for the "top referral sources" section. That tool requires a `segment` ID (a user-defined audience segment), NOT a `domain`, and returns per-segment marketing-channel mix, NOT a referrer list. The right tool is `get-traffic-referrals-incoming`. Per `traffic-sources-shape`.
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize before any call.
- NEVER pass `end_date: <today>`. The server rejects future dates with `VALIDATION_ERROR / Dates not in range`. Derive effective `end_date` per sw-foundation-data § window-resolution (the Call 0 rank smoke's `meta.last_updated`).
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

- **Smoke**: `get-websites-website-rank`, target domain only, country=`$COUNTRY` (resolved per sw-foundation-core § default-country resolution: user-supplied wins, else the account-coverage default, else `us`), bounded `start_date = "2_months_ago"`, `end_date = "latest"`. The smoke IS the Call 0 rank call; reuse it, never re-issue it.
- **Secondary probe**: `get-websites-traffic-channels`, target, country=`$COUNTRY`, single-month window.
- **Pinned absence outcomes**: `get-websites-website-rank`: retarget the smoke and degrade rank rendering; `get-websites-traffic-channels`: ABORT with the caveat (there is no channel mix without it); OPTIONAL tools: skip their steps with one consolidated caveat line.
- The smoke runs at the user country, so a country-coverage gap can hit the smoke itself: do NOT retry or mark fragile; pivot to `country=ww`, re-smoke ONCE at `ww`, and surface the worldwide caveat, per sw-foundation-core § Skip + pivot rule.
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED: `get-websites-website-rank`, `get-websites-traffic-channels`. OPTIONAL: `get-traffic-referrals-incoming`, `get-websites-ppc-spend`, `get-website-analysis-ad-networks-agg`. OPT-IN ONLY (when `--with-share-tool` supplied): `get-traffic-channels-share`.

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. sw-channel-mix is single-domain, so this rarely fires. If the conversation contains a list of domains and the user did not pin one, ask which domain to mix-analyze (single confirmation).

## Step 4: Plan the call sequence

| Call | Tool | Purpose |
|------|------|---------|
| 0 | `get-websites-website-rank` | The Step 2 smoke (reused, not re-called) + headline rank + derive effective `end_date` from `meta.last_updated`. Bound to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits vs ~74 for the default 36-month series. Per `website-rank-no-global-field`, the response has NO `global_rank` field; render the in-country rank from this single call. If the Rank + reach section needs an explicit global rank column too, make a SECOND call with `country: "ww"` (also bounded the same way). |
| 1 | `get-websites-traffic-channels` | Current window |
| 2 | `get-websites-traffic-channels` | Prior window (only if `--vs-period`) |
| 3 | `get-traffic-channels-share` | OPT-IN ONLY (when `--with-share-tool` supplied). Long-tail referrer rows the traffic-channels tool does not surface. Default OFF: ~200 data credits per call avoided; for a typical single-domain run that's ~200 data credits saved. Share % view of the 10 channels is derived client-side from Call 1 visits (see the Step 5 derivation). The long-tail-referrer data is partially recovered from Call 4 (`get-traffic-referrals-incoming`) which this recipe already calls, so skipping it does not lose unique signal. |
| 4 | `get-traffic-referrals-incoming` | Top referral sources by domain (only if accessible; `limit: 20`, sort client-side) |
| 5 | `get-websites-ppc-spend` | Paid investment (only if accessible; single `ppc_spend` scalar per month, NO channel split) |
| 6 | `get-website-analysis-ad-networks-agg` | Ad network breakdown (only if accessible; defaults: `ad_network_type: incoming, limit: 10`, 3-month window to cap cost at ~20 data credits) |

## Step 5: Execute

Call 0 runs first; derive the effective `end_date` from its `meta.last_updated`, then derive the current and prior windows with relative keywords per sw-foundation-data § window-resolution rule 7 (default 3-month window: current = `2_months_ago` through `latest`; prior = `5_months_ago` through `3_months_ago`; never client-side date arithmetic). Calls 1, 4, 5, and 6 are independent given the resolved date range; parallelize. Call 2 only runs if `--vs-period`; can parallelize with Calls 4-6 since its params are independent. Call 3 only runs if `--with-share-tool` was supplied.

Compute period-over-period deltas client-side:
1. From Call 1 (current window): aggregate `data` into `dict[source_type] -> sum(visits)` across all returned month rows.
2. From Call 2 (prior window): same aggregation.
3. For each channel in the 10-channel taxonomy: `delta_visits = current[ch] - prior[ch]`, `pct_change = (current[ch] - prior[ch]) / prior[ch]` (guard division by zero, render `n/a` if `prior[ch]` is zero or null).
4. **Apply the verdict ladder per sw-foundation-render § expert-heuristics to the OVERALL traffic delta** (sum across channels): `|delta_pct| < 5%` -> `WITHIN NOISE`; `5% <= |delta_pct| < 15%` -> `MATERIAL`; `|delta_pct| >= 15%` -> `MAJOR`. The verdict label becomes the first word of the Executive read lede. When the verdict is WITHIN NOISE, suppress the NARRATIVE sections only; do NOT invent root causes for noise. The data tables (channel breakdown, share, referrals, PPC) STILL render in this same response (the user invoked the recipe; the tables are the requested deliverable). The Strategic insights and NEXT MOVES sections are replaced by a one-line "Within-noise verdict; no root-cause hypothesis warranted at this delta."
5. If user supplies asymmetric windows (e.g. `--window quarter --vs-period previous-month`), normalize to average-visits-per-month per window and compare those, not raw sums.
6. Suppress channels below a visit-count floor (1% of total target traffic) from "biggest mover" candidacy in the executive read; % changes on small-base channels are not interesting.

Compute channel share % client-side from Call 1 visits (no separate tool call needed by default):
- `total_visits = sum(visits[ch] for ch in 10-channel taxonomy)` for the target's current window.
- For each channel: `share[ch] = visits[ch] / total_visits` (guard division by zero; render `n/a` when `total_visits` is zero or null).
- This replaces the default `get-traffic-channels-share` call (saves ~200 data credits per call). The derived share is mathematically identical to what the share tool would return for the 10-channel rollup. The share tool is only needed for its long-tail-referrer rows, which Call 4 (`get-traffic-referrals-incoming`) already surfaces.

Sort `get-traffic-referrals-incoming` rows client-side by `share` descending before rendering.

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, data_credits, last_updated}` (data_credits per sw-foundation-render § citation block: meta.data_credits_charged, fallback meta.sw_coins, null if both absent). Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

## Step 6: Classify output intent

Per sw-foundation-render intent-aware output rendering rules. Default: narrative. Narrow questions render the short form per sw-foundation-render's short-form rule.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} | {country} | {window} | last_updated {meta.last_updated}*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Channel breakdown:** Unicode horizontal bars over the 10-channel taxonomy (group cumulative <15% slices as `(N more)`). Replaces Mermaid pie. Pair with the table.
- **Period-over-period deltas (when `--vs-period`):** Unicode delta bars per channel with `▶`/`◀` direction caps + verdict label (MAJOR / MATERIAL / NOISE).
- **PPC monthly trend:** table only by default (Mermaid xychart-beta is renderer-aware appendix per § visualizations).

Sections in order (answer-first per sw-foundation-render):

- `## Executive read` (numbers-LIGHT, max 3 sentences. When `--vs-period`: FIRST WORD is the overall verdict label per sw-foundation-render § expert-heuristics (`WITHIN NOISE`, `MATERIAL CHANGE`, `MAJOR CHANGE`); name the biggest mover (channel + delta + %) in one sentence. When no `--vs-period`: lede on the dominant channel AND a § expert-heuristics red flag if applicable (e.g., "Paid Search 38% = margin-sensitive"; "Direct 67% = strong brand OR bot noise"; "Organic Search 11% on a content-heavy site = SEO underinvestment"). If engagement metrics are present, cite the matching § expert-heuristics engagement profile in the second sentence. When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## Rank + reach` (table: global rank, country rank, from Call 0). The Global rank column maps to the `country_rank` value from a `country="ww"` call (no `global_rank` field exists per `website-rank-no-global-field`). The Country rank column maps to the `country_rank` value from the `country="<user-country>"` call. When the user country IS `ww`, the Country rank column collapses to `n/a` and only one call is made.
- `## Channel breakdown`. 10-channel taxonomy table from Call 1, columns: `Channel`, `Visits (window)`. Values are ABSOLUTE visits aggregated across the window's months. Rows sorted descending by visits. The 10 channels (alphabetical for reference): Affiliates, Direct, Display Ads, Gen AI, Mail, Organic Search, Organic Social, Paid Search, Paid Social, Referrals. Apply sw-foundation-render § error-rendering pattern 4 (structural-zero) specifically when Paid Social returns exactly `0.0`: render `n/a [1]` and surface the classifier-rollup Caveat. Similarweb's classifier often rolls paid social into Display Ads, so a literal `0.0%` is structural-zero, not measured-zero.
- `## Period-over-period deltas` (only if `--vs-period`). Columns: `Channel`, `Current visits`, `Prior visits`, `Delta visits`, `% change`. Sorted by `abs(delta_visits)` descending.
- `## Channel share %`. Same 10-channel taxonomy, columns: `Channel`, `Share %`. By default, derived client-side from Call 1 visits per the Step 5 derivation (`share[ch] = visits[ch] / sum(visits)`) so no separate tool call is needed; saves ~200 data credits per run. If `--with-share-tool` was supplied AND Call 3 returned data, use Call 3 server-side values instead (only worth it for the long-tail-referrer rows the share tool surfaces). Apply sw-foundation-render § error-rendering pattern 4 (structural-zero) specifically when Paid Social returns exactly `0.0`: render `n/a [1]` and surface the classifier-rollup Caveat. Similarweb's classifier often rolls paid social into Display Ads, so a literal `0.0%` is structural-zero, not measured-zero.
- `## Top referral sources` (only if Call 4 accessible). Top 20 rows sorted client-side by `share` descending. Columns: `Referring domain`, `Share of referrals`, `Change vs prior period`. Context line: "Out of {{meta.total_count}} total referrers." `change` field rendered as % when present, `n/a` when null.
- `## PPC investment` (only if Call 5 accessible). Monthly time series table from Call 5. Columns: `Month`, `PPC spend`, `Currency`. Headline value above the table: "Total over window: {{sum(ppc_spend)}} {{currency}}." If `--vs-period`, render an adjacent "Prior window total: {{sum(prior)}} {{currency}}, delta = {{current - prior}}." (NO per-channel breakdown is rendered; the tool does not supply one.)
- `## Ad networks` (only if Call 6 accessible). Top 10 rows from Call 6, pre-sorted server-side. Columns: `Ad network`, `Share`, `Change`. Render `share` as % (0..1 -> %.1f). Render `change` as `n/a` when null.
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
- Sources line per sw-foundation-render § citation block (single line, NOT a table, NOT collapsible). Last element of the output unless `intent=handoff`.
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
- `channels_share_pct` is populated by default from the client-side derivation (`share[ch] = visits[ch] / sum(visits)` from Call 1). If `--with-share-tool` was supplied AND Call 3 returned data, it is populated from the server response instead. The values are mathematically identical for the 10-channel rollup; the server tool only adds value for the long-tail-referrer rows (which sw-channel-mix surfaces via Call 4 `get-traffic-referrals-incoming` anyway).
- `referrals_top` rows are sorted client-side by `share_of_referrals` descending. `share_of_referrals` is fraction-of-inbound-referrals (0..1), NOT fraction-of-all-visits.
- `ppc.monthly` rows are one per month; NO per-channel decomposition. If composing with traffic-channels for "estimated allocation by paid-channel visit share", emit a separate `ppc.estimated_by_channel` block and qualify it in the rendered output.
- `ad_networks` rows: `share` is fraction-of-incoming-ad-network-traffic (0..1). `change` may be null.

## Edge cases

- **Target has no Similarweb coverage** (Call 0 rank returns null): print "Similarweb has no coverage for {{target}}. Aborting." Exit.
- **No `--vs-period`**: skip Call 2; skip the `## Period-over-period deltas` section; `channels_prior` and `channel_deltas` are null in handoff.
- **`get-websites-ppc-spend` access-denied at runtime**: skip Call 5; skip the `## PPC investment` section; note in Caveats: "PPC investment not accessible on this plan." `ppc` key is null in handoff.
- **`get-website-analysis-ad-networks-agg` access-denied at runtime**: skip Call 6; skip the `## Ad networks` section; note in Caveats: "Ad networks not accessible on this plan." `ad_networks` key is null in handoff.
- **`get-traffic-referrals-incoming` access-denied at runtime**: skip Call 4; skip the `## Top referral sources` section; note in Caveats. `referrals_top` key is null in handoff.
- **`get-traffic-channels-share` access-denied at runtime AND `--with-share-tool` was supplied**: skip Call 3; the `## Channel share %` section still renders from the client-side derivation (Call 1 visits); note the opt-in tool skip in Caveats. `channels_share_pct` is populated from the derivation, not null.
- **User-supplied `end_date` is beyond `meta.last_updated`**: clamp per sw-foundation-data § window-resolution and note in Caveats with the canonical "end_date clamped from <requested> to <meta.last_updated>" wording.
- **Full country name passed**: normalize per sw-foundation-data § country-normalization before any call. If not resolvable, ask one disambiguation question.
- **A channel absent in prior window but present in current** (rare; only on taxonomy revisions): render `delta = current[ch]`, `pct_change = new` (NOT `+inf` or division-by-zero error).
- **`meta.last_updated` differs between Call 1 and Call 2 responses** (e.g. month-end roll happened mid-recipe): unlikely in a single invocation; recipe records `last_updated` once from Call 1 and asserts Call 2 matches, else flag with `[!gap]` in the rendered output.

## Cowork chat-side panel (when --vs-period set)

Per sw-foundation-render-cowork § Tier 2. SUPPLEMENTAL to the markdown answer; the markdown answer ALWAYS renders unchanged.

**Trigger.** `--vs-period` was supplied (single domain, two time periods). The 10-channel period-over-period table is the recipe's signature output; a Recharts grouped-bar chart carries the delta direction + magnitude per channel more cleanly than 10 rows of Unicode delta bars.

**How.** Use the `Write` tool to emit a SINGLE `.jsx` file at `~/sw-channel-mix-vs-panel.jsx`. Cowork renders it inline in the chat the moment the file is written. NO `create_artifact` call needed; chat-side panels are ephemeral per message.

**Constraints.** No `localStorage` (chat-side artifacts cannot use it). No external scripts. Recharts is auto-loaded by the chat-side runtime; do not import from a CDN.

**Page structure (one Recharts `BarChart`):**

- 10 channels on the X axis (one bar group per channel: Direct, Organic Search, Paid Search, Paid Social, Organic Social, Display Ads, Mail, Affiliates, Referrals, Gen AI).
- Two bars per channel: `current` (the Call 1 window) and `prior` (the Call 2 window). Y axis is share % (derived client-side from visits per the sw-channel-mix Step 5 derivation).
- Delta-direction color coding (applied to the `current` bar via the `fill` prop on each cell):
  - `delta_pct_points >= +1.0` (current up by at least one percentage point) -> green (`#10b981`).
  - `delta_pct_points <= -1.0` (down by at least one) -> red (`#ef4444`).
  - else -> gray (`#9ca3af`).
- Hover tooltip per channel: channel name, current %, prior %, `delta_pct_points` (the absolute percentage-point shift), `pct_change` (the relative % change), and the MAJOR / MATERIAL / WITHIN-NOISE classification per sw-foundation-render § expert-heuristics period-over-period verdict ladder (applied to `pct_change`, not `delta_pct_points`).

**Skeleton .jsx.** The panel skeleton lives at `references/cowork/vs-period-panel.jsx`; Read it and substitute the data slots (the per-channel current and prior share values from Call 1 and Call 2).

The runtime LLM replaces the `data` array values with the actual per-channel current + prior share % derived from the recipe's Call 1 and Call 2 responses. The skeleton fixes: Recharts component imports, color logic per § expert-heuristics, delta-direction `Cell` coloring on the current-period bar, and a custom tooltip body that names current / prior / delta-pp / pct-change / verdict.

**Failure handling.** Per sw-foundation-render-cowork § Failure handling. If the `Write` tool errors (no permission on the path, disk error), the recipe drops to Tier 1 silently; the markdown render is identical with or without the panel.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this channel-mix shift" -> `~~deck` (pptx by default). Layouts: title slide, Current channel share, Period-over-period deltas, Top referral sources, PPC investment, Ad networks, Strategic insights.
- "Export the channel-share table to a spreadsheet" -> `~~spreadsheet` (xlsx by default). Tabs: channel shares (current + prior), deltas, referrals, ppc, ad networks.
- "Send this channel-mix brief to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- traffic-channels-tool-shape
- channel-mix-period-comparison
- traffic-sources-shape
- ppc-spend-shape
- ad-networks-shape
- website-rank-no-global-field
- response-field-name-lookup
- partial-access-envelope-shape
