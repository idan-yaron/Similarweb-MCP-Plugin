---
name: sw-aeo-audit
description: AEO and AI search visibility audit for one brand domain. Use for Answer Engine Optimization, an AEO audit or score, an SEO audit of a domain, AI visibility posture, whether LLMs or AI assistants such as ChatGPT cite or recommend a brand, answer box presence, and SERP share of voice for AI engines. Runs a grounded proxy from SEO posture, per keyword SERP share, and answer box adjacent pages; an AI Tracker campaign UUID promotes it to direct measurement. Do not use for keyword gap mining versus a rival (use sw-keyword-opportunity) or for page level content mix (use sw-page-mix). Never fabricates AEO data.
---
# sw-aeo-audit

**Inherits:**
- sw-foundation-core: § capability-gating, § bulk-input-from-context
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering, § expert-heuristics, § visualizations, § handoff-json-schema (when intent=handoff)

Load sw-foundation-core, sw-foundation-data, and sw-foundation-render now via your platform's skill mechanism (the Skill tool where available, plugin-qualified names accepted); where no skill mechanism exists, Read the bundled SKILL.md files of those three skills and apply them inline. Never resolve them via cwd-relative paths.

## Hard rules (NEVER violate)

- NEVER promise direct AI-engine measurement without data in hand. The audit is a proxy WHENEVER the direct path does not return data, which is an account property and not a server fact; entitlement state is stated once in sw-foundation-core references/websites-catalog.md under the AI-referral intent, and this recipe does not restate it. Per `aeo-tool-availability`, `get-gen-ai-campaign-analysis-prompts` returns HTTP 400 `VALIDATION_ERROR: Requested campaign is unknown for your account` for any ad-hoc campaign_id, because an account admin must pre-configure an AI Tracker campaign in the Similarweb product UI. Campaign enumeration DOES exist on the 2026-08 surface (`get-gen-ai-campaigns`), and it is NEVER CALLED regardless of entitlement: its bare listing is 1.9 MB and its only bound is a campaign id obtainable solely from that same listing, so it is never-inline per sw-foundation-core § payload-budget. The `--discover-campaigns` flag that once attempted it has been withdrawn; the recipe asks for a UUID instead. Whether the `get-ai-traffic-*` family returns data varies by account; attempt it and branch on the response. Recipe substitutes SEO + SERP + landing-pages + the `Gen AI` traffic channel as the proxy. The proxy framing ships in the Executive read AND in an always-on Caveat.
- NEVER sum the `Gen AI` channel and the `AI Search` row into one AI number. Report them separately, each with its own gloss. `Gen AI` is a first-class traffic channel; `AI Search` is an AI-answer surface counted INSIDE organic search (source_type `Search - Organic` in the channels-share tool). They are two separate measurement surfaces, so adding them double-counts nothing but implies a single metric that does not exist.
- NEVER use `get-keywords-top-brands-agg` for AEO. That tool is Amazon-shopper-only (returns Amazon brand rankings inside the Amazon shopper graph, NOT general-web SERP brand presence). The general-web equivalent does not exist; recipe uses `get-websites-serp-players-agg` for share-of-voice via SERP-ranked-domains-by-keyword.
- NEVER pass a date range wider than the rolling 3 months to `get-keywords-seo-overview` or `get-websites-serp-players-agg`. Server returns HTTP 400 `VALIDATION_ERROR` per `aeo-seo-overview-shape`, `aeo-serp-players-shape`. Recipe derives effective `end_date` per sw-foundation-data § window-resolution (the Call 1 rank call's `meta.last_updated`; this recipe's Step 2 smoke is `get-keywords-seo-overview`, not rank) and uses the relative-keyword window `start_date = "2_months_ago"`, `end_date = "latest"` (a 3-month INCLUSIVE span; computing end_date minus a literal 3 months yields a 4-month span the server rejects, per § window-resolution rule 3). Wider windows are rejected server-side.
- NEVER pass a 3-month window to `get-websites-landing-pages-agg` with `granularity: "monthly"`. Per `landing-pages-window-constraint`, monthly granularity returns LAST MONTH ONLY (not 3 months); the server either truncates silently or returns `VALIDATION_ERROR`. Call 4 MUST special-case this window: `start_date = first day of effective_end_date's month`, `end_date = effective_end_date`. This is one calendar month, the most recent one.
- NEVER widen the AEO-worthiness scoring set beyond `{related_questions, featured_snippet, featured_answer, organic_sitelinks, organic_expanded_sitelinks}` without updating the rendered footnote AND `tests/grounded/serp-features-enum.md`. The 5-feature set is the answer-box-adjacent enum; `featured_answer` was added in the 2026-05-17 grounding pass after the live MCP returned it on lululemon.com (gift card, returns and refunds) and a broader cross-domain probe (apple.com, webmd.com, clevelandclinic.org). `featured_snippet` is kept for forward-compat; the live server currently labels the answer-box as `featured_answer`.
- NEVER skip the proxy-vs-direct caveat. It ships in EVERY run, even when `--campaign-id` succeeded with 200. The user must always understand the proxy-vs-direct distinction.
- NEVER pass `traffic_source: "all"` to `get-websites-landing-pages-agg`. The parameter is constrained to `paid` or `organic` per `aeo-landing-pages-shape`; AEO recipe always uses `organic`.
- NEVER auto-pick a keyword inference set without offering it as a single confirmation. If `--keywords` is absent AND no keyword list is in conversation context, ask once with explicit options.
- NEVER pass a full country name (`"United States"`) to any tool. All tools want ISO-3166-1 alpha-2 (`"us"`). Normalize before any call.
- NEVER conflate the brand's `serp_features` from `get-websites-serp-players-agg` (per-domain-per-keyword) with the per-URL `serp_features` from `get-websites-landing-pages-agg`. Different aggregations; render in separate tables.
- NEVER abort the audit if Call 5 (`--campaign-id` direct signal) returns 4xx. Surface inline, OMIT the Direct AI-engine signal section, add a Caveat, ship the proxy audit.
- NEVER report `brand_traffic_share > 0` when the brand is absent from a keyword's top-10 SERP players. Render `0.00%` and surface in Caveats (brand absence is a finding, not an error).

