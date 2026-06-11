---
name: sw-router
description: Free-form intent classifier for Similarweb-shaped prompts that did NOT invoke a specific /sw-* command. Auto-triggers on the Similarweb keyword surface (web traffic, web rank, traffic and engagement, channel mix, audience overlap, market size, AEO, similar sites, PPC spend, keywords, app downloads, brand sales, category performance, plus any specific Similarweb MCP tool name). Classifies the prompt against the 7 user-invocable recipes (sw-competitive-teardown, sw-audience-overlap, sw-channel-mix, sw-market-size, sw-aeo-audit, sw-page-mix, sw-keyword-opportunity) and either dispatches to the best match (citing the routing decision in ONE line), asks ONE crisp clarifier with 2-3 explicit options when multiple recipes fit, or plans a direct 1-3 tool MCP sequence when no recipe fits. Never dispatches to itself. Never makes silent routing decisions. Never asks open-ended questions.
user-invocable: false
---
# sw-router

**Inherits:**
- sw-foundation-core: § capability-gating
- sw-foundation-data: § country-normalization, § window-resolution
- sw-foundation-render: § citation block, § error-rendering

Free-form intent classifier for Similarweb-shaped prompts. Pure LLM-discretion routing. The router itself emits no section blocks, no handoff JSON, and (except in Branch C) makes no MCP calls; the dispatched recipe does that work.

## Hard rules (NEVER violate)

- NEVER dispatch to sw-router itself (loop guard).
- NEVER dispatch a recipe silently; cite the routing decision in ONE line first.
- NEVER ask open-ended clarification questions; always 2-3 explicit numbered options with one default marked `(DEFAULT)`.
- NEVER call MCP tools directly except in the no-recipe-fit fallback (Branch C, cap at 3 calls).
- NEVER include user-identifying info from training data; only what is in the prompt or in the MCP responses.
- NEVER trigger when the prompt is itself an explicit `/sw-*` command; the user invoked that recipe directly, so yield to it.
- NEVER invoke a recipe as a slash command (neither `/sw-<recipe>` nor a plugin-qualified form like `/similarweb:sw-<recipe>`); dispatch per § Dispatch mechanics below.
- NEVER echo the dispatched recipe's full output; the recipe owns its own rendering.

## Dispatch mechanics (what dispatching a recipe means)

Dispatching means APPLYING the recipe's skill in this same conversation. It is never a slash-command invocation.

1. Invoke the recipe skill through the platform's skill mechanism (e.g. the Skill tool) using the EXACT name the platform lists for it: `sw-<recipe>`, or its plugin-qualified form (e.g. `similarweb:sw-competitive-teardown`) when the list shows it that way. No leading slash. Pass the resolved target, competitors, country, and window as the invocation arguments.
2. If no skill mechanism exists or the recipe is not listed, Read the recipe's SKILL.md from this plugin's installed skills directory (a sibling folder of this router skill) and follow it directly.
3. The `/sw-*` line rendered in a routing citation, option list, or 2-step plan is notation for the USER (it mirrors the command name a user can type themselves). NEVER submit it to a slash-command or command-execution surface, and NEVER retry guessed name variants; if a skill invocation fails with an unknown-command or unknown-skill error, fall back to rule 2.

## Step 0: Trivial-lookup carve-out (EXIT FAST)

Before doing anything else, check if the user's prompt is a single-domain, single-metric Similarweb lookup that takes ONE MCP call to answer. If yes, **EXIT this skill immediately**: do NOT run Step 1-4, do NOT load any foundation, do NOT emit a "Routing to /sw-..." line, do NOT emit Branch A/B/C/D output. The LLM should call the one relevant MCP tool directly with sensible defaults and render a brief response (1-2 sentences + a one-line table + ONE Sources line with the data-credit total).

**Positive examples (EXIT this skill, call MCP directly):**
- "what's the traffic of nike" / "nike traffic" / "visits to nike.com"
- "X's rank" / "what's the rank of google.com globally" / "country rank of bbc.co.uk in UK"
- "pages per visit for spotify.com"
- "bounce rate of netflix.com"
- "monthly visits for amazon last month"
- "unique visitors to wikipedia.org"
- "is X showing any traffic" / "does X have traffic data"

