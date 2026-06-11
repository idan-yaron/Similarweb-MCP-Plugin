---
name: sw-foundation-core
description: Helper utility loaded by the seven user-invocable Similarweb recipes (sw-competitive-teardown, sw-audience-overlap, sw-channel-mix, sw-market-size, sw-aeo-audit, sw-page-mix, sw-keyword-opportunity) and by sw-router when it dispatches to a recipe or plans a direct-MCP fallback. Carries the Similarweb MCP server core priors such as the tool catalog, capability map, tool-call economy, and freshness rules. Helper sections cited by recipes are section capability-gating and section bulk-input-from-context. NOT loaded for trivial single-domain single-metric lookups; the sw-router Step 0 carve-out exits before reaching the foundations. Does not call MCP tools itself; pairs with sw-foundation-data and sw-foundation-render.
user-invocable: false
---
# sw-foundation-core: Similarweb MCP catalog and tool-call economy

Loads via each recipe's Inherits block and via sw-router dispatch. Does NOT call MCP tools. Teaches the model the surface and the cheap-vs-expensive rules.

## Hard rules (NEVER violate)

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

- ONE tool. ONE domain. ONE country. NO parallel siblings.
- ALWAYS bounded: pass `start_date = "2_months_ago"`, `end_date = "latest"` (the known-safe rolling 3-month window). An unbounded `get-websites-website-rank` smoke returns the multi-year default series at roughly 10x the credits (~74 vs ~6).
- Dispatch synchronously. Wait for the response before issuing any other call.
- The recipe documents which tool is its smoke (see the per-recipe Step 2 sections).
- The smoke result IS charged data. Recipes MUST reuse it for any later step that needs the same (tool, domain, country, window) instead of re-calling.

### Branch logic

After the smoke probe returns:

1. **200 OK**: proceed to the recipe's planned batching. Record the smoke result in conversation-context so the recipe does not re-fetch the same data later.
2. **403 with "missing the required claims" wording**: do NOT proceed with the planned batches yet. Issue ONE secondary probe on a DIFFERENT required tool (one tool, one domain, one country). If that secondary probe also 403s with the same wording, treat as systemic auth failure: render sw-foundation-render § error-rendering Pattern 5 (INSUFFICIENT SIGNAL, capability-refresh as first NEXT MOVE) and STOP. If the secondary probe returns 200, proceed but mark the first tool as inaccessible_this_run (per § capability-gating).
3. **Other non-2xx**: FIRST check for a country-coverage gap, a 400 `client_error` or a 200-empty response carrying a country-coverage message (per § Country-coverage gap detection / § Precedence). If so, do NOT retry; apply the § Skip + pivot rule (pivot to `ww`, re-smoke once at `ww`, surface the worldwide caveat). Otherwise (a genuine 5xx, timeout, or validation error WITHOUT a country-coverage message): retry once with a 2-second pause. On second failure, render the recipe's standard error path for that tool (§ error-rendering Pattern 2). The other planned batches may still proceed in case the failure was transient.

### Anti-pattern (FORBIDDEN)

Do NOT batch N tools across M domains in parallel without an upfront smoke probe. The pattern "dispatch all 8 rank calls in parallel, then 4 traffic-and-engagement, then 4 channels" produces 24 wasted calls when the account lacks claims. Even if the recipe's planning section reads "parallelize within the comp set", that parallelism is GATED on a successful smoke probe.

### Cost

One synchronous round-trip (~1 second) on the success path. Negligible compared to the 20+ wasted calls saved on the failure path.

### Smoke tool catalog (which tool each recipe uses as its smoke)

| Recipe | Smoke tool | First-domain default |
|--------|------------|---------------------|
| sw-competitive-teardown | get-websites-website-rank | target, country=ww |
| sw-audience-overlap | get-websites-website-rank | target, country=ww |
| sw-channel-mix | get-websites-website-rank | target, country=us (or user-supplied) |
| sw-page-mix | get-websites-website-rank | target, country=us (or user-supplied) |
| sw-aeo-audit | get-keywords-seo-overview | the first keyword from the recipe args if supplied, else the user's prompt-derived seed term; country=us |
| sw-keyword-opportunity | get-keywords-overview | the first keyword from the recipe args if supplied, else target's brand term; country=us |
| sw-market-size | get-categories-search | the category-or-keyword-cluster argument; no country needed |

If a recipe omits an explicit smoke tool, the planning step is malformed and the recipe should abort with a Caveats note pointing to this section.

## Capability map schema

`$HOME/.similarweb-plugin/capabilities.json` is an OPTIONAL on-disk hint. Recipes proceed without it; the map is an APPEND-ONLY CACHE of observed access denials, built up lazily as recipes execute.