## Step 0 (silent): conversation-context scan

Apply sw-foundation-data § conversation-context to scan for prior recipe outputs. If found, prepare to reuse rank smoke or window per the helper rules. If no prior recipe found, skip silently and proceed.

## Step 1: Parse and validate input

```bash
DOMAIN="<first positional arg>"
COUNTRY="${COUNTRY:-us}"
COUNTRY="${COUNTRY,,}"  # then apply sw-foundation-data § country-normalization map
KEYWORDS="${KEYWORDS:-}"               # comma-separated csv; 5-10 brand-relevant terms; cap 10
CAMPAIGN_ID="${CAMPAIGN_ID:-}"         # optional UUID; promotes audit from proxy to direct signal
echo "$DOMAIN" | grep -qE "^[a-z0-9.-]+\.[a-z]{2,}$" || { echo "Usage: /sw-aeo-audit <domain> [--country <iso-2>] [--keywords <k1,k2,...>] [--campaign-id <uuid>]"; exit 1; }
if [ -n "$CAMPAIGN_ID" ] && ! echo "$CAMPAIGN_ID" | grep -qiE "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"; then
  echo "Invalid --campaign-id; expected UUID format (8-4-4-4-12 hex)"; exit 1
fi
```

## Step 2: apply lazy capability gating + smoke-first probe (MANDATORY)

- **Smoke**: `get-keywords-seo-overview` for the FIRST keyword from `--keywords` if supplied, else a clear prompt-derived seed term; country=`$COUNTRY` (resolved per sw-foundation-core § default-country resolution; documented default `us`). The live schema has no keyword positional: realize the smoke as `domain = <target>` plus a `keywords_filter_rules` phrase-include on that keyword (consistent with `aeo-seo-overview-shape`). A 200 IS Call 2 (the SEO overview for the first keyword); reuse it, never re-call.
- If NO keywords were supplied AND the prompt carries no clear seed term, run Step 3 (keyword acquisition) BEFORE this smoke so the smoke spends on a keyword the audit will actually use; fall back to the target's brand term only when the prompt implies a brand-level audit.
- **Secondary probe**: `get-websites-website-rank`, target domain, country=`$COUNTRY`. If the smoke is denied but the secondary probe returns 200, ABORT (the recipe cannot ship an AEO audit without SEO-overview signal); render Caveat "AEO audit requires `get-keywords-seo-overview`; tool not accessible on this plan."
- **Pinned absence outcomes**: `get-keywords-seo-overview`: ABORT outright (no smoke retarget exists here; absence supersedes retargeting); `get-websites-serp-players-agg` or `get-websites-landing-pages-agg`: drop their sections and continue; `get-websites-website-rank`: degrade the rank context and derive end_date from the smoke's `meta.last_updated` (the seo-overview response carries it).
- Emit the First read per this recipe's row in sw-foundation-render § insight-first delivery as soon as the first data-bearing call succeeds, before the remaining calls.
- Procedure per sw-foundation-core § smoke-first sequencing, § tool-surface presence, and § capability-gating; parameters per the smoke catalog table there.

REQUIRED (proxy audit):
- `get-websites-website-rank`
- `get-keywords-seo-overview`
- `get-websites-serp-players-agg`
- `get-websites-landing-pages-agg`

OPTIONAL (direct-signal upgrade, ONLY when `--campaign-id` supplied):
- `get-gen-ai-campaign-analysis-prompts`


OPTIONAL (AI-referral ladder, Call 6; full rung definitions in Step 4):
- `get-ai-traffic-landing-pages-agg` then `get-ai-traffic-overview` (rung 1, direct; returns data or 403 depending on the account)
- `get-website-analysis-traffic-channels` (rung 2, the DEFAULT proxy)
- `get-website-analysis-traffic-channels-share` (rung 3, opt-in drill-down, never auto-fires)

None of the OPTIONAL tools can abort the audit. If `--campaign-id` was supplied but `get-gen-ai-campaign-analysis-prompts` is not accessible, skip Call 5 and note in Caveats: "AEO direct-signal tool not accessible on this plan; continuing with proxy audit."

## Step 3: Pick up bulk inputs from context

