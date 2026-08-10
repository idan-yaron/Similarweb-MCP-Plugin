---
name: sw-setup
description: Manual capability probe for the Similarweb MCP server. Runs only when explicitly invoked via the sw-config refresh path and never auto triggers. Calls one cheap tool per category, records access, and writes a fresh capabilities map with a full probe timestamp under the home directory. Recipes never require this file; the plugin discovers access lazily at runtime and appends observed denials to the same map.
user-invocable: false
---
# sw-setup: manual capability probe

**Inherits:**
- sw-foundation-data: § window-resolution

Runs ONLY when `/sw-config --refresh` explicitly invokes it. No auto-trigger.

## Hard rules

- NEVER ask the user a question.
- NEVER auto-trigger. This skill fires only via `/sw-config --refresh`.
- NEVER write outside `$HOME/.similarweb-plugin/`.
- NEVER assume access. A 5xx or timeout marks the tool `pending`, not available.

## Step 1: Probe one tool per category

Call each of these MCP tools (sequentially is fine; the cost is ten calls one-time, 10 data credits in total). FIRST resolve presence per sw-foundation-core § tool-surface presence: tool surfaces are module-gated and drift with server releases, so a probe tool may be ABSENT from the list entirely. An absent tool is NOT called and NOT an error: record it in `tools_absent` (stamped per the capability map schema; never `tools_available = false`, never `tools_inaccessible`) and move on. If a category's documented probe tool is absent but the live list carries another tool serving the same category, probe that one instead and record ITS outcome in `tools_available` under its own name; the absent canonical tool stays in `tools_absent`. `categories_available` includes a category iff some PRESENT tool for it returned 2xx; a category whose probe tool is absent with no present alternative is `module_not_exposed`, persisted as the `tools_absent` entry plus the category's exclusion from `categories_available` (no separate field).

**Apps probe target.** `get-apps-details` is the canonical apps probe. The retarget rule above applies here like anywhere else: if it is absent from the live list but another apps tool is present, probe that one instead and record ITS outcome. Do not treat any apps name as absent without checking the live list, and do not exclude the family from retargeting. `get-apps-details` returned 403 on the reference connector through 2026-08-06 and 200 at 7 credits from 2026-08-07, so its outcome here is an account property and BOTH results are normal. A 403 still PROVES the tool is present, so IF this probe returns `403 FORBIDDEN_ERROR`, record it as a denial (`tools_available = false` plus the `tools_inaccessible` append), never as an absence. Do not presume the outcome: an account carrying the Apps module returns 2xx here, and that is a normal result. A 403 on this probe alone NEVER means the credentials are bad (see the auth-invalid edge case).

| Category | MCP tool | Params |
|----------|----------|--------|
| websites | `get-websites-website-rank` | `{"domain": "google.com", "start_date": "2_months_ago", "end_date": "latest"}` |
| keywords | `get-keywords-overview` | `{"keyword": "similarweb"}` |
| apps | `get-apps-details` | `{"store": "apple", "app_id": "389801252"}` (both required per the live schema; this is the pair actually exercised live) |
| brands | `get-brands-search` | `{"domain": "amazon.com", "search_term": "apple"}` |
| categories | `get-categories-search` | `{"domain": "amazon.com", "search_term": "technology"}` |
| lead-enrichment | `get-lead-enrichment-website` | `{"domain": "similarweb.com"}` |
| ai-traffic | `get-ai-traffic-overview` | `{"domain": "nike.com", "country": "ww", "start_date": "latest", "end_date": "latest"}` (PIN THE WINDOW: the server default spans about three years and rows are months times active LLM sources, so an unpinned probe is the widest call the tool offers) |
| retail-cross | `get-retail-cross-analysis-describe` | `{"limit": 1}` (1.3 KB bounded, 53.4 KB at the server default) |
| demand | `get-demand-search-trends-aggregated` | `{"country": "us", "topic": "running shoes", "granularity": "monthly", "start_date": "latest", "end_date": "latest"}` (uncharged, one `{volume}` row; NEVER probe the `-keywords-aggregated` sibling, which has no `limit` and returned about 77 KB) |
| sales-signals | `get-sales-signals-traffic` | `{"company_domain": "shopify.com"}` (pass NO dates; flat 10 credits, the only charged probe in the matrix) |