Lazy-mode minimal shape: `{schema_version: 2, last_updated, tools_inaccessible: [...]}`. After `/sw-config --refresh` invokes sw-setup, the same file additionally carries `mcp_server_version`, `last_full_probe`, `refresh_after`, `state` (one of `ready | auth_invalid | mcp_not_configured | probe_partial` per `auth-invalid-envelope-shape`), `tools_available` (per-tool true/false/pending), and `categories_available`. Tools NOT in `tools_inaccessible` are assumed accessible until observed otherwise.

## MCP tool catalog grouped by intent

Note: the catalog below reflects the Similarweb MCP server as of the last
grounded probe and drifts with server releases; the live tool list exposed by
the client is always the source of truth for what exists. Tools the user lacks
access to are filtered out at recipe execution time using
`$HOME/.similarweb-plugin/capabilities.json`.

### Websites domain-shaped queries

| Intent | Tool | Key params | Notes |
|--------|------|------------|-------|
| Rank a domain | `get-websites-website-rank` | domain, country | Cheap. Use as a smoke test. Response has `country_rank` + `category_rank` only; NO `global_rank` field. For global rank, pass `country: "ww"` and use the returned `country_rank` (see `website-rank-no-global-field`). `web_source` constraint: `total` only. |
| Traffic + engagement of one domain | `get-websites-traffic-and-engagement` | domain, country, start_date, end_date | Default window: last 90 days. |
| Compare N domains' traffic | `get-websites-traffic-and-engagement` (same tool, looped over each domain) | as above; one call per domain | No batched-over-entities variant exists for this tool. Loop the non-agg tool. |
| Traffic channels (absolute visits) | `get-websites-traffic-channels` | domain, country, window | Returns absolute visits by channel across the live 10-channel taxonomy: Affiliates, Direct, Display Ads, Gen AI, Mail, Organic Search, Organic Social, Paid Search, Paid Social, Referrals. Use `get-traffic-channels-share` for share-percentage view. |
| Marketing channels by source | `get-traffic-referrals-incoming` | domain | Per-domain inbound referrers (`get-segments-traffic-sources` takes a Segment ID, not a domain). |
| Similar sites | `get-websites-similar-sites-agg` | domain, country, limit | Default limit 10. WINDOW CONSTRAINT: explicit start_date/end_date must span EXACTLY 3 months (use start_date 2_months_ago, end_date latest) or the call 400s with "must span exactly 3 month(s)"; omitting both dates is also safe. Response rows carry `affinity` (0..1 similarity); there is NO `similarity_score` field. Per `similar-sites-window-constraint`. |
| Audience overlap | `get-websites-audience-overlap-agg` | domain, domains (comma-joined string, 2-5 domains) | Returns 2^N-1 subset rows in a single batched call. |
| Demographics | `get-websites-demographics-agg` | domain, country | Age + gender breakdown. |
| Geography | `get-websites-geography-agg` | domain | Country share. |
| Conversion rates | `get-websites-conversion-rates-agg` | domain, vertical | Vertical-specific. Module-gated: absent from many plans' tool lists entirely; verify the tool is present in the live tool list before planning it. |
| PPC spend | `get-websites-ppc-spend` | domain, country, window, currency | Returns estimated monthly PPC spend as a single scalar per month (no by-channel breakdown). |
| SERP positions | `get-websites-serp-players-agg` | keyword, country | Domain rankings for a keyword. |
| Landing pages | `get-websites-landing-pages-agg` | domain, source_channel | Top entry points by channel. |
| Popular pages on a domain | `get-pages-popular-pages-agg` | domain | URL-level traffic. |

### Keywords-shaped queries

| Intent | Tool | Key params |
|--------|------|------------|
| Overview of a keyword | `get-keywords-overview` | keyword, country |
| Top brands for a keyword | `get-keywords-top-brands-agg` | keyword, country |
| Top products for a keyword | `get-keywords-top-products-agg` | keyword, country |
| SEO landscape for a keyword | `get-keywords-seo-overview` | keyword, country |

### Apps-shaped queries

