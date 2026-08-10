# Payload budget, full call classes and reference measurements (sw-foundation-core reference)

Response SIZE is a planning axis independent of credits. This file carries the two short lists that decide behavior, plus reference measurements for choosing a bound. The inline `§ payload-budget` section in `SKILL.md` carries the invariants and the classes; this file is what you Read when planning a call to a tool you have not bounded before.

Grounded in `payload-measurements`, `harness-oversized-output-buffering`, and `demand-trends-aggregation-semantics`.

## Why bytes need their own axis

Credits and bytes are independent, and the most dangerous call on this surface charges zero. `get-user-segments-describe` is uncharged and returned 23.9 MB on a real account, which is not an error the plugin can handle: a context overflow has no envelope, no retry, and no turn left in which to apply a skip rule. Every other gating axis (absence, a 403 denial, a country gap) hands back a response that a recipe can route. This one does not, so it must be prevented at planning time rather than handled at render time.

The corollary that catches people: **a tool with no `limit` parameter is not therefore small.** Both never-inline tools below lack a working `limit`, and `get-demand-search-trends-keywords-aggregated` has none either yet returned 77 KB for zero credits. Find the growth term (row count, date window, keyword count behind a topic seed, an explicit flag, a nested field) and bound THAT.

## Scope: bytes only

Everything below is about response SIZE. It says nothing about whether a call should be made, and it never makes a side-effectful tool callable: `post-emails-outreach` and `post-contacts-bulk` are governed by the never-auto-invoke Hard rule in `SKILL.md`, which no class here overrides. A tool can be tiny and still be the wrong thing to do.

## The three call classes (read-only tools)

### Never inline

No parameter brings these under budget, so they are not called. There is no buffered-read escape: an MCP result reaches the model before any script can touch it, so the only lever is the request.

| Tool | Why no bound helps | Observed |
|---|---|---|
| `get-user-segments-describe` | `length` and `chars` are accepted and INERT. Passing `length: 1` and `length: 5, chars: 2000` both returned the identical payload. Growth term is segment count times covered-country count | 23.9 MB, uncharged |
| `get-gen-ai-campaigns` | Its only bound is a `campaign_id` obtainable solely from its own bare listing, so discovery costs the thing the bound was meant to avoid | 1.9 MB bare, about 1.1 KB with an id |

`get-gen-ai-campaigns` is not called by any shipped skill. A campaign id is a user-supplied or setup-time input, never a runtime discovery step. If a user supplies an id, the bounded call is fine.

### Safe unbounded

These accept no bound parameter and have been measured small. Calling them without a bound is correct because there is nothing to pass.

| Tool | Observed | Credits |
|---|---|---|
| `get-industry-demographics-describe`, `get-industry-unique-users-describe` | about 17 KB each, near-identical content; fetch one and reuse rather than both | 0 |

### Bound required

**Every other live tool, measured or not.** Pass an explicit `limit`, `metrics` list, date window, or id filter, and never rely on server defaults.

The default for a tool nobody has measured is bound-required, not silence. Requiring a bound asserts nothing about the tool's safety and costs nothing; staying silent is a safety assertion by omission, and that inference is exactly what shipped an unconditional 23.9 MB call. Roughly a hundred of the live tools have no payload measurement, and all of them are bound-required.

Two tools in this class are safe at their DEFAULT and dangerous only under an explicit parameter, which inverts the usual reading:

- **`get-custom-industries-describe`**: 60 bytes at its server default, 5.0 MB with `include_shared: true`. The bound is "do not pass the flag".
- **`get-sales-signals-news`**: about 8 KB at a 7-day window, 1.7 MB at the server default window. The bound is "pin the window to at most 7 days". Do not attempt to buffer the response instead; a skill cannot buffer what has already entered its context.
- **`get-ai-traffic-overview` and `get-ai-traffic-overview-aggregated`**: RECLASSIFIED here from safe-unbounded. The schema accepts `start_date`, `end_date`, and `metrics`, and the SERVER DEFAULT window is about three years, so calling it "as-is" asks for the widest window it offers. It returned 128 rows across 15 LLM sources on one domain with real AI traffic, uncharged. The bound is "pin the window". An earlier about-1-KB reading came from a domain or account with almost no AI data and did not transfer. Grounded in `ai-traffic-overview-window-default`.
- **`get-demand-search-trends-keywords-aggregated`**: about 77 KB and roughly 999 keywords on ONE common topic over two months, and it charges 0. It has no `limit` at all, so the bound is "narrow the topic, and shorten the window". A broad seed has no safe call, and the free charge is not a signal of a small response.

## The inline budget

About 50 KB per response, and it is a **conservative proxy, not a measured threshold**. The bracketing observation was uncontrolled: a prose-heavy payload of about 45 KB was inlined by the client while a structured-JSON payload of 53.4 KB was not, and those differ substantially in tokens per byte, so the real cut-off may be counted in tokens or characters. The exact number is not load-bearing, because every bound-accepting tool carries a bound regardless. Use the budget to decide how tight a bound should be, not whether to pass one.