**Why these probe shapes, and what is deliberately NOT probed.** Every probe is either a bounded call or a describe that takes no bound. NO never-inline tool enters this matrix: `get-user-segments-describe` (23.9 MB) and `get-gen-ai-campaigns` (1.9 MB bare) are never called here or anywhere, per sw-foundation-core § payload-budget. The industry family is deliberately UNPROBED: its only free entry point is a describe of about 17 KB, and the payload budget binds the whole setup turn, so paying a third of the turn budget for one category is a bad trade when industry access has tracked the websites category on every account observed. If that ever diverges, add the probe and accept the cost. Ten probes at these shapes cost 10 data credits in total, all from the sales-signals row.

For each call:
- Success (2xx with payload) => `tools_available[<tool>] = true`
- HTTP 403 with `error.code` FORBIDDEN_ERROR (match on status and code, never on message text: the wording drifted from "Access denied. The user might be missing the required claims for this tool." to "Access forbidden. Upgrade your account." between server releases, per `partial-access-envelope-shape`) => `tools_available[<tool>] = false` AND append the tool name to `tools_inaccessible`. This is the ONLY outcome that appends to `tools_inaccessible` (the v0.1.13 rule in sw-foundation-core § capability-gating: a validation 400 recorded as a denial would poison the map).
- Any other `client_error` response (e.g. a validation 400 such as "Dates not in range") => `tools_available[<tool>] = false` only; do NOT append to `tools_inaccessible`.
- Client-level unknown-tool error on a name the list contained (message-gated per `unknown-tool-error-shape`) => treat as absence: record in `tools_absent`, leave it out of `tools_available`, never `tools_inaccessible`.
- `server_error` or unparseable => `tools_available[<tool>] = "pending"`
- Timeout or no response => `tools_available[<tool>] = "pending"`

Recommended approach: invoke each MCP tool via the AI client's native MCP surface; record the outcome in working memory; parallelize when the client supports it.

The rank probe uses `end_date="latest"` (the server resolves to actual `meta.last_updated`) per sw-foundation-data § window-resolution. Passing `end_date = today` or `end_date = first day of current month` 4xxs because `meta.last_updated` lags by days.

**Coverage seed: DISABLED. Do NOT call `get-user-segments-describe`.** It is free in credits and 23,918,985 characters on a real account (2026-08-07), which exhausts the context window rather than returning an error. Its advertised `length` and `chars` parameters are accepted but inert, so no bound makes it safe, and an overflow is not recoverable: there is no error envelope, no retry, and no turn left in which to apply a skip rule. Free in credits is not free in context, and the two are independent; the tool is never-inline per sw-foundation-core § payload-budget.

The seed stays disabled until the platform can hand a raw tool result to a file before it reaches the model. No supported client is known to do that today, so treat this as off everywhere rather than as a condition that might fire. Skip Step 2.5 entirely and continue to Step 3; the rest of setup is unaffected. Grounded in `describe-envelope-and-coverage-probe`.

## Step 2: Write capabilities.json