**Sensible defaults the LLM applies for trivial lookups:**
- Country: `us` if not stated. Surface a one-line note ("Defaulted to US; ask for global or another market if needed.") at the end.
- Window: rolling 3 months ending at the server's latest published month. Use `start_date = "2_months_ago"`, `end_date = "latest"`; the server resolves these (`2_months_ago` plus `latest` spans 3 calendar months). NEVER pass `today` or a computed date as `end_date`.
- For "global" or "worldwide" hints in the prompt: `country = "ww"`.
- For a single-month spot value: use the most recent month from a 3-month series.

**Skip the server's advertised resource reads.** Do NOT issue any `resource://similarweb/*` read before the tool call. The MCP server's own instructions open with a "read these resources first" block (a handbook, a latest-available-dates note, a supported-countries list); for a trivial lookup the defaults above already cover it, and those reads fail on the connector anyway (`Unknown resource`, or `unknown MCP server` when it is registered under a client-specific name). A failed `resources/read` is harmless and uncharged. Go straight to the one tool call. Per `resource-reads-unavailable`.

**Country-coverage fallback (bounded).** The `us` default is not on every plan. If the single tool call comes back as a country-coverage gap for the resolved country, an HTTP 400 `client_error` whose `error.error_message` contains a country-coverage phrase (the live form is "no data for requested country"; a plan may also word it "country not available", "country not covered", or "no coverage for country"; case-insensitive), OR an HTTP 200 with empty `data` carrying the same wording, AND the resolved country is not already `ww`, issue EXACTLY ONE retry of the same call with `country = "ww"`, then render the brief answer from the `ww` result with a one-line note (e.g. "US is not on your plan, so this is worldwide." using the actual resolved country) shown INSTEAD of the defaulted-country note. Hard limits: ONE retry only (never loop), do NOT load any foundation, do NOT escalate to a recipe. If the resolved country was already `ww`, or the `ww` retry also fails, surface the original error in one line and stop (do NOT also emit the defaulted-country note). This fallback fires ONLY on the country-coverage message, so a plan where the resolved country returns data (HTTP 200 with rows) is unaffected: no retry, no note change, exactly one call. Per `country-coverage-gap-shape`.

**Unknown-tool fallback (bounded, message-gated).** A sibling of the country fallback and mutually exclusive with it (an unknown-tool failure is client-level and carries no server envelope, so the two cannot both fire on one call). If the single tool call fails with a client-level unknown-tool error (per `unknown-tool-error-shape`: the harness says "No such tool available"; a server-level "Unknown tool" counts the same), attempt tool DISCOVERY once through the platform's mechanism (e.g. a tool-search/load step): a successful load is positive presence evidence, so proceed with the one call. A discovery miss proves nothing: render ONE hedged line ("I could not reach that tool in this session.") and stop. Assert "not exposed on this connector" ONLY when a qualifying live enumeration (the session's own closed tool list for the Similarweb server) positively omits the name: then render ONE line ("`<tool>` is not exposed on this connector; this can be a connector tool setting in your AI client or a plan module.") and stop. Hard limits: zero retries of the failed call, no foundation load, no recipe escalation, never retry guessed name variants. An "Input validation error" is NOT this fallback: the tool exists and the arguments are wrong; fix the arguments and re-issue once.

**Render target for trivial lookups (NO foundation needed):**
- ONE intro sentence ("Nike.com had about 109M visits worldwide in April 2026.").
- ONE table row OR one-line breakdown.
- ONE Sources line: `**Sources:** <total> data credits across <N> calls (<rollup>).`
- That is it. No Executive read, no Caveats unless something failed, no NEXT MOVES, no slash-command hints.

**Multi-domain single-metric carve-out (EXIT this skill, loop one tool).** A prompt naming 2-3 domains and EXACTLY ONE metric, with NO competitive verb ("vs", "compare", "against", "stack up", "head to head") and no second analytical concern (e.g. "traffic of nike and adidas", "visits for nike.com, adidas.com and puma.com"), is still trivial: loop the ONE relevant MCP tool across the domains (max 3 calls) with the same defaults as above, render ONE comparison table plus ONE Sources line, and stop. Any competitive verb, any second metric, any verdict ask, or 4 or more domains routes to Step 1 (the teardown owns genuine comparisons).

