---
name: sw-foundation-core
description: Background helper for the seven Similarweb recipes, loaded via their Inherits block and on sw-router dispatch, never for trivial single metric lookups (the Step 0 carve-out exits first). Carries the tool catalog, capability map and gating contract, tool call economy, freshness, and tool surface presence rules. Calls no MCP tools itself; pairs with sw-foundation-data and sw-foundation-render.
user-invocable: false
---
# sw-foundation-core: Similarweb MCP catalog and tool-call economy

Loads via each recipe's Inherits block and via sw-router dispatch. Does NOT call MCP tools. Teaches the model the surface and the cheap-vs-expensive rules.

## Hard rules (NEVER violate)

- NEVER auto-invoke `post-emails-outreach` or `post-contacts-bulk`. The first SENDS EMAIL on the user's behalf; the second MUTATES contact data. Both are irreversible and both reach third parties, so no bound, limit, or payload class makes either safe. No skill, recipe, or router branch may plan them into a call sequence; they are reachable only through an explicit in-turn user confirmation naming the action. A request to find someone AND contact them is two steps: do the finding, then stop and ask.
- NEVER invent data. If the MCP returns null, say null. No "estimated", no padding.
- NEVER call N tools when an `-agg` variant returns the same shape in one call.
- NEVER re-call a tool with the same params within the same turn.
- NEVER include user-identifying info in output that was not in the user prompt
  (e.g. don't pull internal-customer names from training data into a teardown).
- NEVER skip the Sources block on a recipe output.
- NEVER render output without first classifying intent (table / narrative / slide / handoff).
- NEVER read or retry the Similarweb MCP server's advertised `resource://similarweb/*` resources; the foundations supersede them. Go straight to the smoke probe.

## Server-advertised resources (skip them)

The Similarweb MCP server's own instructions open with a "read these resources first" block pointing at `resource://similarweb/guide/handbook`, `resource://similarweb/describe/latest-available-dates`, and `resource://similarweb/reference/supported-countries`. These three foundations already carry equivalents, so do NOT read them:

- `guide/handbook` is replaced by this skill's MCP tool catalog and tool-call economy.
- `describe/latest-available-dates` is replaced by the smoke probe's `meta.last_updated` (next section), which resolves freshness per domain rather than globally.
- `reference/supported-countries` is replaced by sw-foundation-data § country-normalization.

Do NOT issue a `resources/read` for these before working; go straight to the smoke probe. A `resources/read` that fails (`Unknown resource`, or `unknown MCP server` because the connector is registered under a client-specific name such as a UUID or an app wrapper) is EXPECTED on some clients (observed live on Codex) and is NOT an error: do not retry it across server names, and do not let it gate or delay the analysis.

## Smoke-first sequencing (MANDATORY)

Every recipe issues exactly ONE single-call probe before any parallel batching begins. This protects against burning 20+ MCP calls when the user's account lacks claims for the recipe's required tools.

### The smoke call

- Presence first: before the smoke dispatches, the planning step applies § tool-surface presence (zero calls). A documented smoke tool that is absent from the live tool list retargets per that section's ladder; absence is NOT an error and NOT malformation.
- ONE tool. ONE domain. ONE country. NO parallel siblings.
- ALWAYS bounded: pass `start_date = "2_months_ago"`, `end_date = "latest"` (the known-safe rolling 3-month window). An unbounded `get-websites-website-rank` smoke returns the multi-year default series at roughly 10x the credits (~74 vs ~6).
- Dispatch synchronously. Wait for the response before issuing any other call.
- The recipe documents which tool is its smoke (see § Smoke tool catalog below; the per-recipe Step 2 parameter forms mirror it).
- The smoke result IS charged data. Recipes MUST reuse it for any later step that needs the same (tool, domain, country, window) instead of re-calling.

### Branch logic

After the smoke probe returns:

1. **200 OK**: proceed to the recipe's planned batching. Record the smoke result in conversation-context so the recipe does not re-fetch the same data later.
2. **403 with `error.code` FORBIDDEN_ERROR** (match on status and code, never on message text: the wording drifts between server releases): do NOT proceed with the planned batches yet. Issue ONE secondary probe on a DIFFERENT required tool (one tool, one domain, one country; pick it from the PRESENT subset per § tool-surface presence). If that secondary probe also returns a 403 FORBIDDEN_ERROR, treat as systemic auth failure: render sw-foundation-render § error-rendering Pattern 5 (INSUFFICIENT SIGNAL, capability-refresh as first NEXT MOVE) and STOP. If the secondary probe returns 200, proceed but mark the first tool as inaccessible_this_run (per § capability-gating).
3. **Client-level unknown-tool error** (message-gated per `unknown-tool-error-shape`: the harness says "No such tool available", or the server says "Unknown tool" for an advertised name): the tool is not callable on this connector. Do NOT retry and do NOT issue a denial-confirmation probe for it; mark `absent_this_run[tool]`, retarget the smoke per § tool-surface presence, and continue. Evaluated BEFORE the country-coverage check in the next branch; the envelopes are disjoint (a client-level error carries no server envelope). An "Input validation error" is NOT this branch: the tool exists and the arguments are wrong; fix the call.
4. **Other non-2xx**: FIRST check for a country-coverage gap, a 400 `client_error` or a 200-empty response carrying a country-coverage message (per § Country-coverage gap detection / § Precedence). If so, do NOT retry; apply the § Skip + pivot rule (pivot to `ww`, re-smoke once at `ww`, surface the worldwide caveat). Otherwise (a genuine 5xx, timeout, or validation error WITHOUT a country-coverage message): retry once with a 2-second pause. On second failure, render the recipe's standard error path for that tool (§ error-rendering Pattern 2). The other planned batches may still proceed in case the failure was transient.

### Anti-pattern (FORBIDDEN)

Do NOT batch N tools across M domains in parallel without an upfront smoke probe. The pattern "dispatch all 8 rank calls in parallel, then 4 traffic-and-engagement, then 4 channels" produces 24 wasted calls when the account lacks claims. Even if the recipe's planning section reads "parallelize within the comp set", that parallelism is GATED on a successful smoke probe.

### Cost

One synchronous round-trip (~1 second) on the success path. Negligible compared to the 20+ wasted calls saved on the failure path.

### Smoke tool catalog (per-recipe smoke, secondary probe, and pinned absence outcomes)

The single authoritative home for each recipe's smoke parameters, secondary probe, and pinned absence outcomes is the table in `references/smoke-catalog.md`; the recipes' Step 2 parameter forms mirror it, so Read the reference when authoring or reconciling a Step 2 form rather than on every run. An absence outcome inherits the same tool's denial outcome per § tool-surface presence (zero calls, zero retries, "not exposed on this connector" caveat wording).

If a recipe omits an explicit smoke tool, the planning step is malformed and the recipe should abort with a Caveats note pointing to this section. (A documented smoke tool that is ABSENT from the live tool list is not malformation; it retargets per § tool-surface presence.)

## Capability map schema

`$HOME/.similarweb-plugin/capabilities.json` is an OPTIONAL on-disk hint. Recipes proceed without it; the map is an APPEND-ONLY CACHE of observed access denials, built up lazily as recipes execute.

Lazy-mode minimal shape: `{schema_version: 2, last_updated, tools_inaccessible: [...]}`. After `/sw-config --refresh` invokes sw-setup, the same file additionally carries `mcp_server_version`, `last_full_probe`, `refresh_after`, `state` (one of `ready | auth_invalid | mcp_not_configured | probe_partial` per `auth-invalid-envelope-shape`), `tools_available` (per-tool true/false/pending; CALLED probes only), and `categories_available`. Tools NOT in `tools_inaccessible` are assumed accessible until observed otherwise.

**Presence fields, read-path precedence, fingerprint maintenance (in brief).** The map additionally carries `tools_absent` (planned-and-absent observations stamped with the surface hash; NEVER written to `tools_inaccessible`, which stays 403-claims only per the v0.1.13 rule, and a claims denial is never written to `tools_absent`) and `tool_surface` (sha256 fingerprint over the sorted unique unqualified names, plus count, observed_at, prefix). Precedence: an enumerable live list is the SOLE presence authority; otherwise stamp-matched `tools_absent` entries advisorily skip OPTIONAL tools only (never a REQUIRED tool); a call-time unknown-tool error overrides both for the run. Fingerprint maintenance is event-driven, never per-turn (compute only on count drift, an impending `tools_absent` write, or /sw-config --show or --refresh); the refresh suggestion renders ONCE per surface change, a first write is silent, and drift response stays user-consented (NEVER auto-probe). The full field definitions, the 4-step precedence contract with the legacy discriminator, and the maintenance rules live in `references/capability-map-schema.md`; Read it before any capability-map read or write decision.

**Canonical fingerprint step.** Run the bundled script, never improvised code (the bytes are pinned because the LLM re-writes code each run, the same reason the append-on-denial step below is scripted). Via Bash, pipe the JSON document `{"tools": [the unqualified names], "prefix": "the observed prefix"}` on stdin to the script at `scripts/capmap.py` (path relative to this skill's own directory), subcommand fingerprint. It computes sha256 over the sorted unique names, upserts `tool_surface` atomically (temp+rename, no BOM), and prints `changed`, `first`, or `same`. Render the refresh suggestion only when it prints `changed`. For `tools_absent` upserts, pipe `{"tools": [names], "observed_under": "the hash just computed"}` to the same script, subcommand absent (read, upsert by `name`, atomic temp+rename). If the script file is missing, skip the map update, add one Caveat line ("capability map not updated: bundled script missing"), and suggest running sw-setup via /sw-config --refresh; NEVER improvise replacement code.

## MCP tool catalog grouped by intent

Note: the catalog below reflects the Similarweb MCP server as of the last
grounded enumeration (2026-08-06, 113 tools) and drifts with server releases;
the live tool list exposed by the client is always the source of truth for
what exists. Presence is per-account and resolved at planning time per
§ tool-surface presence (live list, zero calls); access denials are handled
per § capability-gating. The catalog is a prior for intent mapping, quirks,
and economics only. Tools the user lacks
access to are filtered out at recipe execution time using
`$HOME/.similarweb-plugin/capabilities.json`.

### Websites domain-shaped queries

Rank, traffic-and-engagement, traffic channels (including the `Gen AI` channel), channel shares, incoming / outgoing / aggregated referrals, similar sites, audience overlap, demographics, geography, conversion rates, search (PPC) spend, display ad networks, social traffic sources, subdomains, SERP positions, landing pages, popular pages. The per-intent table with key params and the load-bearing quirks (rank has NO global_rank field, similar-sites' exact-3-month window and missing country param, agg-vs-looped rules, the ten-channel taxonomy, the two DIFFERENT source_type vocabularies between the channels and channels-share tools, and the `-agg` vs `-aggregated` suffix split between the older and newer families) lives in `references/websites-catalog.md`; Read it before planning any website call outside a recipe's documented call plan. It also carries § AI-referral intent, the ladder that replaced the retired `get-websites-referrals-agg` AI proxy: the claims-gated ai-traffic tools first, then ONE `get-website-analysis-traffic-channels` call read at its `Gen AI` row (10 credits per month, absolute visits).

### Keywords-shaped queries

| Intent | Tool | Key params |
|--------|------|------------|
| Overview of a keyword | `get-keywords-overview` | keyword, country |
| Top brands for a keyword | `get-keywords-top-brands-agg` | keyword, country |
| Top products for a keyword | `get-keywords-top-products-agg` | keyword, country |
| SEO landscape for a keyword | `get-keywords-seo-overview` | keyword, country |

### Apps-shaped queries

The apps surface is module-gated: plans without the Apps module do not expose these tools AT ALL (absent from the tool list rather than returning 403); resolve presence per § tool-surface presence before planning any apps call (absent means module_not_exposed, zero calls). `get-apps-details` is the ONLY apps tool on the live surface as of the 2026-08-07 enumeration, and its entitlement varies by account: the reference connector returned 403 through 2026-08-06 and 200 from 2026-08-07. Either outcome proves PRESENCE, so a denial renders as a denial, never as an absence. The other six apps names are documented-absent across two consecutive enumerations. The active guidance and that documented-absent list live in `references/apps-catalog.md`; Read it only when an apps-shaped query is actually in play.

### Brands and categories

| Intent | Tool | Key params |
|--------|------|------------|
| Brand sales performance | `get-brands-sales-performance-agg` | brand, window |
| Top competitors of a brand | `get-brands-top-competitors-agg` | brand, country |
| Top keywords for a brand | `get-brands-top-keywords-agg` | brand, country |
| Category performance | `get-categories-performance-agg` | domain (Amazon TLD), category (numeric ID) [^amazon-tld] |
| Top brands in category | `get-categories-top-brands-agg` | domain (Amazon TLD), category (numeric ID) [^amazon-tld] |
| Top keywords in category | `get-categories-top-keywords-agg` | domain (Amazon TLD), category (numeric ID) [^amazon-tld] |
| Resolve category ID | `get-categories-search` | domain (Amazon TLD), search_term [^amazon-tld] |

[^amazon-tld]: The `categories` surface is Amazon-shopper-only and takes an Amazon TLD via the `domain` param (NOT a country). Allowed enum: `amazon.com`, `amazon.co.uk`, `amazon.de`, `amazon.fr`, `amazon.it`, `amazon.ca`. Resolved `category` is the numeric ID returned by `get-categories-search`. To get country-specific Amazon demand, pass `domain: "amazon.de"` (NOT `country: "de"`).

### Lead enrichment

Two tools enrich a website (by domain) or a company (by name or domain); the parameter table lives in `references/lead-enrichment-catalog.md`.

### Commerce: the shopper and criq families

Amazon on-site search (32 tools, the `get-categories-`, `get-brands-`, `get-products-`, `get-clicks-` names plus the six shopper `get-keywords-` names) and cross-retailer performance (the 12 `get-retail-cross-` names). Membership is taken from the live name enumeration; the `[shopper]` and `[criq]` prefixes that open each tool description are the per-tool confirmation, verified on a sample rather than on all 44. Neither takes a Similarweb domain, and they do not share identifiers with each other or with the web family. The `domain` parameter on a shopper tool names the MARKETPLACE (`amazon.com` and its five siblings), never the analysed brand, which is a separate `brand` parameter; criq keys on an ACCOUNT-SCOPED custom-category UUID plus a market code. Both families require an uncharged discovery call first (`get-categories-search`, `get-brands-search`, `get-retail-cross-analysis-describe`) because their ids cannot be guessed or carried across marketplaces. NEVER sum shopper `clicks` with web `visits`: different quantities on different surfaces. Watch the prefix trap: `get-keywords-performance` and its siblings are `[shopper]`, while `get-keywords-seo-overview`, `get-keywords-overview`, and `get-keywords-latest-agg` are `[web]` SEO tools. The full intent tables, the two-axis criq cost shape (`rows x (metrics + 1)`, the same shape geography-agg follows), and the silent window-widening trap live in `references/commerce-catalog.md`; Read it before planning any commerce call.

### Buying signals

Six event-detection tools keyed on a COMPANY rather than a page or keyword: intent, technology, ecommerce, traffic, ad-network, news. Five charged a FLAT 10 credits per call, measured across row counts from 1 to 12 and windows from one day to two years, and none accepts a `limit`, so the lever is WHICH tools to call, not how much to ask for. Three traps: `get-sales-signals-intent` accepts exactly ONE valid window (its latest update day) and 400s on any other, so pass no dates at all; an empty result is a POPULATED message-only row rather than an empty array, so `len(data)` is not an emptiness test; and the technology tool's `Dates not in range` 400 shares its status and category with the country-coverage gap, which is why that detection is message-gated. Payloads name real third-party vendors, so examples are always synthetic and a signal renders as "topic interest detected", never as a claim about the company's plans. The intent table and cadences live in `references/signals-catalog.md`; Read it before planning any sales-signals call.

## Tool-call economy rules

1. **Prefer the aggregated variant for time aggregation** (spelled `-agg` in the older families and `-aggregated` in the newer `get-website-analysis-*` referral family; never guess which, resolve the name from the live tool list). When you need a single aggregated row (e.g. lifetime demographics, all-time conversion) rather than a time series, the `-agg` variant returns one row at substantially lower credit cost (about 37x cheaper for demographics, per `agg-variant-cost-savings`). For comparing N domains, loop the non-agg tool. The documented exception is `get-websites-audience-overlap-agg`, which accepts a comma-joined `domains` parameter (2-5 domains) and returns 2^N-1 subset rows in a single call.
2. **Smoke test first.** Use `get-websites-website-rank` as a one-call check that the domain has Similarweb coverage before running a full recipe.
3. **Default windows.** Defer to sw-foundation-data § window-resolution: rolling 3 months (`start_date = "2_months_ago"`, `end_date = "latest"`) for traffic and SERP surfaces; the Amazon shopper surface defaults server-side to a multi-year aggregate. Override only when the user specifies.
4. **Skip tools the user lacks.** Read `$HOME/.similarweb-plugin/capabilities.json` first; filter call plan against it.
5. **Never re-call within a turn.** If you already have the data from a previous call this turn, use it. Don't re-call.

## Freshness rules

Each MCP response carries `meta.last_updated` in `YYYY-MM-DD` form. Use it as the source of truth for that tool's freshness rather than assuming a cadence. The observed production cadence table (near-real-time vs monthly buckets, plus the categories-performance 3-year default-window footnote) lives in `references/freshness-cadences.md`. If the user asks for "today" data and `meta.last_updated` is older than 3 days, surface this in the Caveats block.

## Helper sections (recipes reference these by name)

### § tool-surface presence

Presence ("does this tool exist on this connector?") is a gating axis SEPARATE from access (403 claims) and country coverage, and the only free one: detect it from the AI client's live tool list at planning time, zero calls, never by probing. Grounded in `mcp-tool-catalog-v1`, `plan-gating-vs-server-drift`, and `unknown-tool-error-shape`. Tri-state evidence rule in brief: PRESENT only on positive evidence (a qualifying closed-list enumeration with sentinel quorum, or a successfully loaded tool schema); ABSENT only when a qualifying enumeration positively omits the name; otherwise UNKNOWN, which proceeds optimistically (cached `tools_absent` entries may advisorily skip OPTIONAL tools, NEVER abort or skip a REQUIRED tool). Prior-session memory, `capabilities.json`, and this skill's catalog are never presence evidence. **Predecessor fallback (check BEFORE declaring absence).** A rename breaks in both directions, and connectors do not all update together (the OpenAI-curated Similarweb connector is packaged separately from the direct MCP server, and clients cache tool surfaces). So when a documented name is ABSENT, consult the name-history map in `mcp-tool-catalog-v1` Appendix C: if this tool's retired predecessor IS present in the live list, call the predecessor, treat the capability as PRESENT, and add one Caveat ("this connector still exposes `<old-name>`; using it. Your Similarweb connector may be a release behind."). Only entries with a REAL successor qualify; an Appendix C entry mapped to `none` (currently `get-websites-referrals-agg`) was retired outright and is never a substitute. Only when neither name is present is the tool truly absent. Pinned outcomes: an absent tool inherits the recipe's documented DENIAL outcome with zero calls, zero retries, Pattern 7 wording ("not exposed on this connector"), persisted to `tools_absent`, never `tools_inaccessible`; an absent smoke tool retargets per the documented ladder rather than skipping the smoke. Call-time detection is message-gated ("No such tool available" / "Unknown tool"; an "Input validation error" is NOT absence). The full rules (qualifying-evidence definition with the 4 sentinel names, canonical-name matching, ordering, the retarget ladder, call-time consolidation bullets, aggregate insufficiency, per-platform evidence classes) live in `references/tool-surface-presence.md`; Read it BEFORE applying the pre-filter (which runs at planning time, before the capability-map read and before the smoke probe, consuming zero MCP calls).

### § capability-gating

The capability map at `~/.similarweb-plugin/capabilities.json` is an OPTIONAL hint, not a hard prerequisite; recipes proceed without it and NEVER block on its state. Step 2 pattern in brief: read the map if present and pre-filter the call plan (skip OPTIONAL tools listed in `tools_inaccessible`; abort when a REQUIRED tool is listed); execute the plan with § error-rendering Pattern 3 handling; record a tool as access-denied ONLY on an actual HTTP 403 with `error.code` FORBIDDEN_ERROR (match status and code, never message text: the wording drifts between server releases). NEVER record a validation 400 ("Dates not in range", a bad metric or param), a country-coverage gap, or an ABSENT tool as a denial: each would poison the map and wrongly skip a tool the plan actually grants (absence persists to `tools_absent`, never here). The full doctrine (legacy schema-v1 reads, expiry, the in-run `inaccessible_this_run` tracking, the skip rule, tool-level vs domain-level 403 distinction with the PPC-spend canonical example, render wording, the required-tool-no-fallback abort) lives in `references/capability-gating.md`; Read it when the first 403 of the run arrives, or before pre-filtering against a populated map.

**Append-on-denial step** (at run end, or as the 403 is observed; only tool-level denials persist, domain-level 403s stay in-run). Via Bash, pipe `{"tool": "the denied tool name"}` on stdin to the bundled script at `scripts/capmap.py` (path relative to this skill's own directory), subcommand deny: idempotent sorted append to `tools_inaccessible`, atomic temp+rename write, no BOM, never improvised inline code. If the script file is missing, skip the map update, add one Caveat line ("capability map not updated: bundled script missing"), and suggest running sw-setup via /sw-config --refresh; NEVER improvise replacement code.

### Country-coverage gap detection (in-run)

A second failure envelope, distinct from 403: the tool itself is accessible but the user's plan does not cover the requested ISO-2 country, so only worldwide (`ww`) is on this plan for that tool. Detection is MESSAGE-GATED (per `country-coverage-gap-shape`) in either of two HTTP shapes: a 400 `client_error` (live-observed) OR a 200 with empty data (retained defensively), whose message carries one of "no data for requested country", "country not available", "country not covered", "no coverage for country" (case-insensitive substring match). A 400 WITHOUT this message (e.g. "Dates not in range") is NOT a country gap; it stays on the validation and retry path per the distinction table below. **Precedence (global):** check this BEFORE the generic error paths; a response carrying the message never routes to retry-once, never renders "unavailable this run", and is NEVER recorded as an access denial, for the smoke probe and every batched call, in every recipe. Track `country_unavailable_this_run[(tool, country)]` from the start of every recipe turn. The full shape definitions live in `references/country-gap.md`; Read it on the FIRST non-2xx or empty-data response of any run, before routing the error.

### Skip + pivot rule on country-coverage gap

On the first (tool, country) gap: record it, skip ALL remaining not-yet-dispatched domains for that pair, and pivot to `country=ww` for that tool this turn (when the smoke itself gapped, re-smoke once at ww); when 2 or more distinct tools gap on the same country, skip subsequent (tool, country) batches entirely and fall back to ww immediately; render ONE consolidated Caveats line ("Country X not on this plan; rendered worldwide. Affected tools: ...") and let the header line show the pivoted country per sw-foundation-render § error-rendering Pattern 6 main text. The full 5-step rule with the parallel-batch and smoke-pairing notes lives in `references/country-gap.md`.

### § payload-budget

Response SIZE is a planning axis independent of credits, resolved before the call like presence and gating, not handled after it like a 403. Three invariants. **(1) Credits and bytes are independent.** The most dangerous call on this surface charges zero, and a context overflow is unrecoverable in a way every other failure is not: no envelope, no retry, no turn left in which to apply a skip rule. **(2) A tool with no `limit` parameter is not therefore small.** Find its growth term (row count, date window, an explicit flag) and bound that. **(3) The budget binds a TURN, not a call.** A recipe that fans out (per-keyword loops, comp sets, per-country batches) divides the budget by its fan-out factor when choosing a bound, and sequences rather than parallelizes when the product still exceeds it; ten individually compliant calls still overflow together.

These classes are about response BYTES and say nothing about whether a call should be made at all; the never-auto-invoke rule for the two side-effectful tools is a Hard rule above, and it is not overridden by anything here.

Three call classes, for read-only tools. **Never inline**: `get-user-segments-describe` and `get-gen-ai-campaigns`. No parameter brings them under budget (the first accepts `length` and `chars` and ignores both; the second is bounded only by an id obtainable from its own unbounded listing), so they are not called, and there is no buffered-read escape because an MCP result reaches the model before any script can touch it. **Safe unbounded**: `get-ai-traffic-overview`, `get-ai-traffic-overview-aggregated`, `get-industry-demographics-describe`, `get-industry-unique-users-describe`. These accept no bound parameter and are measured small. **Bound required**: every other READ-ONLY live tool, measured or not. Pass an explicit `limit`, `metrics` list, date window, or id filter, and never rely on server defaults. This class is not a licence to call: it answers "how do I shape a call I have already decided to make", never "may I make it".

The default for an unmeasured tool is bound-required, never silence. Requiring a bound asserts nothing about safety and costs nothing; staying silent is a safety assertion by omission, and that is precisely the inference that shipped an unconditional 23.9 MB call. Two tools are safe at their DEFAULT and dangerous only under an explicit parameter: NEVER pass `include_shared: true` to `get-custom-industries-describe` (60 B to 5.0 MB), and pin `get-sales-signals-news` to a window of at most 7 days (8 KB to 1.7 MB).

The inline budget is about 50 KB per response and is a conservative proxy, not a measured threshold; the exact number is not load-bearing because every bound-accepting tool is bounded regardless. Some clients replace an oversized result with a size notice and a preview instead of the payload, so a 200 does not guarantee the data is in front of you (see sw-foundation-render § error-rendering Pattern 8). The full lists, the reference measurements for choosing a bound, and the rule for adding a tool to either list live in `references/payload-budget.md`; Read it before bounding a tool for the first time.

### Distinction summary

| Envelope | What it means | In-run map | Skip rule |
|----------|---------------|------------|-----------|
| Tool name absent from a qualifying live tool list, OR call-time "No such tool available" / server "Unknown tool" (message-gated per `unknown-tool-error-shape`) | Not exposed on this connector (module gating or surface drift) | `absent_this_run[tool]` | Zero calls, no retry, no denial-confirmation probe; outcome inherits the tool's documented denial outcome; smoke retargets per § tool-surface presence; one consolidated caveat; NEVER recorded in `tools_inaccessible` |
| HTTP 403 + `error.code` FORBIDDEN_ERROR (status and code only; NEVER the message text, which drifts between releases) | Account/tool gated | `inaccessible_this_run[tool]` | Skip ALL domains for that tool; fall back to optional probes; if 2+ required tools 403 trigger Pattern 5 |
| HTTP 400 client_error OR HTTP 200 empty data, WITH a "no data for requested country" message | Country not on plan for that tool | `country_unavailable_this_run[(tool, country)]` | Skip remaining domains for that (tool, country); pivot to ww; if 2+ tools country-gap for same country, propagate to subsequent tools |
| HTTP 200 + empty data for one specific domain (no country-coverage message) | That domain has no traffic for the window | NO tracking; just render n/a for that cell | None; per-domain absence is a real result |
| HTTP 5xx / timeout / validation error WITHOUT a country-coverage message | Transient or schema problem | NO tracking | Retry once per § error-rendering Pattern 2 |
| HTTP 2xx whose content is a size statement plus a file path instead of the payload (shape-matched, never on wording) | Response exceeded the AI client's inline budget; the client buffered it and the model never saw the data | `oversized_this_run[tool]` | Never retry (a 2xx reproduces exactly) and never parse the preview; render the cell, caveat the bound used, and OFFER one tighter re-call as a NEXT MOVE per sw-foundation-render § error-rendering Pattern 8. The re-call is the user's choice, not an automatic extra paid call. Prevention is the real control: bound every call per § payload-budget |

### § bulk-input-from-context

When a recipe accepts a LIST of inputs (multiple domains, brands, or keywords), use whatever the user already shared in the current conversation (a pasted list, an @-mentioned file already read into context, args in the prompt); DO NOT scan the working directory or do filesystem globbing (context-derived only; identical across Claude Code, Codex, Cursor, Claude.ai). The 4-step detection rules (including the over-25 confirmation question and the one crisp disambiguation question) live in `references/bulk-input.md`; Read it when a list-shaped artifact is in context.

## What this skill does NOT do

It does not call MCP tools, produce visible output, or override sw-config / any recipe's hard rules. Country / window normalization lives in sw-foundation-data. Rendering, citation block, error rendering, expert heuristics, visualizations, and handoff JSON live in sw-foundation-render. Recipe and router skills load all three sub-foundations and act on them.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- mcp-tool-catalog-v1
- agg-variant-cost-savings
- freshness-per-tool
- cheap-probe-tool-per-category
- website-rank-no-global-field
- resource-reads-unavailable
- country-coverage-gap-shape
- similar-sites-window-constraint
- unknown-tool-error-shape
- unknown-tool-error-shape-other-platforms
- plan-gating-vs-server-drift
- describe-envelope-and-coverage-probe
- audience-geography-shape
- keywords-latest-agg-shape
- referral-pipelines-divergence
- technologies-agg-shape
- traffic-by-demographics-semantics
- payload-measurements
- harness-oversized-output-buffering
- geography-agg-cost-shape
- ai-traffic-vs-channel-proxy-completeness
- commerce-surface-entity-models
- sales-signals-family-shape
- demand-trends-aggregation-semantics
- criq-performance-cost-shape
- web-family-cost-shapes-2026-08
