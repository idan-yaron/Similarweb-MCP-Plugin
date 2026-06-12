# Country-coverage gap, full detection and pivot rules (sw-foundation-core reference)

## Detection (in-run)

A second failure envelope, distinct from 403: the tool itself is accessible but the user's plan does not cover the requested ISO-2 country, so only worldwide (`ww`) is on this plan for that tool. This gap surfaces in EITHER of two HTTP shapes (live-observed as the 400 form on two accounts; the 200 form is retained defensively). Per `country-coverage-gap-shape`.

The detection envelope to watch for (across MCP tools) is a country-coverage MESSAGE in either of two HTTP shapes:

- **Shape A (live-observed):** HTTP 400 with `category: client_error` (or `status_code: 400`) and an `error.error_message` carrying the country-coverage wording.
- **Shape B (retained):** HTTP 200 with `data` an empty array, empty object, or null, AND a `meta` field, status, message, or note carrying the country-coverage wording.
- In BOTH shapes the discriminator is the MESSAGE: text matching one of "no data for requested country", "country not available", "country not covered", "no coverage for country" (case-insensitive substring match). A 400 WITHOUT this message (e.g. "Dates not in range") is NOT a country gap; it stays on the validation and retry path per the distinction summary table.

**Precedence (global).** Country-coverage gap detection is checked BEFORE the generic error paths. Whenever a response carries the country-coverage message (Shape A or Shape B), apply the Skip + pivot rule below and do NOT route that response to § smoke-first branch "Other non-2xx" (no retry-once on the smoke), to § error-rendering Pattern 2 (no "unavailable this run"), or to § capability-gating access-denied recording (a country gap is a per-(tool, country) plan limitation, NOT a tool denial, so the tool is never appended to `tools_inaccessible`). This holds for the smoke probe and every batched call, in every recipe, regardless of any recipe's inline error-branch summary. The discriminator is the message; a response WITHOUT it keeps its normal path.

Maintain a parallel in-memory map: `country_unavailable_this_run: dict[(tool, country), bool]` from the start of every recipe turn. Track per-(tool, country) pair the same way `inaccessible_this_run` tracks per-(tool, domain) for 403.

## Skip + pivot rule

When the FIRST domain attempted with a (tool, country) pair returns the country-coverage-gap envelope (NOT a 403; either Shape A 400-client_error-with-country-message or Shape B 200-empty-data-with-country-message above):

1. Record `country_unavailable_this_run[(tool, country)] = True`.
2. Skip ALL remaining domains in this turn for this (tool, country) pair. Do not batch the rest. "Remaining" means not-yet-dispatched: sibling calls already in flight in the same parallel batch are not retracted (their gap responses are uncharged and recorded); whether a per-domain batch was dispatched in parallel before the first gap returned is an execution-environment detail, and both shapes comply.
3. Pivot strategy: substitute `country=ww` for the remaining domains for this tool in this turn. If a ww call has already succeeded for this tool in this turn, the (tool, ww) data is already cached; use it.
4. CROSS-TOOL PROPAGATION: when 2 or more distinct tools report country-coverage gap for the same country in this turn, set `country_suspicious_this_run[country] = True`. For all SUBSEQUENT tool batches in this recipe, skip the (subsequent_tool, country) batch entirely without a smoke probe. Fall back to country=ww immediately.
5. Render rule: in the Caveats block, surface one consolidated line: "Country X not on this plan; rendered worldwide. Affected tools: tool-1, tool-2, ..." Do NOT render one line per tool. Once the run has pivoted, the header line renders the pivoted country (`ww`), not the requested one, per sw-foundation-render § error-rendering Pattern 6 main text.

This rule pairs with § smoke-first sequencing. Recipes whose smoke probe runs at `country=ww` (e.g. sw-competitive-teardown) never trigger this path on the smoke itself; recipes whose smoke runs at the user-supplied country (e.g. sw-channel-mix, default `us`) CAN hit the gap on the very first call, in which case the same detect-and-pivot rule applies to the smoke. Either way, detection runs on the first (tool, country) call that carries the country-coverage message, smoke or batched.