**Negative examples (DO proceed to Step 1 and run the router):**
- Two or more domains WITH a competitive verb ("nike vs adidas", "compare X and Y"), or 4 or more domains in any phrasing. A 2-3 domain single-metric ask with no competitive verb exits via the carve-out above.
- Anything with "vs", "compare", "stack up against", "head to head".
- Channel breakdowns, traffic-source shifts, period-over-period deltas ("did X's paid drop", "channel mix", "traffic sources").
- Audience-side questions ("overlap", "demographics", "who else visits").
- AEO / SEO posture questions ("AEO audit", "is X in ChatGPT").
- Market sizing ("how big is the X market", "leaders in Y").
- Keyword gap / opportunity questions.
- Page-mix / content-surface questions.
- Anything mentioning multiple metrics ("traffic AND engagement", "rank AND channels").
- Anything requesting a verdict, recommendation, or strategic read ("what should I do about X").

**Decision rule.** If the prompt is one positive-example pattern AND none of the negative-example patterns fit, EXIT this skill (let the LLM call MCP directly). Otherwise, proceed to Step 1. When in doubt (the prompt is ambiguous between trivial and complex), proceed to Step 1; over-routing into a recipe wastes a few seconds, but mis-classifying a complex question as trivial costs the user analytical depth they wanted. Default to the heavier path on ties.

## Step 1: Read the user prompt

The user message is the free-form question. If the prompt is an explicit `/sw-*` command (starts with `/sw-`), do nothing and yield. Otherwise, classify against the recipe inventory in Step 2.

## Step 2: Recipe inventory

The plugin ships 7 user-invocable recipes. The sw-config and sw-setup operator skills are NOT recipes; never route to them from a free-form question.

| Recipe | When it fits | Example intents |
|--------|--------------|-----------------|
| `/sw-competitive-teardown` | Multi-tool view of one target against named (or implied) competitors. The prompt names a target and one or more competitors, OR uses "vs", "compare", "stack up against", "competitive view of". | "compare apple.com to samsung.com on traffic", "how does X stack up", "competitive view of Z", "X vs Y", "teardown of nike vs adidas" |
| `/sw-audience-overlap` | Audience-side analysis: who visits both, demographics, geography, deduplicated audience. Prompt uses "audience", "overlap", "demographics", "who else visits", "who is X's audience". | "who is apple.com's audience also visiting", "audience overlap between apple and google", "demographics of X", "who else does X's audience visit", "what's the overlap audience of X and Y" |
| `/sw-channel-mix` | Marketing channel breakdown with optional period-over-period delta. Prompt uses "traffic sources", "channel mix", "where is X's traffic from", "did paid drop", "social vs search", "channel breakdown". | "where is netflix.com's traffic coming from this quarter", "channel mix of X", "did X's paid search drop", "social vs search for X", "traffic sources for nike.com" |
| `/sw-market-size` | Category sizing on Amazon shopper data (and optional Web companion): demand, leaders, share of category. Prompt uses "market size", "how big is the X market", "who owns the X category", "demand for X", "leaders in X", "market for Y on amazon". | "how big is the cybersecurity market in the US", "market size of vegan dog food on amazon", "who owns the streaming category", "demand for noise-canceling headphones" |
| `/sw-aeo-audit` | AI engine visibility (proxy via SEO + SERP + landing pages, optional direct signal upgrade) plus traditional SEO posture. Prompt uses "AEO", "audit aeo", "is X showing up in ChatGPT / Perplexity / Gemini", "X's SEO posture", "share of voice in AI answers". | "is amazon showing up in ChatGPT answers for laptop reviews", "audit aeo for nytimes.com", "X's AEO posture", "is X in Perplexity for Y" |
| `/sw-page-mix` | URL-level and folder-level content surface for a domain. Prompt uses "top pages", "popular pages", "folder structure", "content surface", "page mix", "where does X's traffic land", "anchor pages", "concentration of pages". | "what are nike.com's top pages", "show me the content surface of bestbuy.com", "where does target.com's traffic concentrate by page", "folder-level breakdown of nytimes.com" |
| `/sw-keyword-opportunity` | Keyword gap analysis between a target and a competitor. Prompt uses "keyword gap", "what keywords does X rank for that Y doesn't", "keyword opportunity", "where can I outrank", "SEO gap analysis". | "what keywords is adidas winning that nike isn't", "keyword gap between hubspot and salesforce", "where can semrush outrank ahrefs", "SEO opportunity vs competitor" |

## Step 3: Pick a branch

Three outcomes. Pick exactly one.

### Branch A: high-confidence single match

Exactly one recipe clearly fits. Infer parameters from the prompt:

- **Target domain**: the domain mentioned in the prompt (lowercase, strip protocol / trailing slash). If no domain is given but a brand is (e.g. "apple"), pick the canonical apex (`apple.com`).
- **Competitors**: any other domains mentioned. If the prompt uses "and its competitors" or similar, pass through without explicit `--vs`; the recipe will infer.
- **Country**: explicit country mention normalized to ISO-3166-1 alpha-2 (`"United States"` → `us`). Default `us` when not stated.
- **Window**: explicit time mention (e.g. "this quarter" → `--window quarter`, "last year" → `--window 12m`). Otherwise let the recipe use its default.
- **Recipe-specific flags**: e.g. `--vs-period previous-quarter` if the prompt says "compared to last quarter", `--web-companion` if the market-size prompt mentions web traffic, `--keywords ...` if the AEO prompt lists keywords.

Cite the decision in ONE line, then dispatch per § Dispatch mechanics. When ANY parameter was inferred (not stated by the user), the routing-decision line MUST surface the inference in natural language so the user can correct it before the recipe runs. Per sw-foundation-render § citation block conversational-tone rule, the inferred-default citation is phrased as a plain sentence, NOT as a `--flag` hint. Country and window are the two inferences most likely to silently mislead non-US or non-default-window users.

- **Country inferred (not stated)**: append the default in a plain sentence, e.g. "Defaulting to country=us. Ask if you want a global view or a different market."
- **Window defaulted to non-obvious value**: cite the default in a plain sentence, e.g. "Defaulting to the last 90 days."
- Both inferences fire when both apply; cite each on its own line under the routing decision.

Examples:

```
Routing to /sw-channel-mix because the question is about traffic-source shifts for one target.
Defaulting to country=us. Ask if you want a global view or a different market.
/sw-channel-mix netflix.com --window quarter
```

```
Routing to /sw-competitive-teardown because the question compares one target against named competitors.
Defaulting to country=us. Ask if you want a global view or a different market.
Defaulting to the last 90 days.
/sw-competitive-teardown apple.com --vs samsung.com
```

The final `/sw-*` line in each example is part of the rendered citation (it shows the user the equivalent command). Execute the dispatch per § Dispatch mechanics; never submit that line as a command.

### Branch B: ambiguous (multiple recipes plausibly fit)

Two or more recipes plausibly fit, OR the prompt is too short / vague to pin one (e.g. "give me an analysis of apple", "what's happening with X"). Ask ONE crisp clarifier with 2-3 explicit numbered options. Mark one as `(DEFAULT)`.

**Competitor naming rule.** For options that name a recipe taking competitors (`/sw-competitive-teardown` or `/sw-audience-overlap`), do NOT suggest specific competitor names from training-data priors. Render the option with empty `--vs` / `--against` slots and add a one-line note that the recipe will auto-discover competitors. Naming competitors from training is a hallucination footgun; the recipe grounds the discovery in `get-websites-similar-sites-agg`.

```
Two angles fit here:
[1] /sw-competitive-teardown apple.com  (DEFAULT)
[2] /sw-audience-overlap apple.com

Recipe will discover competitors via get-websites-similar-sites-agg if you don't supply --vs/--against. Or pass them explicitly.

Pick 1 or 2.
```

Wait for user input. Then dispatch the picked recipe per § Dispatch mechanics.

### Branch C: no recipe fits

The question is Similarweb-shaped (e.g. "which subdomains carry bbc.co.uk's traffic", "enrich this list of domains", "is X in our category leaderboard") but none of the 7 recipes is a clean match. A single-domain single-metric lookup (e.g. a bare rank question) belongs to Step 0, NOT here; Branch C is for non-recipe questions that still need 1-3 planned calls. Plan a direct MCP call sequence (1-3 tools maximum) and execute it. Render the result per sw-foundation-render § citation block (Executive read + tool output sections + Sources line as the last element).

Branch C operates LAZILY per sw-foundation-core § capability-gating (no upfront probe required). Try to read `~/.similarweb-plugin/capabilities.json` if present; proceed regardless. Per-call access denial is handled inline via § error-rendering pattern 3 and appended to `tools_inaccessible` at the end of the run.

Cite the decision in ONE line, then list the planned calls:

```
No specific recipe fits this question. Running a direct MCP plan:
  - get-website-content-subdomains-agg(domain="bbc.co.uk", start_date="2_months_ago", end_date="latest")
```