Per sw-foundation-core § bulk-input-from-context. If `--keywords` was not supplied:
1. Inspect the conversation context for a keyword-list-shaped artifact relevant to the brand (5-10 keywords).
2. If found and count > 10: ask one confirmation question with default "top 10 by relevance".
3. If found and shape is ambiguous (could be products, categories, or generic terms): ask ONE crisp disambiguation question with explicit options.
4. If not found, ask the user once: "I need 5-10 brand-relevant keywords to audit AEO posture. Share them with me, or suggest a category and I'll propose 5."

## Step 4: Plan the call sequence

| Call | Tool | Purpose |
|------|------|---------|
| 1 | `get-websites-website-rank` | Headline rank + derive effective `end_date` from `meta.last_updated` (NOT this recipe's smoke; the Step 2 smoke is `get-keywords-seo-overview`). Bound to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~6 data credits vs ~74 for the default 36-month series |
| 2 | `get-keywords-seo-overview` | Branded vs unbranded clicks split + intent mix; addressable AEO market context. Bounded by the rolling 3-month `start_date`/`end_date` window pinned in the hard rules above; the server rejects anything wider |
| 3 | `get-websites-serp-players-agg` | LOOPED per keyword, capped at 10 calls; brand's `traffic_share` + `serp_features` per keyword; competitive set. Bounded by the same rolling 3-month `start_date`/`end_date` window and by the keyword cap, which is the fan-out lever for the turn budget |
| 4 | `get-websites-landing-pages-agg` | Brand's organic landing pages; AEO-worthiness score per URL from answer-box-adjacent `serp_features`. Bounded by the single-calendar-month `start_date`/`end_date` special case in the hard rules above plus `traffic_source: organic` |
| 5 | `get-gen-ai-campaign-analysis-prompts` | ONLY if `--campaign-id` supplied. Direct AI-engine signal; renders AFTER the proxy sections. ALWAYS bound it: pass a small `limit` AND a `metrics` list that OMITS `response`. The `response` field carries the full model answer per row and dominates the payload (about 453 KB at server defaults versus 1.2 KB at limit 1 without it, per `payload-measurements`). Bound at the request, never by capping rows at render time after paying for them |
| 5b | WITHDRAWN | `get-gen-ai-campaigns` is never-inline per sw-foundation-core § payload-budget: 1.9 MB bare, and its only bound is an id obtainable solely from that same listing. There is no bounded call to make, so campaign discovery is not attempted and the recipe keeps the blind UUID ask |
| 6 | AI-referral ladder (3 rungs, defined below) | AI-referral signal: is AI actually sending traffic to the target |

### Call 6: the AI-referral ladder

Three rungs, direct-measurement-first. Rung 1 is the primary path whenever the account has it: it names AI sources from the AI-traffic module itself. Rungs 2 and 3 are what a gated account can see, and neither recovers what rung 1 reports. Per `traffic-channels-tool-shape`, `referral-pipelines-divergence`, and `partial-access-envelope-shape`; the rung-1 attempt is the probe, per sw-foundation-core § capability-gating Fallback-on-denial (try-primary-catch-403). The referral-pipeline AI proxy this ladder replaces is gone: `get-websites-referrals-agg` was RETIRED in the 2026-08 surface change (never call it), and its AI rows did not move into the surviving referral tools, so never look for AI-assistant referrers in `get-website-analysis-traffic-referrals-incoming` or `get-website-analysis-traffic-referrals-aggregated` (a limit-100 scan of the aggregated tool surfaced no AI-assistant domain at all; AI referrers are served by the traffic-channels family now).

**Rung 1: direct measurement, account-dependent.** Attempt `get-ai-traffic-landing-pages-agg` (target, country, latest, `limit: 10`: it is 1 credit per row, so the bound is the cost lever as well as the payload lever, and 10 rows is what the landing-pages section renders; the server default of 100 would cost about 100 credits for rows the render discards), then `get-ai-traffic-overview` (which accepts no bound parameter, is about 1 KB, and charged 0 on every observation, so it is called as-is). On the reference connector both returned HTTP 403 `FORBIDDEN_ERROR` (uncharged) through 2026-08-06 and 200 from 2026-08-07; that is one account moving, not a rule about accounts. A 403 here means the tool is PRESENT on the server and the AI-research claim is not enabled for this account: render it with exactly that framing per sw-foundation-render § error-rendering Pattern 3, never as "no AI data exists". On a 200, this rung IS the answer: label the section DIRECT measurement and skip rungs 2 and 3 unless the user also asked for channel context. NEVER describe any part of the audit as direct AI measurement unless one of these two tools returned data.

**Rung 2: the DEFAULT proxy.** Runs whenever rung 1 is denied, absent, or fails for any other reason (a 5xx or timeout degrades here too; rung 2 is the floor, not a 403-only branch). ONE `get-website-analysis-traffic-channels` call (target, `country`, `granularity: "monthly"`, `web_source: "total"`). Pass the window EXPLICITLY as `start_date` = first day of the effective month from Call 1 and `end_date` = that same effective month end: one calendar month, 10 credits. NEVER omit both dates: the server default resolves to a multi-year span and charges ~370 credits (`traffic-channels-tool-shape`), and NEVER inherit Step 5's general 3-month window here, which would charge 30. 10 credits per requested month, window-priced, no `limit` parameter. The response carries `Gen AI` as a first-class channel with ABSOLUTE VISITS alongside the other nine (Affiliates, Direct, Display Ads, Mail, Organic Search, Organic Social, Paid Search, Paid Social, Referrals). Derive:

```
ai_visits    = visits of the row where source_type == "Gen AI"   (0.0 when the row is absent)
total_visits = sum(visits) over ALL rows returned for that date
ai_share     = ai_visits / total_visits    (guard: see the zero rule below)
```

Guard the denominator. When the response returns ZERO rows for the effective month, or `total_visits` is zero or null, the recipe measured NOTHING: render a data-unavailable Caveat per sw-foundation-render § error-rendering Pattern 1 and omit the AI-referral section. Do NOT compute `0 / 0` and do NOT render the no-measurable-traffic line, which is a claim about the world. Only an ABSENT `Gen AI` row inside a POPULATED response (`total_visits` greater than zero) sets `ai_visits = 0.0` and licenses the no-measurable-traffic finding.

Iterate the returned rows; NEVER index a fixed month-by-channel grid, because the server may omit a sub-meaningful row (`traffic-channels-tool-shape`). Request the 3-month window (`start_date = "2_months_ago"`, `end_date = "latest"`, 30 credits) ONLY when the user asked for an AI trend; one month is the default.

**Rung 3: opt-in drill-down that names SOME AI sources.** Never auto-fires. ONE `get-website-analysis-traffic-channels-share` call at `limit: 50` (100 credits; this tool prices at exactly 2 credits per requested row). It returns the AI sources that reach the top 50 referrers at that limit, which is a partial view and not an enumeration: across two domains and two consecutive months one Gen AI source crossed the rank-50 boundary between months and another sat past rank 90, so no fixed limit is sufficient and raising it costs linearly without closing the gap. Render it as "AI sources within the first 50 referrers", state that a source absent from the list is unknown rather than zero, and make the NEXT MOVE name the direct AI-traffic module as the path to a complete list. NEVER present this as the set of AI sources sending traffic. Rows are `{domain, source_type, share}`; `meta.visits` carries the period total. There is NO server-side `source_type` filter, so filter client-side: rows with `source_type == "Gen AI"` are the named AI-assistant referrers, and the `AI Search` row (source_type `Search - Organic`) is reported separately. Offer this rung in NEXT MOVES when rung 2 shows a non-trivial `Gen AI` share; run it only after the user says yes.

Two-vocabulary discipline: the channels tool and the channels-share tool spell their `source_type` values differently (Mail vs Email, Organic Search vs Search - Organic). Never equate them, and never sum `Gen AI` with `AI Search` into one AI number without the gloss (hard rule above).

Per-keyword fanout: Call 3 fans out to N keywords (default 5-10, capped at 10). Calls are independent; parallelize. Default audit total cost = ~12-13 data credits for the shared SEO and SERP calls, plus the AI rung. On an ENTITLED account rung 1 costs about 10 credits (landing-pages at `limit: 10`, 1 per row; the overview is uncharged), so the entitled default is about 22-23 credits and it is the complete path. On a GATED account rung 2 costs 10 credits for one month, so the gated default is about 22-23 credits as well, but buys a share figure rather than named sources. Rung 2's 10-credits-per-month price is measured directly; rung 1's figure is *derived* from its measured 1-credit-per-row price at the shipped `limit: 10`, not read off a live 10-row run. Opt-in rungs are excluded from that default: rung 3 adds 100 credits at `limit: 50`. The retired referral-based proxy cost ~30-40 credits, so the default ladder is CHEAPER than what it replaced, and the expensive rung is now opt-in.

## Step 5: Execute

Call 1 runs first. Derive the effective window per sw-foundation-data § window-resolution: pass `start_date = "2_months_ago"`, `end_date = "latest"`; the server clamps to its latest published month and echoes the effective dates (a 3-month inclusive span, e.g. effective `end_date = 2026-04` gives `start_date = 2026-02`). NEVER compute `end_date - 3 months` client-side; per § window-resolution rule 3 that yields a 4-month span the capped tools reject.

**Window special-case for Call 4 (per `landing-pages-window-constraint`):** Calls 2 and 3 use the rolling 3-month window. Call 4 (`get-websites-landing-pages-agg`) is monthly-only-last-month: pass `start_date = first day of effective_end_date's month`, `end_date = effective_end_date`. Concretely if `end_date = 2026-04-30`, Call 4 uses `start_date = 2026-04-01, end_date = 2026-04-30` (the single most recent month) while Calls 2 and 3 use `start_date = 2026-02-01, end_date = 2026-04-30` (the rolling 3-month window). Passing a 3-month window to landing-pages-agg with monthly granularity returns last-month-only data anyway (silent truncation) or a VALIDATION_ERROR; this special-case avoids both failure modes.

Calls 2 and 4 are independent given the resolved windows; parallelize with Call 3. Call 3 fans out per keyword and is itself independent across keywords; parallelize within the loop. Call 5 (if `--campaign-id`) runs in parallel with all proxy calls; Call 6 rung 1 also runs in parallel with the proxy calls; rung 2 fires only after rung 1's outcome is known (it is the fallback), and rung 3 never fires inside the same turn as the initial render.

Client-side derivations after responses arrive:

1. **From Call 2 (SEO context):** aggregate per-month rows. Compute:
   - `branded_clicks_share = sum(branded_clicks) / sum(clicks)`
   - `unbranded_clicks_share = sum(unbranded_clicks) / sum(clicks)`
   - Per-intent share: `<intent>_clicks_share = sum(<intent>_intent_clicks) / sum(clicks)` for each of {informational, navigational, transactional, local, job_search}.

2. **From Call 3 (per keyword):** for each keyword response, locate the row where `domain` matches `$DOMAIN` (root-domain match, ignoring subdomain). Record:
   - `brand_traffic_share` (default `0.0` if brand absent from top-10)
   - `brand_serp_features` (default `[]` if absent)
   - `brand_top_url` (default `null` if absent)
   - `brand_top_position` (default `null` if absent)
   - Extract competitive set from the other 9 rows; identify the top non-brand competitor by `traffic_share` and record their `domain` + `traffic_share`.
   - If brand is absent: add Caveat entry "brand absent from top-10 SERP players for `<keyword>`".

3. **From Call 4 (AEO-worthy pages):** for each URL row, compute:
   ```
   ANSWER_BOX_FEATURES = {"related_questions", "featured_snippet", "featured_answer", "organic_sitelinks", "organic_expanded_sitelinks"}
   url.aeo_score = sum(1 for f in url.serp_features if f in ANSWER_BOX_FEATURES)
   url.answer_box_features = [f for f in url.serp_features if f in ANSWER_BOX_FEATURES]
   ```
   Sort URLs by `aeo_score` desc, tie-break by `traffic_share` desc. The 5-feature set is grounded in `tests/grounded/serp-features-enum.md`; `featured_answer` was added in the 2026-05-17 grounding pass after the live MCP returned it on informational pages (lululemon gift card / returns and refunds, webmd explainers, apple support pages). `featured_snippet` is kept for forward-compat with future server-side label changes; the live server currently uses `featured_answer` for the answer-box surface.

4. **Recommendations:**
   - `defend_keywords = top 5 by brand_traffic_share from Call 3` (descending; exclude brand-absent rows).
   - `optimize_pages = top 5 by aeo_score from Call 4` (descending; tie-break by traffic_share).

5. **From Call 5 (if supplied):** if HTTP 200, parse the prompts payload (prompt text, LLM response, brands mentioned, citations, sentiment, source LLM); cap at 20 prompts for rendering. If HTTP 4xx, OMIT the `## Direct AI-engine signal` section and add Caveat: "Direct AI-engine signal call returned `<status_code>` `<error_message>`; proxy audit completed."


6. **From Call 6 (AI-referral ladder):** record which rung produced the section. Rung 1 200 gives direct rows as returned. Rung 2 gives `ai_visits`, `total_visits`, `ai_share` per the ladder formula; when the `Gen AI` row is absent from the returned rows, `ai_visits = 0.0` and the section renders the no-measurable-traffic line rather than a fabricated zero-share table. Rung 3 (only if the user opted in) gives the named `Gen AI` source rows and the separate `AI Search` row; keep the two lists apart.

Execute via the AI client's MCP surface. Accumulate source records `{tool, params, status, data_credits, last_updated}` (data_credits per sw-foundation-render § citation block: meta.data_credits_charged, fallback meta.sw_coins, null if both absent). Per sw-foundation-render § error-rendering for null / non-2xx / capability-skipped.

## Step 6: Classify output intent

Per sw-foundation-render intent-aware output rendering rules. Default: narrative. Narrow questions render the short form per sw-foundation-render's short-form rule.

## Step 7: Render

Apply token compression per sw-foundation-render § citation block. Output length per sw-foundation-render's output-render targets.

**Header (FIRST line of output, ONE italic line):** `*{target} | {country} | rolling 3-month | last_updated {meta.last_updated} | proxy audit*`. Drop duplicate parentheticals from every subsequent section header.

Visualizations per sw-foundation-render § visualizations (Unicode-first):
- **Per-keyword brand traffic_share:** Unicode horizontal bars, one per keyword, sorted descending by `brand_traffic_share`. Pair with the table.
- **SEO context intent_mix:** Unicode horizontal bars over the 5 intent categories (`informational / navigational / transactional / local / job_search` per Step 5 derivation 1). Replaces Mermaid pie. Pair with the SEO context table.

Sections in order (answer-first per sw-foundation-render):

- `## Executive read` (numbers-LIGHT, max 3 sentences; always frames the audit as PROXY. Name the STRONGEST AEO surface (top brand-traffic-share keyword) AND the WEAKEST (lowest brand-traffic-share OR brand absent) in the same paragraph. If `--campaign-id` AND Call 5 returned 200, name ONE direct-signal headline finding separated from proxy framing. When the current recipe builds materially on a prior recipe in this conversation, prepend the Executive read with the "Connecting back" line per sw-foundation-data § conversation-context.).
- `## SEO context` (table from Call 2 aggregates. Rows: `Branded clicks share`, `Unbranded clicks share`, `Informational intent share`, `Navigational intent share`, `Transactional intent share`, `Local intent share`, `Job-search intent share`. Values rendered as percent to 2 decimal places. Subtitle: "Addressable AEO market = unbranded clicks; AI engines disproportionately answer informational queries." Window cited above the table.).
- `## Per-keyword SERP landscape` (one row per keyword from Call 3. Columns: `Keyword`, `Brand traffic share`, `Brand SERP features`, `Top non-brand competitor`, `Competitor share`, `Brand top URL`, `Brand top position`. `Brand SERP features` rendered as comma-separated list. Brand-absent rows render `0.00%` for traffic share, `n/a` for features and URL.).
- `## AI-citation-worthy pages` (one row per URL from Call 4, sorted by `aeo_score` desc. Columns: `URL`, `AEO score`, `Answer-box features`, `Traffic share`, `Top keyword`. Answer-box features rendered from the 5-feature set only (NOT the full `serp_features` list). Footnote: "AEO score = count of answer-box-adjacent serp_features per URL (related_questions, featured_snippet, featured_answer, organic_sitelinks, organic_expanded_sitelinks). Pages with higher AEO scores are more likely to be cited by AI engines synthesizing answers. `featured_answer` is the live answer-box surface returned by the Similarweb MCP; `featured_snippet` is kept for forward-compat.").
- `## Direct AI-engine signal` (ONLY if `--campaign-id` supplied AND Call 5 returned 200. Renders the prompts payload as a list capped at 20 entries with prompt text, source LLM, response, brands mentioned, citations, sentiment. Subtitle: "Direct AI Tracker measurement for campaign_id `<uuid>`.").
- `## AI-referral signal` (from Call 6, rendered from whichever rung produced data).
  - **Rung 1 (200):** render the direct AI-traffic rows as returned (landing page or AI source, estimated visits) under the subtitle "DIRECT AI-traffic measurement." This is the only wording in the whole recipe allowed to call anything direct.
  - **Rung 2 (the default):** render one line plus a Unicode bar per sw-foundation-render § visualizations comparing `Gen AI` against the largest channel: `Gen AI` absolute visits, `ai_share` as a percent to 2 decimal places, and the same-window all-channel total. Subtitle: "AI-referral PROXY (the direct AI-traffic tools are present on the server but not enabled for this account; this is the `Gen AI` channel from the traffic-channels breakdown, `<month>`, `<country>`)." When a 3-month window was requested, add the month-over-month direction in one clause.
  - **Rung 3 (only when the user opted in):** add a named-source table (`Source domain`, `Share`) from the `source_type == "Gen AI"` rows, then render the `AI Search` row on its own line glossed as "an AI-answer surface counted inside organic search, not inside the Gen AI channel". NEVER add the two figures together.
  - **No signal:** if the `Gen AI` row is absent or its visits are 0, render one line: "No measurable Gen AI channel traffic detected this period."
  - NEVER compare a traffic-channels or channels-share figure against a referral-pipeline share (`get-website-analysis-traffic-referrals-incoming` or `-aggregated`) without the pipeline gloss, per `referral-pipelines-divergence`; the referral tools carry no AI-assistant rows at all.
- `## Recommendations` (two subsections: `### Top 5 keywords to defend` (ranked by current `brand_traffic_share` from Call 3, descending) and `### Top 5 pages to optimize` (ranked by `aeo_score` from Call 4, descending). Each item carries a one-line rationale (e.g., "currently winning featured_snippet + organic_sitelinks; defend by keeping content authoritative" or "currently absent from related_questions; add FAQ schema to capture that surface"). EVERY recommendation ends with a confidence label `(confidence: HIGH | MEDIUM | LOW)` per sw-foundation-render § expert-heuristics hypothesis calibration. HIGH for keywords with brand_traffic_share > 30% AND at least one answer-box-adjacent serp_feature; MEDIUM for keywords with brand_traffic_share 10-30% OR aeo_score >= 2; LOW for keywords with brand_traffic_share < 10% OR aeo_score == 0. NEVER ship without confidence labels. **Refusal-as-feature per sw-foundation-render § expert-heuristics**: if NO audited keyword shows brand_traffic_share > 5% AND NO landing-page URL has any answer-box-adjacent serp_feature (aeo_score = 0 across the board), REPLACE this section with a clear `## INSUFFICIENT AEO SIGNAL` block. Body: "No defensible AEO hook detected across the audited keyword set: brand absent or sub-5% on every keyword's top-10 SERP players; zero landing-page URLs carry answer-box-adjacent serp_features (related_questions, featured_snippet, featured_answer, organic_sitelinks, organic_expanded_sitelinks). Specific recommendations would be generic and unactionable. Re-run after the domain accumulates SERP presence, or share a broader keyword set if you want me to test a different keyword pool. Provide the actual data above as the diagnostic." NEVER ship a generic recommendation when this refusal condition fires.).
- `## NEXT MOVES` (EXACTLY 2 backtick-quoted natural-language questions, each
  with a one-sentence rationale max. Per sw-foundation-render § citation block
  conversational-tone rule, NEVER emit `/sw-X` slash-commands or `--flag` syntax
  here. The router auto-dispatches free-form questions.

  Question types to suggest, picked by the strongest signal in the render:
  - **Competitive teardown vs the dominant SERP players**:
    `"How does <target> stack up against <top-3-non-brand-domains-from-serp-players>?"`
    followed by one sentence on going head-to-head against the actual SERP players the audit surfaced.
  - **Channel-mix to see if AEO trend matches traffic shift**:
    `"How did <target>'s channel mix shift over the last quarter?"`
    followed by one sentence on checking whether the AEO / SEO posture matches an underlying traffic shift.
  - **Name the AI sources** (only when Call 6 rung 2 ran and the `Gen AI` share is
    non-trivial; this is the opt-in rung-3 offer):
    `"Which AI assistants are actually sending traffic to <target>?"`
    followed by one sentence saying the follow-up names the individual Gen AI
    source domains and costs 100 credits.
  - **Audience overlap with top AI-cited domains** (only when `--campaign-id` AND Call 5 returned a direct signal):
    `"What's <target>'s audience overlap with <top-cited-domain>?"`
    followed by one sentence on whether the AI-citation neighbor overlaps with the brand's existing audience.

  Reference specific keywords, competitor domains, or AI-cited domains surfaced in THIS run.)
- `## Caveats` (ALWAYS includes the proxy-vs-direct caveat; additional entries per sw-foundation-render § error-rendering for null / unavailable / capability-skipped / inferred keywords / brand absent from any keyword's top-10 / `end_date` clamped / window narrower than 3 months for new domains).
- Sources line per sw-foundation-render § citation block (single line, NOT a table, NOT collapsible). Last element of the output unless `intent=handoff`.
- `[optional] ## Handoff` (JSON, only when intent=handoff).

Proxy-vs-direct caveat exact text class (this is the only variant; campaign discovery is withdrawn, so the recipe always asks blind for a UUID): "This audit approximates AEO from traditional SEO + SERP + landing-pages signals plus the `Gen AI` traffic channel (the proxy). Direct AI-engine measurement requires a pre-configured AI Tracker campaign in the Similarweb product UI. If you have a campaign UUID, share it with me and I'll lift this from proxy to direct measurement."


## Step 8: Citation + caveats + optional handoff

Per sw-foundation-render § citation block (pass the source records from Step 5). Per sw-foundation-render § handoff-json-schema, emit the `data` payload below when intent classifies as `handoff`.

### data schema for sw-aeo-audit handoff

```json
{
  "rank": {"global": 0, "country": 0, "country_param_global": "ww", "country_param_country": "us"},
  "seo_context": {
    "branded_clicks_share": 0.0,
    "unbranded_clicks_share": 0.0,
    "intent_mix": {
      "informational": 0.0,
      "navigational": 0.0,
      "transactional": 0.0,
      "local": 0.0,
      "job_search": 0.0
    }
  },
  "per_keyword_serp": [
    {
      "keyword": "<text>",
      "brand_traffic_share": 0.0,
      "brand_serp_features": ["<feature>"],
      "competitive_set": [{"domain": "<domain>", "share": 0.0}],
      "brand_top_url": "<url-or-null>",
      "brand_top_position": 0
    }
  ],
  "aeo_worthy_pages": [
    {
      "url": "<url>",
      "aeo_score": 0,
      "answer_box_features": ["<feature>"],
      "traffic_share": 0.0,
      "top_keyword": "<text>"
    }
  ],
  "direct_ai_signal": null,
  "recommendations": {
    "defend_keywords": ["<keyword>"],
    "optimize_pages": ["<url>"]
  },
  "_meta": {
    "audit_type": "proxy",
    "window": "3-month rolling",
    "end_date": "YYYY-MM-DD"
  }
}
```

Field semantics:
- `seo_context.intent_mix` carries the five intent shares from `get-keywords-seo-overview`. If the server adds a new intent class (per the re-validation notes in `aeo-seo-overview-shape`), add the key and re-balance the denominator.
- `per_keyword_serp` rows: one per keyword in the requested set (5-10 rows). `brand_traffic_share = 0.0`, `brand_serp_features = []`, `brand_top_url = null`, `brand_top_position = null` when the brand is absent from the keyword's top-10; absence is also surfaced in Caveats.
- `per_keyword_serp[].competitive_set` lists the top non-brand competitor only (one row); a future extension can carry the full top-9-non-brand list if a competitive-set deliverable is asked for. Current shape ships one entry per keyword.
- `aeo_worthy_pages` rows sorted by `aeo_score` desc, tie-break by `traffic_share` desc. `aeo_score` is an integer in [0, 5]. `answer_box_features` is the intersection of the URL's `serp_features` with the 5-feature answer-box-adjacent enum (`{related_questions, featured_snippet, featured_answer, organic_sitelinks, organic_expanded_sitelinks}`).
- `direct_ai_signal` is `null` unless `--campaign-id` was supplied AND Call 5 returned 200. Shape when populated:

```json
{
  "campaign_id": "<uuid>",
  "prompts": [
    {
      "prompt_text": "<text>",
      "source_llm": "chatgpt | google_ai_mode | perplexity | gemini",
      "response": "<text>",
      "brands_mentioned": ["<brand>"],
      "citations": ["<url>"],
      "sentiment": "positive | neutral | negative"
    }
  ]
}
```

- `recommendations.defend_keywords` is the top-5 keywords by `brand_traffic_share` descending, excluding brand-absent keywords. If fewer than 5 keywords have any brand presence, ship fewer rows + note in Caveats.
- `recommendations.optimize_pages` is the top-5 URLs by `aeo_score` descending; tie-break by `traffic_share`. Always ships up to 5 rows from the landing-pages response.
- `_meta.audit_type` is `"proxy"` by default; `"proxy+direct"` when `--campaign-id` was supplied AND Call 5 returned 200. NEVER `"direct"` alone (the proxy IS the audit).
- `_meta.window` is `"3-month rolling"` by default; `"narrower-than-3-months"` for new domains with insufficient history (+ Caveat).
- `_meta.end_date` is the clamped `end_date` from Call 1's `meta.last_updated`.

## Edge cases

- **`--campaign-id` supplied but tool returns 4xx**: surface inline ("Direct AI-engine signal call returned `<status_code>` `<error_message>`"); continue with proxy audit; add Caveat; OMIT the `## Direct AI-engine signal` section; `direct_ai_signal` is `null` in handoff.
- **`--keywords` not supplied AND no keyword inference possible from context**: ask once with explicit options: "I need 5-10 brand-relevant keywords to audit AEO posture. Share them with me, or suggest a category and I'll propose 5." Do NOT silently invent.
- **User supplies more than 10 keywords**: ask one disambiguation question with default "top 10 by relevance" (recipe convention; matches `aeo-serp-players-shape` cost budget of one call per keyword).
- **Server returns < 3 months of data (new domain)**: adjust window to whatever the server returned; record actual span in `_meta.window` and add Caveat: "Domain has less than 3 months of Similarweb coverage; AEO audit ran on a narrower window of `<start>` to `<end>`. Re-run after coverage matures."
- **Domain has 0 organic landing pages** (Call 4 returns empty `data`): AEO recipe is moot for this domain. Print: "Similarweb has no organic landing-pages data for `<domain>`; the AEO recipe needs at least one organic page to compute AI-citation-worthy candidates. Verify the domain has organic search traffic, or re-run after coverage matures." Skip the `## AI-citation-worthy pages` and `### Top 5 pages to optimize` sections. SEO context + per-keyword SERP landscape still ship.
- **Brand absent from a keyword's top-10 SERP players**: render the keyword row with `brand_traffic_share = 0.00%`, `brand_serp_features = n/a`, `brand_top_url = n/a`, `brand_top_position = n/a`. Add Caveat per missing keyword. NOT an abort condition.
- **Target has no Similarweb coverage** (Call 1 rank returns null): print "Similarweb has no coverage for `<domain>`. Aborting AEO audit." Exit.
- **User-supplied `end_date` is beyond `meta.last_updated`**: clamp per sw-foundation-data § window-resolution and note in Caveats with the canonical "end_date clamped from <requested> to <meta.last_updated>" wording.
- **`get-gen-ai-campaign-analysis-prompts` access-denied at runtime AND `--campaign-id` was supplied**: skip Call 5; OMIT the `## Direct AI-engine signal` section; add Caveat: "AEO direct-signal tool not accessible on this plan; continuing with proxy audit." `direct_ai_signal` is `null` in handoff.
- **A user asks which AI Tracker campaigns their account has**: the recipe cannot enumerate them. `get-gen-ai-campaigns` is never-inline (1.9 MB bare, no working bound), so answer that campaign discovery is not available from here and ask for the UUID from the Similarweb product UI.
- **Both rung-1 AI-traffic tools 403 AND the rung-2 traffic-channels call also fails or is absent**: OMIT the `## AI-referral signal` section entirely and add ONE consolidated Caveat naming both causes per sw-foundation-render § error-rendering Pattern 3 and Pattern 7. Never substitute a referral tool; the referral pipelines carry no AI-assistant rows.
- **Rung 2 returns 200 but no `Gen AI` row**: render the no-measurable-traffic line. This is a real finding (below the reporting floor), not a failure, so it never becomes a Caveat about tool access.
- **User asks to name the AI sources**: run rung 3 at `limit: 50` and say the cost before calling. Never downgrade the limit to save credits; below 50 the `AI Search` row and below 25 the `chatgpt.com` row fall off the response and read as a false zero.
- **All keyword SERP calls fail with 5xx** (Call 3 entirely down): skip the `## Per-keyword SERP landscape` and `### Top 5 keywords to defend` sections; add Caveat. SEO context + AI-citation-worthy pages still ship.

## Export options (Cowork-only)

When the runtime is Cowork, the recipe output can be exported via connectors declared in `CONNECTORS.md`. The recipe does NOT bundle these targets; it calls them via the `Skill` tool at runtime. Each export is opt-in: the user must ask for it in natural language. The recipe never auto-exports.

- "Build me a deck of this AEO audit" -> `~~deck` (pptx by default). Layouts: title slide, AEO-score breakdown, Per-keyword SERP landscape, AI-citation-worthy pages, Top 5 pages to optimize, Strategic insights.
- "Export the AEO-score breakdown to a spreadsheet" -> `~~spreadsheet` (xlsx by default). Tabs: per-keyword SERP, landing-page candidates, brand SERP features.
- "Send this AEO audit to my team in chat" -> `~~chat` (slack-by-salesforce by default).
- "Save as PDF" -> `~~doc` (pdf by default).

If a connector is not configured, the recipe surfaces a one-line fallback: "To export this to <category>, install a <category> plugin via Cowork Customize > Plugins."

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- unknown-tool-error-shape
- aeo-tool-availability
- aeo-seo-overview-shape
- aeo-serp-players-shape
- aeo-landing-pages-shape
- serp-features-enum
- landing-pages-window-constraint
- response-field-name-lookup
- partial-access-envelope-shape
- referral-pipelines-divergence
- traffic-channels-tool-shape
- payload-measurements
- ai-traffic-vs-channel-proxy-completeness
