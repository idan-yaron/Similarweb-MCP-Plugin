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

Call each of these MCP tools (sequentially is fine; the cost is six cheap calls one-time). FIRST resolve presence per sw-foundation-core § tool-surface presence: tool surfaces are module-gated and drift with server releases, so a probe tool may be ABSENT from the list entirely (observed live for the apps surface). An absent tool is NOT called and NOT an error: record it in `tools_absent` (stamped per the capability map schema; never `tools_available = false`, never `tools_inaccessible`) and move on. If a category's documented probe tool is absent but a sibling tool for the same category exists in the live list (e.g. `get-apps-details` instead of `get-apps-search`), probe the sibling instead and record the SIBLING's outcome in `tools_available` under the sibling's name; the absent canonical tool stays in `tools_absent`. `categories_available` includes a category iff some PRESENT tool for it returned 2xx; a category whose probe tool is absent with no present sibling is `module_not_exposed`, persisted as the `tools_absent` entry plus the category's exclusion from `categories_available` (no separate field).

| Category | MCP tool | Params |
|----------|----------|--------|
| websites | `get-websites-website-rank` | `{"domain": "google.com", "start_date": "2_months_ago", "end_date": "latest"}` |
| keywords | `get-keywords-overview` | `{"keyword": "similarweb"}` |
| apps | `get-apps-search` | `{"term": "instagram"}` |
| brands | `get-brands-search` | `{"domain": "amazon.com", "search_term": "apple"}` |
| categories | `get-categories-search` | `{"domain": "amazon.com", "search_term": "technology"}` |
| lead-enrichment | `get-lead-enrichment-website` | `{"domain": "similarweb.com"}` |

For each call:
- Success (2xx with payload) => `tools_available[<tool>] = true`
- HTTP 403 carrying "missing the required claims" (or an equivalent access-denied message, per `auth-invalid-envelope-shape`) => `tools_available[<tool>] = false` AND append the tool name to `tools_inaccessible`. This is the ONLY outcome that appends to `tools_inaccessible` (the v0.1.13 rule in sw-foundation-core § capability-gating: a validation 400 recorded as a denial would poison the map).
- Any other `client_error` response (e.g. a validation 400 such as "Dates not in range") => `tools_available[<tool>] = false` only; do NOT append to `tools_inaccessible`.
- Client-level unknown-tool error on a name the list contained (message-gated per `unknown-tool-error-shape`) => treat as absence: record in `tools_absent`, leave it out of `tools_available`, never `tools_inaccessible`.
- `server_error` or unparseable => `tools_available[<tool>] = "pending"`
- Timeout or no response => `tools_available[<tool>] = "pending"`

Recommended approach: invoke each MCP tool via the AI client's native MCP surface; record the outcome in working memory; parallelize when the client supports it.

The rank probe uses `end_date="latest"` (the server resolves to actual `meta.last_updated`) per sw-foundation-data § window-resolution. Passing `end_date = today` or `end_date = first day of current month` 4xxs because `meta.last_updated` lags by days.

## Step 2: Write capabilities.json

Feed the probe outcomes to the bundled writer at `scripts/capmap.py` (a build-time copy of sw-foundation-core's single source; Python 3 via Bash, atomic write, no BOM, never improvised inline code). Pipe ONE JSON document on stdin to the script's init subcommand, e.g. `python3 scripts/capmap.py init <<'JSONEOF' ... JSONEOF`. Document shape (the AI client substitutes the actual probe outcomes; example values shown, apps probed via the sibling get-apps-details):

```json
{
  "mcp_server_version": "<populated-from-probe>",
  "state": "ready",
  "tools": ["<every unqualified name from the live enumeration; omit or leave empty when no qualifying evidence exists>"],
  "prefix": "<observed-prefix>",
  "tools_available": {
    "get-websites-website-rank": true,
    "get-keywords-overview": true,
    "get-apps-details": true,
    "get-brands-search": false,
    "get-categories-search": true,
    "get-lead-enrichment-website": false
  },
  "tools_inaccessible": ["get-brands-search", "get-lead-enrichment-website"],
  "tools_absent": ["get-apps-search"],
  "categories_available": ["websites", "keywords", "apps", "categories"]
}
```

`state` is one of ready | auth_invalid | mcp_not_configured | probe_partial. `tools_available` carries CALLED probe outcomes only (true | false | "pending"). The script computes the timestamps (`last_full_probe`, `last_updated`, `refresh_after` 30 days out), fingerprints `tools` into `tool_surface` (omitted when `tools` is empty: no qualifying enumeration, no fingerprint), and stamps each `tools_absent` name with that surface hash.

This write OVERWRITES any existing `capabilities.json` (including lazy-built append-only state). That is the point of `/sw-config --refresh`: a clean, full known-state map. If the script file is missing, skip the write, keep the probe results in conversation context, and surface one line that the plugin bundle is incomplete (reinstall to restore it); NEVER improvise replacement code.

## Step 3: Done

Exit silently. Return control to sw-config with no user-visible output; sw-config renders the summary.

## Edge cases

- **`$HOME/.similarweb-plugin/` not writable**: catch the error from `mkdir`, log to stderr ("filesystem read-only; capabilities will not persist this session"), keep the probe results in conversation context only.
- **All six probes return 5xx**: write capabilities.json with `tools_available: {}` and `state: "probe_partial"`. Next refresh retries fully.
- **MCP server not configured in the client**: `mcp_not_configured` requires ZERO Similarweb-scoped names in the live enumeration, or enumeration impossible AND every probe raising the client-level unknown-tool error. When enumeration found a non-empty Similarweb surface or ANY probe returned 2xx, a client-level unknown-tool error on one probe means that TOOL is absent (record in `tools_absent` per Step 1), never `mcp_not_configured`. Only in the true not-configured case: write `capabilities.json` with `state: "mcp_not_configured"` and exit; sw-config surfaces the configuration message.
- **Auth-invalid envelope** (any probe returns `error.category == "client_error"` with `status_code` in `{401, 403}` per `auth-invalid-envelope-shape`): write `capabilities.json` with `state: "auth_invalid"`. sw-config surfaces a re-auth prompt instead of attempting tool calls.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- auth-invalid-envelope-shape
- partial-access-envelope-shape
- cheap-probe-tool-per-category
- mcp-tool-catalog-v1
- unknown-tool-error-shape