Then execute. If a planned tool turns out inaccessible (403) at runtime, drop it and note the skip in the Caveats block; if it fails with a client-level unknown-tool error (per `unknown-tool-error-shape`), treat it as not exposed on this connector: drop it with the "not exposed on this connector" caveat wording, zero retries, never retry guessed name variants. Do not exceed 3 calls for a typical direct-MCP question (the lead/contact enrichment carve-out below is the one exception, and it caps cost a different way). When the plan includes `get-websites-website-rank`, bound it to a known-safe window per sw-foundation-data § window-resolution (`start_date = "2_months_ago"`, `end_date = "latest"`); ~2-4 data credits vs ~74 for the default 36-month series. For "global rank" questions, pass `country: "ww"` and use the returned `country_rank` field (there is NO `global_rank` field per `website-rank-no-global-field`); for in-country rank, pass the ISO-2 country.

**Stop broadening once the answer is settled.** Branch C is a SHORT fallback, not an open-ended investigation. The moment a call returns the answer OR clearly establishes it is "not found", STOP and report what you have (including "not found"); note any early stop in Caveats. NEVER keep trying new domains, name variants, or filters hoping a later call lands. That broaden-and-retry loop (the failure that ran ~9 calls on a single lookup) is exactly what this guards against.

**Lead/contact enrichment cost discipline.** When a Branch C plan is a person or company lookup (any of `post-contact-enrichment-contacts`, `post-contact-search-contacts`, `get-lead-enrichment-company`, `get-lead-enrichment-website`):
- The contact tools (`post-contact-*`) are the free, primary path; the company and website lead-enrichment tools are the metered, expensive calls. This is the one Branch C case where more than 3 calls is acceptable, BECAUSE the extra calls are free contact lookups, NOT because broadening is encouraged: use the free contact tools to settle found-or-not-found, then stop.
- Issue AT MOST ONE paid enrichment call total (`get-lead-enrichment-company` OR `get-lead-enrichment-website`, never both). NEVER re-enrich the same entity through a sibling domain: a subdomain or country domain (e.g. `at.nestle.com`, `nestle.at`) usually resolves to the same parent-company record as the apex (`nestle.com`), so a second enrichment just re-buys the same data, often with less of it. Once you have a company row, stop.
- On a PERSON lookup that returns no contact row, the honest answer is "no contact profile found." NEVER silently spend the paid enrichment on unrequested company context as a consolation. Report the empty contact result, then OFFER company context as a follow-up the user can ask for ("Want me to pull Similarweb's company profile for nestle.com?"). Spend the paid call only if the user actually asked for company data.

### Branch D: chained 2-recipe plan

The question requires TWO recipes chained because it mixes two distinct analytical concerns that neither recipe alone addresses cleanly. Detection signals:

- Two distinct analytical concerns separated by "AND" / "also" / "plus" / "and then" / a comma-and-conjunction in the user prompt.
- One question mentioning multiple data dimensions (competitive + AEO; market sizing + leader content; channel mix + keyword gap; audience overlap + content surface; rank trend + keyword opportunity).
- A single domain plus two distinct verbs from different recipe surfaces ("compare X and Y AND check their AI answer presence").

Cite the routing rationale in ONE line BEFORE the 2-step plan (e.g., "Routing as a 2-step plan because the question mixes competitive view + AEO posture."), then render the 2-step plan and consent gate:

```
This question needs 2 recipes:
  1. /sw-competitive-teardown apple.com --vs samsung.com
  2. /sw-aeo-audit apple.com --keywords "laptop reviews"

Estimated: ~6 minutes, ~250 data credits. Proceed?
```

**Consent gate.** Mandatory. User responses meaning yes (case-insensitive): `yes`, `y`, `proceed`, `go`, `ok`, `do it`. Anything else (including `no`, `n`, `cancel`, `wait`, `not yet`, or a fresh prompt) = cancel.

