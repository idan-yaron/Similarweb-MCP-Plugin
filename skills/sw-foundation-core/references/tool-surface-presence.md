# § tool-surface presence, full rules (sw-foundation-core reference)

Presence ("does this tool exist on this connector?") is a gating axis SEPARATE from access (403 claims) and country coverage. It is the only axis that is free to detect: the AI client hands every session the connector's tool list at zero data credits. Detect it live at planning time; never spend a call to discover what the list already states. Grounded in `mcp-tool-catalog-v1` (the surface drifts per account and per release: 90 tools on 2026-05-16, 80 on 2026-06-11, 113 on 2026-08-06, 129 on 2026-08-10, all on the same connector, and names that were absent for two months have since returned; plan-gating vs server drift is unresolved per `plan-gating-vs-server-drift`) and `unknown-tool-error-shape`.

**Names drift, not just counts.** The 2026-08-06 enumeration retired 8 names in a single wave, all of them renames into the `get-website-analysis-*` namespace (the `get-traffic-*` prefix was eliminated entirely). A renamed tool reads as ABSENT to the pre-filter, so a stale catalog row silently fires a denial outcome on a capability the account fully has. That is not hypothetical: it is exactly how the 2026-08 wave broke two shipped recipes.

## § predecessor fallback (rename-transition safety)

A rename is a two-sided hazard. A plugin pinned to the OLD name breaks the moment the server renames; a plugin pinned to the NEW name breaks on any connector still serving the old surface. Connectors do not all update together: the OpenAI-curated Similarweb connector is packaged separately from the direct MCP server, and a user's client may cache an older tool surface. So resolve a documented tool name to whichever of its names the LIVE list actually carries:

1. The documented (current) name is present: use it. This is the normal path and costs nothing.
2. The documented name is ABSENT and the name-history map in `mcp-tool-catalog-v1` Appendix C lists a retired predecessor whose successor is this tool, AND that predecessor IS present in the live list: call the PREDECESSOR, and treat the capability as PRESENT. Add one Caveats line: "this connector still exposes `<old-name>`; using it. Your Similarweb connector may be a release behind." Never abort, never drop the section.
3. Neither name is present: this is a true absence; fall through to the Absent outcome.

Two hard limits. Only entries with a REAL successor in Appendix C are eligible: an entry mapped to `none` (currently `get-websites-referrals-agg`) was retired outright, its data moved elsewhere, and calling it is never a substitute. And this fallback only covers renames that preserved the request and response contract, which is what Appendix C records; if a predecessor returns a shape the recipe cannot read, treat it as absent rather than rendering a wrong number.

This is a transition affordance, not a permanent dual-target design. Retire a predecessor from Appendix C once no supported connector serves it.

## Evidence rule (tri-state: present / absent / unknown)

- **Qualifying enumeration evidence** is a harness-provided artifact in the CURRENT session that lists the Similarweb server's tools as a closed list under one server prefix (on Claude Code: the session-start deferred-tools attachment, the same source `mcp-tool-catalog-v1` used). Qualification requires a sentinel quorum: at least 3 of these 4 unqualified names present in the artifact: `get-websites-website-rank`, `get-keywords-overview`, `get-brands-search`, `get-lead-enrichment-website`. Quorum failure, zero matching servers, or two-plus matching servers means presence is UNKNOWN (never absent) and no fingerprint is written.
- **Discovery is asymmetric.** A successfully loaded tool schema (e.g. via the platform's tool-search mechanism) proves PRESENCE. A discovery miss proves NOTHING. Prior-session memory, `capabilities.json`, and the sw-foundation-core catalog are never presence evidence in either direction.
- **Canonical names.** Live names arrive platform-qualified (`mcp__similarweb__get-...`, or a client-specific id form). Match and store the UNQUALIFIED name (the substring after the last `__`), scoped to the one server that passed the quorum.

## Ordering

The presence pre-filter runs at planning time, BEFORE the capability-map read and BEFORE the smoke probe, consuming zero MCP calls. The claims filter (§ capability-gating) then quantifies over PRESENT tools only. (The sw-router Step 0 trivial path is exempt by design: it never runs a pre-filter; its only presence behavior is the call-time rule below.)

## Outcomes

- **Present**: plan normally.
- **Renamed-predecessor present** (the documented name is absent BUT its retired predecessor is present, per § predecessor fallback below): call the predecessor and plan normally. This is NOT an absence.
- **Absent** (qualifying evidence positively omits the name, AND the predecessor fallback found nothing): the outcome inherits the recipe's documented DENIAL outcome for that same tool (degrade, pivot offer, ask-user, abort; pinned per recipe in the smoke catalog reference and mirrored in each recipe's Step 2 parameter form), differing only in: zero calls, no denial-confirmation probe, no retry, Pattern 7 wording ("not exposed on this connector"), and persistence to `tools_absent` (capability map schema) instead of `tools_inaccessible`. Abort only where denial would abort.
- **Unknown** (no qualifying evidence): skip the pre-filter entirely and proceed optimistically; call-time detection below is the only absence detector. Cached `tools_absent` entries may advisorily skip OPTIONAL tools, but NEVER abort or skip a REQUIRED tool from cache.

