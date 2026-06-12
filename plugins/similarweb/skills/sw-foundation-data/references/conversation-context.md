# § conversation-context, full reuse rules (sw-foundation-data reference)

When a recipe runs in a conversation that already contains output from a prior recipe (this turn or earlier), the model SHOULD detect and reuse that output to (a) skip redundant tool calls, (b) reference prior findings in the new output, (c) tighten NEXT MOVES bullets to build on what's already known.

**Detection pattern.** Scan recent assistant turns for the standard recipe header `*<target> | <country> | <window> | last_updated <date>*` (the italic context line from § citation block). Each header tags an upstream recipe run. Also scan for the bold Sources line `**Sources:** N data credits across M calls (...)` which marks a completed recipe.

**Reuse rules:**

1. **Window and freshness.** If a prior recipe this session resolved a window for the SAME target AND country AND its `last_updated` matches today's expected publish boundary, reuse that window and `last_updated` rather than re-resolving on the current recipe's first call. Surface a single-line Caveat: "Window reused from prior /sw-<recipe> for <target>." Recipes that render rank (sw-competitive-teardown) may also reuse a prior rank value when present.

2. **Competitor set.** If a prior recipe surfaced a competitor list (similar-sites discovery in /sw-competitive-teardown, --against in /sw-audience-overlap, --vs in /sw-competitive-teardown), and the current recipe needs competitors without explicit args supplied, reuse the prior set. Surface in a Caveat: "Competitor set reused from prior /sw-<recipe>: <list>." If explicit competitors are supplied this turn, ignore the prior set.

3. **Effective end_date.** A prior recipe's resolved effective `end_date` (the server's latest published month) is target-independent; reuse it for the current recipe regardless of target, unless the user explicitly asks for a different window. Full window-plus-freshness reuse with the Caveat line still requires the SAME target and country per rule 1; this rule covers only the publish-boundary date itself.

**Cross-reference rules.** When the current recipe surfaces a finding that materially relates to a prior recipe's verdict, prepend ONE optional sentence under the Executive read:

> "Connecting back to your earlier /sw-<recipe> for <target>: <one sentence linking findings>."

OPTIONAL; include only when the linkage is substantive (a SAME POND label connecting to a channel-mix overlap; a rank shift explaining a market-size finding; an AEO recommendation linking to a content gap surfaced in /sw-page-mix). Do NOT cross-reference trivial connections. If the model is unsure whether a linkage is substantive, OMIT.

**Hard rules:**
- NEVER fabricate a prior-recipe finding. Only reference what literally appears in conversation context.
- NEVER reuse window or rank data if the prior `last_updated` is older than the current expected last-published-month boundary.
- NEVER reference a prior recipe without naming it by slash-command form (e.g., "your earlier /sw-channel-mix run for adidas.com").
- FAIL-SAFE: when in doubt, re-resolve via a fresh first call (or re-run the smoke for recipes that keep one). A redundant call is cheaper than a stale figure.
- When no prior recipe ran in this session, skip this entire helper silently. Do NOT mention it.
