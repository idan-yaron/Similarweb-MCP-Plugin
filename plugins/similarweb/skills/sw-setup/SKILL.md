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

Call each of these MCP tools (sequentially is fine; the cost is six cheap calls one-time). FIRST resolve presence per sw-foundation-core § tool-surface presence: tool surfaces are module-gated and drift with server releases, so a probe tool may be ABSENT from the list entirely (observed live for the apps surface). An absent tool is NOT called and NOT an error: record it in `tools_absent` (stamped per the capability map schema; never `tools_available = false`, never `tools_inaccessible`) and move on. If a category's documented probe tool is absent but the live list carries another tool serving the same category, probe that one instead and record ITS outcome in `tools_available` under its own name; the absent canonical tool stays in `tools_absent`. `categories_available` includes a category iff some PRESENT tool for it returned 2xx; a category whose probe tool is absent with no present alternative is `module_not_exposed`, persisted as the `tools_absent` entry plus the category's exclusion from `categories_available` (no separate field).

**Apps has no alternative left.** `get-apps-details` is the canonical apps probe and the only apps tool on the live surface as of the 2026-08-06 enumeration; the previous apps probe target and its siblings were absent from two consecutive enumerations (2026-06-11 and 2026-08-06), so they are documented-absent in sw-foundation-core § apps-catalog rather than probed here. `get-apps-details` returned 403 on the grounded connector, and a 403 PROVES the tool is present, so IF this probe returns `403 FORBIDDEN_ERROR`, record it as a denial (`tools_available = false` plus the `tools_inaccessible` append), never as an absence. Do not presume the outcome: an account carrying the Apps module returns 2xx here, and that is a normal result. A 403 on this probe alone NEVER means the credentials are bad (see the auth-invalid edge case).

| Category | MCP tool | Params |
|----------|----------|--------|
| websites | `get-websites-website-rank` | `{"domain": "google.com", "start_date": "2_months_ago", "end_date": "latest"}` |
| keywords | `get-keywords-overview` | `{"keyword": "similarweb"}` |
| apps | `get-apps-details` | `{"store": "apple", "app_id": "389801252"}` (both required per the live schema; this is the pair actually exercised live) |
| brands | `get-brands-search` | `{"domain": "amazon.com", "search_term": "apple"}` |
| categories | `get-categories-search` | `{"domain": "amazon.com", "search_term": "technology"}` |
| lead-enrichment | `get-lead-enrichment-website` | `{"domain": "similarweb.com"}` |

For each call:
- Success (2xx with payload) => `tools_available[<tool>] = true`
- HTTP 403 with `error.code` FORBIDDEN_ERROR (match on status and code, never on message text: the wording drifted from "Access denied. The user might be missing the required claims for this tool." to "Access forbidden. Upgrade your account." between server releases, per `partial-access-envelope-shape`) => `tools_available[<tool>] = false` AND append the tool name to `tools_inaccessible`. This is the ONLY outcome that appends to `tools_inaccessible` (the v0.1.13 rule in sw-foundation-core § capability-gating: a validation 400 recorded as a denial would poison the map).
- Any other `client_error` response (e.g. a validation 400 such as "Dates not in range") => `tools_available[<tool>] = false` only; do NOT append to `tools_inaccessible`.
- Client-level unknown-tool error on a name the list contained (message-gated per `unknown-tool-error-shape`) => treat as absence: record in `tools_absent`, leave it out of `tools_available`, never `tools_inaccessible`.
- `server_error` or unparseable => `tools_available[<tool>] = "pending"`
- Timeout or no response => `tools_available[<tool>] = "pending"`

Recommended approach: invoke each MCP tool via the AI client's native MCP surface; record the outcome in working memory; parallelize when the client supports it.

The rank probe uses `end_date="latest"` (the server resolves to actual `meta.last_updated`) per sw-foundation-data § window-resolution. Passing `end_date = today` or `end_date = first day of current month` 4xxs because `meta.last_updated` lags by days.

**Coverage seed (free, uncharged).** Also call `get-user-segments-describe` (no params; it returns the `{response}` envelope, not the `{meta, data}` shape). From `response.traffic_and_engagement.countries` capture the covered country codes (the object keys; `world` is the alias for `ww`); from any one country entry capture its `start_date`/`end_date` (the account's `data_window`) and `fresh_data`; from `response.segments` capture the segment list. This is the seeding input for Step 2.5. A failed or absent describe simply skips the coverage write; the rest of setup is unaffected. Grounded in `describe-envelope-and-coverage-probe`.

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
  "tools_absent": [{"tool": "get-websites-conversion-rates-agg", "observed_under": "<surface-hash>", "observed_at": "<date>"}],
  "categories_available": ["websites", "keywords", "categories"]
}
```

`state` is one of ready | auth_invalid | mcp_not_configured | probe_partial. `tools_available` carries CALLED probe outcomes only (true | false | "pending"). The script computes the timestamps (`last_full_probe`, `last_updated`, `refresh_after` 30 days out), fingerprints `tools` into `tool_surface` (omitted when `tools` is empty: no qualifying enumeration, no fingerprint), and stamps each `tools_absent` name with that surface hash.

This write OVERWRITES any existing `capabilities.json` (including lazy-built append-only state). That is the point of `/sw-config --refresh`: a clean, full known-state map. If the script file is missing, skip the write, keep the probe results in conversation context, and surface one line that the plugin bundle is incomplete (reinstall to restore it); NEVER improvise replacement code.

## Step 2.5: Seed coverage (after the init write)

After the init write succeeds, record the account's data coverage so recipes resolve their default country without burning a sacrificial country 400 (per sw-foundation-core § default-country resolution). Write ONE JSON document to a temp file with the Write tool, then run `python3 scripts/capmap.py coverage --file <tempfile>`. Document shape (substitute the values captured by the Step 1 coverage seed):

```json
{
  "countries": ["world", "ww"],
  "data_window": {"start": "2023-05", "end": "2026-05"},
  "fresh_data": "2026-06-09",
  "segments": []
}
```

`observed_under` is omitted on purpose: the writer stamps the coverage block with the map's current `tool_surface.hash` (just written by init) so a later surface change quarantines it automatically. The coverage write touches ONLY the coverage block, never `state` or the tool lists. If the Step 1 describe failed or returned no countries, SKIP this step entirely; recipes then fall back to their documented defaults plus the country-coverage pivot.

## Step 3: Done

Exit silently. Return control to sw-config with no user-visible output; sw-config renders the summary.

## Edge cases

- **`$HOME/.similarweb-plugin/` not writable**: catch the error from `mkdir`, log to stderr ("filesystem read-only; capabilities will not persist this session"), keep the probe results in conversation context only.
- **All six probes return 5xx**: write capabilities.json with `tools_available: {}` and `state: "probe_partial"`. Next refresh retries fully.
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