## Smoke retarget ladder

When the recipe's documented smoke tool is absent: promote the recipe's documented secondary-probe tool to smoke; if that is also absent, smoke the first PRESENT REQUIRED tool; when no REQUIRED tool is present, abort at planning time with zero calls (aggregate insufficiency below). The retarget preserves the claims-probe purpose of smoke-first; never skip the smoke because the documented tool is absent. A retargeted smoke dispatches with the recipe's planned call params for the tool it retargets to (its call-plan row form), not a minimal probe shape, so a 200 is reusable as that planned call.

## Call-time detection (message-gated per `unknown-tool-error-shape`)

A failed call whose error carries "No such tool available" (client-level) or "Unknown tool" (server-level, the advertised-but-not-callable case) is absence-equivalent for THIS RUN:

- Record `absent_this_run[tool]`; skip all remaining calls to that tool this turn, all domains.
- Collapse sibling failures from the same parallel batch into ONE consolidated caveat line ("Not exposed on this connector: tool-1, tool-2"), mirroring the country-gap consolidation rule.
- Render every charged row already received; never discard data.
- Zero retries, no denial-confirmation probe; evaluated BEFORE the country-gap check (disjoint envelopes: a client-level error carries no server envelope).
- "Input validation error" is NOT absence: the tool exists and the call's arguments are wrong; fix the call (Pattern 2 territory; recorded nowhere).
- The advertised-but-not-callable case stays in-run only; never persist it to `tools_absent` (the live list contains the name, so a stamped absence entry would contradict the quarantine reader).
- On platforms whose error wording is not yet grounded (per `unknown-tool-error-shape-other-platforms`), do NOT claim absence from a failed call; render the hedged wording "could not reach that tool in this session" and handle per § error-rendering Pattern 2.

## Aggregate insufficiency

When fewer than 2 of the recipe's REQUIRED tools are both present and accessible (absences and 403s counted together), escalate per § error-rendering Pattern 5 semantics with a caveat naming BOTH causes, instead of shipping a multi-section-dropped report that reads like a verdict. Once a headline insight has rendered this run, subsequent REQUIRED-tool failures follow sw-foundation-render § insight-first delivery's partial-failure clause instead of escalating here; pre-headline insufficiency escalates unchanged.

## Per-platform evidence classes (client-scoped; rows fill in as platforms are observed)

| Platform | Qualifying closed-list artifact | Status |
|----------|--------------------------------|--------|
| Claude Code | Session-start deferred-tools attachment | Grounded 2026-06-11, re-grounded 2026-08-06 |
| Cowork | Not yet observed | Treat presence as unknown |
| Codex | Not yet observed | Treat presence as unknown |
| Cursor | Not yet observed | Treat presence as unknown |
| Claude.ai | Recipes ship without foundations; the recipes' inline restatement plus call-time detection carry the discipline | Treat presence as unknown |
