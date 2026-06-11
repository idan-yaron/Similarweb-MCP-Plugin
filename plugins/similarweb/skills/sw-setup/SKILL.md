---
name: sw-setup
description: Manual capability probe for the Similarweb MCP server. Runs only when explicitly invoked via the sw-config refresh path; does NOT auto-trigger. Calls one cheap MCP tool per category (websites, keywords, apps, brands, categories, lead enrichment), records which tools the user has access to, and writes a fresh capabilities.json with a tools available map and a last full probe timestamp at $HOME/.similarweb-plugin/. Recipes do not require this file; the plugin runs lazily and discovers access at runtime via the foundation render error pattern, then appends observed denials to the same file. This skill exists as a manual recovery path for users who want a thorough up front map.
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

Call each of these MCP tools (sequentially is fine; the cost is six cheap calls one-time). FIRST check the client's live tool list: tool surfaces are module-gated and drift with server releases, so a probe tool may be ABSENT from the list entirely (observed live for the apps surface on plans without the Apps module). An absent tool is NOT called and NOT an error: record `tools_available[<tool>] = false`, note the category as `module_not_exposed` in working memory, and move on. If a category's documented probe tool is absent but a sibling tool for the same category exists in the live list (e.g. `get-apps-details` instead of `get-apps-search`), probe the sibling instead and record under the sibling's name.

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
- Any non-2xx response (auth failure, access denied, validation error, server error) => record as `tools_available[<tool>] = false` if the response category is `client_error` (per `auth-invalid-envelope-shape`), AND append the tool name to `tools_inaccessible`. Mark `pending` if it's `server_error` or unparseable.
- Timeout or no response => `tools_available[<tool>] = "pending"`

Recommended approach: invoke each MCP tool via the AI client's native MCP surface; record the outcome in working memory; parallelize when the client supports it.

The rank probe uses `end_date="latest"` (the server resolves to actual `meta.last_updated`) per sw-foundation-data § window-resolution. Passing `end_date = today` or `end_date = first day of current month` 4xxs because `meta.last_updated` lags by days.

## Step 2: Write capabilities.json

Use Python via Bash to avoid BOM issues on Windows (per project rule):

```bash
python3 - <<'PYEOF'
import json, os, datetime
caps = {
  "schema_version": 2,
  "mcp_server_version": "<populated-from-probe>",  # the AI client substitutes the actual probed server version here at runtime
  "last_full_probe": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "last_updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "refresh_after": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "state": "ready",  # one of: ready | auth_invalid | mcp_not_configured | probe_partial
  "tools_available": {
    # populated from probe outcomes; example:
    "get-websites-website-rank": True,
    "get-keywords-overview": True,
    "get-apps-search": True,
    "get-brands-search": False,
    "get-categories-search": True,
    "get-lead-enrichment-website": False,
  },
  "tools_inaccessible": ["get-brands-search", "get-lead-enrichment-website"],
  "categories_available": ["websites", "keywords", "apps", "categories"],
}
path = os.path.expanduser("~/.similarweb-plugin/capabilities.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
  json.dump(caps, f, indent=2)
PYEOF
```

The values above are placeholders; the AI client substitutes the actual probe outcomes before running the heredoc.

This write OVERWRITES any existing `capabilities.json` (including lazy-built append-only state). That is the point of `/sw-config --refresh`: a clean, full known-state map.

## Step 3: Done

Exit silently. Return control to sw-config with no user-visible output; sw-config renders the summary.

## Edge cases

- **`$HOME/.similarweb-plugin/` not writable**: catch the error from `mkdir`, log to stderr ("filesystem read-only; capabilities will not persist this session"), keep the probe results in conversation context only.
- **All six probes return 5xx**: write capabilities.json with `tools_available: {}` and `state: "probe_partial"`. Next refresh retries fully.
- **MCP server not configured in the client**: probe call raises a client-level error ("tool not found"). Skill catches, writes `capabilities.json` with `state: "mcp_not_configured"`, and exits. sw-config surfaces the configuration message.
- **Auth-invalid envelope** (any probe returns `error.category == "client_error"` with `status_code` in `{401, 403}` per `auth-invalid-envelope-shape`): write `capabilities.json` with `state: "auth_invalid"`. sw-config surfaces a re-auth prompt instead of attempting tool calls.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- auth-invalid-envelope-shape
- partial-access-envelope-shape
- cheap-probe-tool-per-category
- mcp-tool-catalog-v1