Note that some clients replace an oversized result with a size notice and a preview rather than the payload, so a 200 does not guarantee the data is in front of you. See sw-foundation-render `§ error-rendering` Pattern 8 for how that renders.

**An oversized result also hides what it cost.** The notice replaces the envelope, so the charge never reaches the model inline and the call reads as free. It is not: an unbounded call of this shape has been observed costing a four-figure credit total, invisibly. This is the strongest practical argument for the bound, ahead of the context budget: a payload you cannot see is one you paid for anyway. Pattern 8 permits a metadata-only extract to recover the figure where the client exposes the buffered file.

## Reference measurements for choosing a bound

Account-scoped, observed 2026-08-07 unless noted. **Every figure names the parameter shape it was measured at**, because a bare number reads as a property of the tool and is usually a property of one call. Sizes move with account data volume; the growth term is what transfers between accounts.

| Tool | Shape measured | Payload | Credits |
|---|---|---|---|
| `get-websites-geography-agg` | server default (limit 100, 6 metrics) | about 28 KB | 700 |
| `get-websites-geography-agg` | limit 10, 2 metrics | small | 30 |
| `get-websites-audience-interests-agg` | server default (limit 100) | about 22 KB | 500 |
| `get-website-content-technologies-agg` | server default (limit 100) | about 45 KB | 10 |
| `get-website-analysis-traffic-channels-share` | limit 100 | about 12 KB | 200 |
| `get-ai-traffic-overview` | no dates (server default, about 3 years) | 128 rows, not byte-measured | 0 |
| `get-retail-cross-analysis-describe` | server default | 53.4 KB | 0 |
| `get-retail-cross-analysis-describe` | limit 1 | 1.3 KB | 0 |
| `get-gen-ai-campaign-analysis-prompts` | limit 1, `metrics` omitting `response` | 1.2 KB | not recorded |
| `get-gen-ai-campaign-analysis-prompts` | server defaults | 453 KB | not recorded |
| `get-ai-traffic-landing-pages-agg` | limit 2 | 1 KB | 1 per row |
| `post-contact-search-contacts` | limit 1 | 1.9 KB | not recorded |
| `post-contact-search-contacts` | limit 100 | 69 KB | not recorded |
| `get-demand-search-trends-keywords-aggregated` | one common topic, 2 months (no limit param exists) | 77 KB | 0 |
| `get-retail-cross-performance-categories-performance` | limit 20, default metrics | small | 60 |
| `get-websites-demographics` | 1 month, 8 metrics | small | 8 |
| `get-websites-serp-players` | limit 25, 1 month | small | 1 |

**`post-contact-search-contacts` and `post-contact-enrichment-contacts` return personal data about real people.** The sizes above are per-row references for choosing a bound, not an invitation to widen a search. Both bounds are mandatory: an explicit `limit` (the server defaults it to 0 and then rejects 0, so omitting it always fails) AND `output_fields` restricted to the columns the answer actually renders. `output_fields` has NO server-side forcing function, so nothing fails when it is omitted; it just returns every field the server holds. Returned contact PII is never persisted anywhere outside the current answer: not the capability map, not a handoff, not a file, not a rendered artifact. Render only the fields the user asked for and drop the rest.

`get-websites-geography-agg` is the worked example for why shapes matter: it is priced on rows AND metrics at once, fitting rows times (metrics + 1) across the two shapes above, so widening the `metrics` list raises the charge proportionally. Grounded in `geography-agg-cost-shape`.

**"Server default" is not "unbounded".** Several tools echo `limit: 100` in `meta.query` when no limit is passed, so a server-default measurement is a bounded measurement at a bound you did not choose. Read `meta.query` to see what the server actually applied.

## Adding a tool to these lists

A tool joins **never inline** only when no parameter brings it under budget, and the entry must say which parameters were tried and what they did. A tool joins **safe unbounded** only when it accepts no bound parameter AND has a recorded measurement. Everything else stays bound-required, which needs no entry at all. When in doubt, leave it out: the default is already the safe answer, and a wrong entry on either list is worse than no entry.

## Machine-readable lists

`build.py --validate` parses the four fenced blocks below and fails the build on a violation, so these are the authoritative lists and the prose above is the explanation. Keep them in sync: a name added to a human table but not to its block is unenforced, and a name in a block that no longer exists on the live surface trips the tool-name drift guard.

### List: never-inline

```
get-user-segments-describe
get-gen-ai-campaigns
```

Naming one of these in a shipped file requires citing `§ payload-budget` nearby, so a reader always meets the reason it is not called.

### List: safe-unbounded

```
get-industry-demographics-describe
get-industry-unique-users-describe
```

These are exempt from the bound requirement because they accept no bound parameter. Everything NOT on this list needs an explicit bound in a call plan, measured or not.

### List: never-auto-invoke

```
post-emails-outreach
post-contacts-bulk
```

Side-effectful. Any shipped file naming one must carry the never-auto-invoke rule, so the prohibition can never travel separately from the tool name.

### List: pii-contact

```
post-contact-search-contacts
post-contact-enrichment-contacts
```

Return personal data. Any shipped file naming one must carry the PII handling rule in the same file.