The apps surface is module-gated: plans without the Apps module do not expose these tools AT ALL (they are absent from the client's tool list rather than returning 403). Before planning any apps call, verify the tool name appears in the live tool list; if absent, treat the category as module_not_exposed and say so, do not attempt the call.

| Intent | Tool | Key params |
|--------|------|------------|
| Find an app | `get-apps-search` | term |
| App downloads | `get-apps-downloads` | app_id, country, window |
| App active users | `get-apps-active-users` | app_id, country, window |
| App rankings | `get-apps-ranks` | app_id, country, category |
| App retention | `get-apps-retention` | app_id, country |
| App audience | `get-apps-audience-demographics` | app_id, country |

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

| Intent | Tool | Key params |
|--------|------|------------|
| Enrich a website | `get-lead-enrichment-website` | domain |
| Enrich a company | `get-lead-enrichment-company` | name OR domain |

## Tool-call economy rules

1. **Prefer `-agg` for time aggregation.** When you need a single aggregated row (e.g. lifetime demographics, all-time conversion) rather than a time series, the `-agg` variant returns one row at substantially lower credit cost (about 37x cheaper for demographics, per `agg-variant-cost-savings`). For comparing N domains, loop the non-agg tool. The documented exception is `get-websites-audience-overlap-agg`, which accepts a comma-joined `domains` parameter (2-5 domains) and returns 2^N-1 subset rows in a single call.
2. **Smoke test first.** Use `get-websites-website-rank` as a one-call check that the domain has Similarweb coverage before running a full recipe.
3. **Default windows.** Defer to sw-foundation-data § window-resolution: rolling 3 months (`start_date = "2_months_ago"`, `end_date = "latest"`) for traffic and SERP surfaces; the Amazon shopper surface defaults server-side to a multi-year aggregate. Override only when the user specifies.
4. **Skip tools the user lacks.** Read `$HOME/.similarweb-plugin/capabilities.json` first; filter call plan against it.
5. **Never re-call within a turn.** If you already have the data from a previous call this turn, use it. Don't re-call.

## Freshness rules

Each MCP response carries `meta.last_updated` in `YYYY-MM-DD` form. Use it as
the source of truth for that tool's freshness rather than assuming a cadence.
Cadences observed in production (subject to drift; re-grounded each release):

| Bucket | Approximate cadence | Example tools |
|--------|---------------------|---------------|
| Near-real-time | Updated within the last 24 hours | `get-apps-*` (active users, downloads) |
| Monthly | Updated at month boundary | `get-websites-traffic-and-engagement`, `get-brands-sales-performance-agg`, `get-categories-performance-agg` [^cat-perf-window] |

[^cat-perf-window]: `get-categories-performance-agg` rolls its `meta.last_updated` monthly but its data window defaults to a 3-year aggregate (`2023-04-01` through last-completed-month), NOT a rolling 30-day window. Pass explicit `start_date` / `end_date` to override.

If the user asks for "today" data and `meta.last_updated` is older than
3 days, surface this in the Caveats block.

## Helper sections (recipes reference these by name)

### § capability-gating

The capability map at `~/.similarweb-plugin/capabilities.json` is an OPTIONAL hint, not a hard prerequisite. Recipes proceed without it.

**Pattern (each recipe Step 2):**

1. Try to read `~/.similarweb-plugin/capabilities.json`. If present and not expired, use its `tools_inaccessible` list (and `tools_available` map if also present) to pre-filter the call plan (skip OPTIONAL tools known to be inaccessible; abort if REQUIRED tools are flagged inaccessible). Expiry applies only to full-probe maps via their `refresh_after` field; a lazy append-only map (no `refresh_after`) never expires, it is an advisory set of observed denials.
2. If missing or expired, proceed with no prior knowledge. Execute the recipe's planned tool calls.
3. Wrap each tool call in § error-rendering pattern 3 handling. Record a tool as access-denied ONLY on an actual access error: HTTP 403 carrying "missing the required claims" (or an equivalent auth/access-denied message), consistent with the in-run tracking and persistence rules below. Do NOT record other 4xx responses as denials: a validation error (a 400 such as "Dates not in range", "at most 3 months", or a bad metric or param) is a schema or transient problem (handle per § error-rendering Pattern 2), and a country-coverage gap (per § Country-coverage gap detection / § Precedence) is a per-(tool, country) plan limitation, NOT a tool denial. Recording a validation error or a country gap in `tools_inaccessible` would poison the map and wrongly skip a tool the plan actually grants.
4. At the end of the recipe (whether success, partial, or aborted), if any access-denied was observed, APPEND those tool names to `tools_inaccessible` in `~/.similarweb-plugin/capabilities.json`. Create the file with minimal shape if missing. Never overwrite known-accessible status; only append observed denials.
5. The recipe NEVER blocks on capability map state. If the map says nothing about a tool, try it. If it says inaccessible, skip (optional) or abort with a clear message (required).

State enum reduces to simple list semantics: `tools_inaccessible: ["get-X", "get-Y"]`. Tools NOT in the list are assumed accessible until observed otherwise.

**Special case:** if a recipe's REQUIRED tool returns access-denied AND there is no fallback path, render: "Tool {X} is not accessible on this plan. Required for this recipe. Aborting; contact your CSM if you believe you should have access." Exit cleanly with the Sources line.

**In-run capability tracking.** Maintain an in-memory map `inaccessible_this_run: dict[tool_name, set[domain]]` from the start of every recipe turn. Before each MCP call, check the map. After each call:

- If the tool returned 403 with "missing the required claims" wording: record `(tool, domain)` as inaccessible for the rest of this turn.
- If the tool returned 200: record `(tool, domain)` as confirmed-accessible.

**Skip rule.** If a tool has been recorded as 403-failing for THIS specific domain in this turn, skip the duplicate call. If a tool has been recorded as 403-failing on the FIRST domain attempted with that tool (i.e., no successful call to this tool in this turn yet AND we have at least one 403), assume tool-level access denial: skip ALL remaining calls to this tool for any domain in this turn, and add the tool to the `Caveats` block as "not accessible on this plan".

**Successful call resets the heuristic.** If at any point a tool returns 200 for any domain, do NOT assume tool-level denial; treat subsequent 403s on OTHER domains as domain-level restrictions (see tool-level vs domain-level rule below).

**Tool-level vs domain-level 403.** Both surface as the same 403 envelope. Distinguish by observation:

- **Tool-level**: 403 on the FIRST domain attempted with a tool, with no prior 200 from that tool in this turn. The whole tool is gated on this account. Skip all remaining domains for this tool.
- **Domain-level**: 403 on a domain AFTER at least one 200 from the same tool on another domain. The tool is accessible but this specific domain is restricted (possibly by the user's plan-tier domain quota or the brand-claims surface). Mark only that `(tool, domain)` pair as inaccessible. Continue trying the tool on other domains.
- **Render rule**: in the Caveats block, distinguish: "not accessible on this plan" (tool-level) vs "this domain not covered by your plan's brand allowlist" (domain-level).

The PPC-spend pattern is the canonical example: when one domain succeeds and other domains 403, that is a domain-level restriction, not a tool-level denial.

**Mid-run persistence.** When a 403 is observed during a recipe run:

1. Read `~/.similarweb-plugin/capabilities.json` (lazily create with `{schema_version: 2, last_updated: now, tools_inaccessible: []}` if missing).
2. If the tool is not in `tools_inaccessible` yet, append it.
3. Write the file atomically (write to a temp file in the same directory, then rename) to avoid corruption on concurrent runs.
4. Use Python 3 stdlib via Bash for the read-modify-write. Pure-bash JSON manipulation is fragile.

Idempotent: re-running with the same tool already in the list is a no-op. The map grows monotonically until a `/sw-config --refresh` resets it. Only tool-level denials persist to the map; domain-level 403s stay in the in-run map and do NOT pollute the on-disk map (a domain-level restriction on a tool the user otherwise has access to should not block future calls to that tool).

**Append-on-denial inline pattern** (bash heredoc, no BOM, idempotent, atomic write):

```bash
python3 - <<'PYEOF'
import json, os, tempfile, datetime
path = os.path.expanduser("~/.similarweb-plugin/capabilities.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
try:
    with open(path, "r", encoding="utf-8") as f:
        caps = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    caps = {"schema_version": 2, "tools_inaccessible": []}
tool = "REPLACE_WITH_TOOL_NAME"
if tool not in caps.get("tools_inaccessible", []):
    caps.setdefault("tools_inaccessible", []).append(tool)
    caps["tools_inaccessible"] = sorted(set(caps["tools_inaccessible"]))
caps["last_updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(caps, f, indent=2)
os.replace(tmp, path)
PYEOF
```

### Country-coverage gap detection (in-run)

A second failure envelope, distinct from 403: the tool itself is accessible but the user's plan does not cover the requested ISO-2 country, so only worldwide (`ww`) is on this plan for that tool. This gap surfaces in EITHER of two HTTP shapes (live-observed as the 400 form on two accounts; the 200 form is retained defensively). Per `country-coverage-gap-shape`.

The detection envelope to watch for (across MCP tools) is a country-coverage MESSAGE in either of two HTTP shapes:

- **Shape A (live-observed):** HTTP 400 with `category: client_error` (or `status_code: 400`) and an `error.error_message` carrying the country-coverage wording.
- **Shape B (retained):** HTTP 200 with `data` an empty array, empty object, or null, AND a `meta` field, status, message, or note carrying the country-coverage wording.
- In BOTH shapes the discriminator is the MESSAGE: text matching one of "no data for requested country", "country not available", "country not covered", "no coverage for country" (case-insensitive substring match). A 400 WITHOUT this message (e.g. "Dates not in range") is NOT a country gap; it stays on the validation and retry path per the distinction table below.

**Precedence (global).** Country-coverage gap detection is checked BEFORE the generic error paths. Whenever a response carries the country-coverage message (Shape A or Shape B), apply the § Skip + pivot rule below and do NOT route that response to § smoke-first branch "Other non-2xx" (no retry-once on the smoke), to § error-rendering Pattern 2 (no "unavailable this run"), or to § capability-gating access-denied recording (a country gap is a per-(tool, country) plan limitation, NOT a tool denial, so the tool is never appended to `tools_inaccessible`). This holds for the smoke probe and every batched call, in every recipe, regardless of any recipe's inline error-branch summary. The discriminator is the message; a response WITHOUT it keeps its normal path.

Maintain a parallel in-memory map: `country_unavailable_this_run: dict[(tool, country), bool]` from the start of every recipe turn. Track per-(tool, country) pair the same way `inaccessible_this_run` tracks per-(tool, domain) for 403.

### Skip + pivot rule on country-coverage gap

When the FIRST domain attempted with a (tool, country) pair returns the country-coverage-gap envelope (NOT a 403; either Shape A 400-client_error-with-country-message or Shape B 200-empty-data-with-country-message above):

1. Record `country_unavailable_this_run[(tool, country)] = True`.
2. Skip ALL remaining domains in this turn for this (tool, country) pair. Do not batch the rest.
3. Pivot strategy: substitute `country=ww` for the remaining domains for this tool in this turn. If a ww call has already succeeded for this tool in this turn, the (tool, ww) data is already cached; use it.
4. CROSS-TOOL PROPAGATION: when 2 or more distinct tools report country-coverage gap for the same country in this turn, set `country_suspicious_this_run[country] = True`. For all SUBSEQUENT tool batches in this recipe, skip the (subsequent_tool, country) batch entirely without a smoke probe. Fall back to country=ww immediately.
5. Render rule: in the Caveats block, surface one consolidated line: "Country X not on this plan; rendered worldwide. Affected tools: tool-1, tool-2, ..." Do NOT render one line per tool.

This rule pairs with § smoke-first sequencing. Recipes whose smoke probe runs at `country=ww` (e.g. sw-competitive-teardown) never trigger this path on the smoke itself; recipes whose smoke runs at the user-supplied country (e.g. sw-channel-mix, default `us`) CAN hit the gap on the very first call, in which case the same detect-and-pivot rule applies to the smoke. Either way, detection runs on the first (tool, country) call that carries the country-coverage message, smoke or batched.

### Distinction summary

| Envelope | What it means | In-run map | Skip rule |
|----------|---------------|------------|-----------|
| HTTP 403 + "missing required claims" | Account/tool gated | `inaccessible_this_run[tool]` | Skip ALL domains for that tool; fall back to optional probes; if 2+ required tools 403 trigger Pattern 5 |
| HTTP 400 client_error OR HTTP 200 empty data, WITH a "no data for requested country" message | Country not on plan for that tool | `country_unavailable_this_run[(tool, country)]` | Skip remaining domains for that (tool, country); pivot to ww; if 2+ tools country-gap for same country, propagate to subsequent tools |
| HTTP 200 + empty data for one specific domain (no country-coverage message) | That domain has no traffic for the window | NO tracking; just render n/a for that cell | None; per-domain absence is a real result |
| HTTP 5xx / timeout / validation error WITHOUT a country-coverage message | Transient or schema problem | NO tracking | Retry once per § error-rendering Pattern 2 |

### § bulk-input-from-context

When a recipe accepts a LIST of inputs (multiple domains, brands, or keywords), use whatever the user already shared in the current conversation: a pasted list, an @-mentioned file the agent already read into context, args in the prompt itself.

DO NOT scan the working directory or do filesystem globbing. Bulk-input detection is context-derived only; identical across Claude Code, Codex, Cursor, Claude.ai.

1. Inspect the conversation context for a list-shaped artifact relevant to the recipe (domains for a website recipe, brands for a brand recipe, keywords for a keyword recipe).
2. If found and count > 25: ask one confirmation question ("competitors.csv has 47 items; process top 25, all, or pick a range?"). Default option is "top 25 by rank".
3. If found and shape is ambiguous (could be domains or brand names or keywords): ask ONE crisp disambiguation question with explicit options. Never open-ended.
4. If not found, the recipe runs on its explicit args only.

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