**On consent:** dispatch Step 1 per § Dispatch mechanics, render its output. Then dispatch Step 2 the same way with sw-foundation-data § conversation-context active (Step 2's silent Step 0 conversation-context scan will reuse Step 1's rank smoke, competitor list, or window per the helper's reuse rules). Step 2's Executive read includes a "Connecting back to /sw-<recipe-1>" line if the linkage is substantive per the § conversation-context cross-reference rules.

**On cancel:** print ONE line: "Cancelled. Tell me which angle you want and I'll run that one." Stop.

**Cost estimate.** Sum the per-recipe data-credit guidance for a rough order of magnitude (NOT exact); round to the nearest 50. Each recipe's own cost notes are the source of truth; for reference: sw-competitive-teardown ~130-340 (scales with comp-set size, 2-5 domains), sw-audience-overlap ~300-900 (heaviest; deduplicated-audience and geography dominate, see its budget gates), sw-channel-mix ~140-200, sw-market-size ~90-100 (up to ~300 with traffic enrichment), sw-aeo-audit ~12-20, sw-page-mix ~120-130, sw-keyword-opportunity ~25-30. Surface the rough total in the consent prompt.

**Hard rules for Branch D:**

- NEVER chain more than 3 recipes in one plan. Cap at 3; if 4+ recipes would fit, surface "I'd want to chain 4 recipes but that's too many; pick the 2 most important angles" with the 4 numbered options.
- NEVER auto-execute without consent. The consent gate is mandatory.
- NEVER proceed to Step 2 if Step 1 fails (recipe returned partial / aborted / 4xx). Report Step 1's failure and stop. Do NOT silently swallow Step 1 errors.
- NEVER use Branch D when one recipe alone would suffice. If a single recipe's NEXT MOVES would already cover the user's second concern, route as Branch A and let the NEXT MOVES carry the chain. Branch D is for genuine compound questions, not for "show me everything".
- NEVER chain two instances of the same recipe (e.g., two /sw-competitive-teardown runs with different competitors). That's a Branch B clarification, not a Branch D chain.

**Example chains:**

- competitive view + AEO posture: `/sw-competitive-teardown` then `/sw-aeo-audit`.
- market sizing + leader content surface: `/sw-market-size` then `/sw-page-mix` for the leader.
- channel mix + keyword gap: `/sw-channel-mix` then `/sw-keyword-opportunity`.
- audience overlap + content angle: `/sw-audience-overlap` then `/sw-page-mix` for the target.

## Step 4: Execute

- Branch A: dispatch the chosen recipe per § Dispatch mechanics. The recipe handles capability gating, MCP calls, and rendering.
- Branch B: stop after the clarifier; resume on user reply.
- Branch C: run the 1-3 tool plan and render per sw-foundation-render § citation block. The router emits a Sources block citing the direct calls.
- Branch D: render the 2-step plan + consent prompt; STOP and wait. On consent, dispatch Step 1 per § Dispatch mechanics, render, dispatch Step 2 (with § conversation-context active), render. On cancel, emit the one-line cancel message and stop.

## Edge cases

- **Prompt is an explicit `/sw-*` command**: do not route; yield to the named recipe. The router should not even emit a routing line.
- **Prompt is too short / vague** ("analyze apple", "thoughts on X", "what's happening with Y"): Branch B; offer 2-3 most-plausible recipes.
- **Prompt mentions a Similarweb concept not covered by any recipe** (e.g. lead enrichment for a list of domains, app rank, brand sales): Branch C; plan a direct MCP call.
- **Prompt asks for something the MCP does not expose** (e.g. "is X profitable", "what's X's headcount", revenue): explain that Similarweb data covers traffic / SEO / audience / category / app / shopper, NOT financials or HR. Suggest the closest recipe with a caveat (e.g. "I can show you their traffic and category position with a competitive teardown; financials are out of scope.").
- **Multiple targets in the prompt, no clear lead** ("apple, samsung, google all on traffic"): Branch B; ask which one is the lead target, with the other two as `--vs` candidates.
- **Domain is malformed** (typo, missing TLD): ask one clarifier with the closest canonical apex as the default.
- **Recipe inventory drift**: if a recipe is renamed or dropped in a later phase, update the Step 2 table here. The router is the single source of truth for what the user can be routed to.
- **Tool-surface drift**: the MCP tool surface itself drifts per account and per release (90 tools on 2026-05-16, 80 on 2026-06-11 on the same connector; per `mcp-tool-catalog-v1`). A call that fails as unknown-tool is handled by the Step 0 unknown-tool fallback or the Branch C absence rule above; never trust a remembered catalog over the live list.

## Grounded assertions

This skill's behavior is live-validated against the following grounded assertions (recorded in the project's developer-side grounding ledger, which does not ship with the plugin). Build-time validation rejects unknown references.

- website-rank-no-global-field
- resource-reads-unavailable
- country-coverage-gap-shape
- window-relative-keywords
- unknown-tool-error-shape
- mcp-tool-catalog-v1
