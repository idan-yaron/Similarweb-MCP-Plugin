# § capability-gating, full doctrine (sw-foundation-core reference)

The capability map at `~/.similarweb-plugin/capabilities.json` is an OPTIONAL hint, not a hard prerequisite. Recipes proceed without it.

## Pattern (each recipe Step 2)

1. Try to read `~/.similarweb-plugin/capabilities.json`. If present and not expired, use its `tools_inaccessible` list (and `tools_available` map if also present) to pre-filter the call plan (skip OPTIONAL tools known to be inaccessible; abort if REQUIRED tools are flagged inaccessible). Legacy schema-v1 maps (`schema_version: 1`, the early full-probe shape) carry denials as `tools_available: false` entries: those gate access exactly like v2 denial records (the access-gate reading; presence-wise they remain non-evidence per the read-path precedence). Expiry applies only to full-probe maps via their `refresh_after` field; a lazy append-only map (no `refresh_after`) never expires, it is an advisory set of observed denials.
2. If missing or expired, proceed with no prior knowledge. Execute the recipe's planned tool calls.
3. Wrap each tool call in § error-rendering pattern 3 handling. Record a tool as access-denied ONLY on an actual access error: HTTP 403 carrying "missing the required claims" (or an equivalent auth/access-denied message), consistent with the in-run tracking and persistence rules below. Do NOT record other 4xx responses as denials: a validation error (a 400 such as "Dates not in range", "at most 3 months", or a bad metric or param) is a schema or transient problem (handle per § error-rendering Pattern 2), and a country-coverage gap (per § Country-coverage gap detection / § Precedence) is a per-(tool, country) plan limitation, NOT a tool denial. Recording a validation error or a country gap in `tools_inaccessible` would poison the map and wrongly skip a tool the plan actually grants. An ABSENT tool (per § tool-surface presence) is likewise never recorded here; absence persists to `tools_absent` per the capability map schema.
4. At the end of the recipe (whether success, partial, or aborted), if any access-denied was observed, APPEND those tool names to `tools_inaccessible` in `~/.similarweb-plugin/capabilities.json`. Create the file with minimal shape if missing. Never overwrite known-accessible status; only append observed denials.
5. The recipe NEVER blocks on capability map state. If the map says nothing about a tool, try it. If it says inaccessible, skip (optional) or abort with a clear message (required).

State enum reduces to simple list semantics: `tools_inaccessible: ["get-X", "get-Y"]`. Tools NOT in the list are assumed accessible until observed otherwise.

**Special case:** if a recipe's REQUIRED tool returns access-denied AND there is no fallback path, render: "Tool {X} is not accessible on this plan. Required for this recipe. Aborting; contact your CSM if you believe you should have access." Exit cleanly with the Sources line.

## In-run capability tracking

Maintain an in-memory map `inaccessible_this_run: dict[tool_name, set[domain]]` from the start of every recipe turn. Before each MCP call, check the map. After each call:

- If the tool returned 403 with "missing the required claims" wording: record `(tool, domain)` as inaccessible for the rest of this turn.
- If the tool returned 200: record `(tool, domain)` as confirmed-accessible.

**Skip rule.** If a tool has been recorded as 403-failing for THIS specific domain in this turn, skip the duplicate call. If a tool has been recorded as 403-failing on the FIRST domain attempted with that tool (i.e., no successful call to this tool in this turn yet AND we have at least one 403), assume tool-level access denial: skip ALL remaining calls to this tool for any domain in this turn, and add the tool to the `Caveats` block as "not accessible on this plan".

**Successful call resets the heuristic.** If at any point a tool returns 200 for any domain, do NOT assume tool-level denial; treat subsequent 403s on OTHER domains as domain-level restrictions (see tool-level vs domain-level rule below).

## Tool-level vs domain-level 403

Both surface as the same 403 envelope. Distinguish by observation:

- **Tool-level**: 403 on the FIRST domain attempted with a tool, with no prior 200 from that tool in this turn. The whole tool is gated on this account. Skip all remaining domains for this tool.
- **Domain-level**: 403 on a domain AFTER at least one 200 from the same tool on another domain. The tool is accessible but this specific domain is restricted (possibly by the user's plan-tier domain quota or the brand-claims surface). Mark only that `(tool, domain)` pair as inaccessible. Continue trying the tool on other domains.
- **Render rule**: in the Caveats block, distinguish: "not accessible on this plan" (tool-level) vs "this domain not covered by your plan's brand allowlist" (domain-level).

The PPC-spend pattern is the canonical example: when one domain succeeds and other domains 403, that is a domain-level restriction, not a tool-level denial.

## Mid-run persistence

When a 403 is observed during a recipe run: append the tool to `tools_inaccessible` via the bundled capmap script's deny subcommand (the invocation is documented in sw-foundation-core SKILL.md § capability-gating). Idempotent: re-running with the same tool already in the list is a no-op. The map grows monotonically until a `/sw-config --refresh` resets it. Only tool-level denials persist to the map; domain-level 403s stay in the in-run map and do NOT pollute the on-disk map (a domain-level restriction on a tool the user otherwise has access to should not block future calls to that tool).