Feed the probe outcomes to the bundled writer at `scripts/capmap.py` (a build-time copy of sw-foundation-core's single source; Python 3, atomic write, no BOM, never improvised inline code). Write ONE JSON document to a temp file with the Write tool (cross-platform, no shell heredoc), then run `python3 scripts/capmap.py init --file <tempfile>` (use `python` if `python3` is unavailable, e.g. on Windows). Document shape. Every value below is ILLUSTRATIVE and MUST be replaced with what THIS run actually observed; never copy the booleans or the lists verbatim. The example happens to show an account whose apps, brands, and lead-enrichment probes returned 403 (denials, not absences) and one tool absent from the live surface, purely to exercise every field. An account with those claims writes `true` for them and a shorter `tools_inaccessible`:

```json
{
  "mcp_server_version": "<populated-from-probe>",
  "state": "ready",
  "tools": ["<every unqualified name from the live enumeration; omit or leave empty when no qualifying evidence exists>"],
  "prefix": "<observed-prefix>",
  "tools_available": {
    "get-websites-website-rank": true,
    "get-keywords-overview": true,
    "get-apps-details": false,
    "get-brands-search": false,
    "get-categories-search": true,
    "get-lead-enrichment-website": false
  },
  "tools_inaccessible": ["get-apps-details", "get-brands-search", "get-lead-enrichment-website"],
  "tools_absent": [{"name": "get-websites-conversion-rates-agg", "observed_under": "<surface-hash>", "observed_at": "<date>"}],
  "categories_available": ["websites", "keywords", "categories", "ai-traffic", "demand"]
}
```

`state` is one of ready | auth_invalid | mcp_not_configured | probe_partial. `tools_available` carries CALLED probe outcomes only (true | false | "pending"). The script computes the timestamps (`last_full_probe`, `last_updated`, `refresh_after` 30 days out), fingerprints `tools` into `tool_surface` (omitted when `tools` is empty: no qualifying enumeration, no fingerprint), and stamps each `tools_absent` name with that surface hash.

This write OVERWRITES any existing `capabilities.json` (including lazy-built append-only state). That is the point of `/sw-config --refresh`: a clean, full known-state map. If the script file is missing, skip the write, keep the probe results in conversation context, and surface one line that the plugin bundle is incomplete (reinstall to restore it); NEVER improvise replacement code.

## Step 2.5: Seed coverage (DORMANT, not reachable)

**This step does not run.** Its only input was the Step 1 coverage seed, which is disabled, so there is nothing to write. Skip straight from Step 2 to Step 3. The mechanism below is kept, not retired: `capmap.py coverage` still works and the schema still reads a coverage block, so restoring the seed later is a one-line change rather than a rebuild. Do NOT substitute another tool here to keep the step alive; `get-industry-demographics-describe` reports industry-module coverage, not `traffic_and_engagement` coverage, and treating those as equivalent would write a wrong coverage block rather than none.

Recipes therefore resolve their default country from their documented default plus the country-coverage pivot (a sacrificial 400), which is the pre-v0.1.17 behavior. Two other consumers also go dark while the block is absent, and both fail open by design: the `data_window.start` clamp is unavailable, so a recipe that widens its window must not assume history it has not observed and stays within its own documented floor; and the `fresh_data` daily-slice hint is unavailable, which costs nothing because a live response's `meta.last_updated` was always the freshness source of truth.

For reference, when the seed is restored: write ONE JSON document to a temp file with the Write tool, then run `python3 scripts/capmap.py coverage --file <tempfile>`. Document shape:

```json
{
  "countries": ["world", "ww"],
  "data_window": {"start": "2023-05", "end": "2026-05"},
  "fresh_data": "2026-06-09",
  "segments": []
}
```

`observed_under` is omitted on purpose: the writer stamps the coverage block with the map's current `tool_surface.hash` (just written by init) so a later surface change quarantines it automatically. The coverage write touches ONLY the coverage block, never `state` or the tool lists. While the seed is disabled there is no input, so this step is always skipped and no coverage block is written; recipes fall back to their documented defaults plus the country-coverage pivot.

## Step 3: Done

Exit silently. Return control to sw-config with no user-visible output; sw-config renders the summary.

## Edge cases

- **`$HOME/.similarweb-plugin/` not writable**: catch the error from `mkdir`, log to stderr ("filesystem read-only; capabilities will not persist this session"), keep the probe results in conversation context only.
- **All ten probes return 5xx**: write capabilities.json with `tools_available: {}` and `state: "probe_partial"`. Next refresh retries fully.
- **MCP server not configured in the client**: `mcp_not_configured` requires ZERO Similarweb-scoped names in the live enumeration, or enumeration impossible AND every probe raising the client-level unknown-tool error. When enumeration found a non-empty Similarweb surface or ANY probe returned 2xx, a client-level unknown-tool error on one probe means that TOOL is absent (record in `tools_absent` per Step 1), never `mcp_not_configured`. Only in the true not-configured case: write `capabilities.json` with `state: "mcp_not_configured"` and exit; sw-config surfaces the configuration message.
- **Auth-invalid envelope**: write `capabilities.json` with `state: "auth_invalid"` ONLY when the failure is account-wide, never on a single per-tool denial. Account-wide means: a probe returns `status_code: 401`, OR a 403 whose `error.code` is NOT `FORBIDDEN_ERROR`, OR EVERY probe in the matrix returns 401/403. A `403 FORBIDDEN_ERROR` on SOME probes is a per-tool claims denial per Step 1 and leaves `state: "ready"` (this is the EXPECTED outcome for the apps probe on accounts without the Apps module, so treating it as auth-invalid would tell a user with valid credentials that their key was rejected). Per `auth-invalid-envelope-shape` and `partial-access-envelope-shape`.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- auth-invalid-envelope-shape
- partial-access-envelope-shape
- cheap-probe-tool-per-category
- mcp-tool-catalog-v1
- unknown-tool-error-shape
- describe-envelope-and-coverage-probe
