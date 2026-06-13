# § citation block, full compression rules and examples (sw-foundation-render reference)

Every recipe ends its output with a single-line Sources rollup. When intent classifies as `handoff`, the Handoff JSON appendix follows; otherwise the Sources line is the last element.

**Token compression rules (apply across every recipe output):**

- **Header line.** ONE italic context line: `*{domain} | {country} | {window} | last_updated {date}*`. Drop duplicate parentheticals from every subsequent section header.
- **Executive read.** Numbers-LIGHT. Lead with a verdict label (MAJOR / MATERIAL / NOISE / CONCENTRATED / SAME POND / etc.) + ONE most-important finding. Max 3 sentences. Do NOT recap numbers from tables below.
- **Sources.** SINGLE LINE per-tool rollup (see part 1). No per-call table.
- **Caveats.** One bullet per real caveat (clamped windows, access denials, structural-zero rollups, brand absence, fallback modes). Drop duplicated context (window, country) the header already states. Drop "opt-in flag X not supplied" promotional lines: users see opt-in flags via `argument-hint` completion. Caveats are not for advertising features.
- **Strategic insights (DEFEND / EXPOSE / PLAY).** 3 bullets, ~25 words each, `(confidence: HIGH | MEDIUM | LOW)` at end.
- **NEXT MOVES.** 2 backtick-quoted natural-language questions, one-sentence rationale max each. See the conversational-tone rule below. Do NOT emit slash-commands or `--flag` syntax in NEXT MOVES.

**1. Sources (single line, NOT a table, NOT collapsible).** Format:

`**Sources:** <total> data credits across <N> calls (<per-tool-rollup>).<optional-status-suffix>`

- `<total>` = sum of `data_credits` per call. Read each response's `meta.data_credits_charged` (the live MCP field), falling back to the legacy `meta.sw_coins` for older server deploys. When a call carries NEITHER field, treat that call as unknown (not 0): sum the known calls and append ` (<K> call(s) of unknown cost)` to the total, so a missing field never silently renders as free. When every call's cost is known, emit the plain total even if it is 0. The rename to "data credits" / `data_credits` happens at render/serialization time; grounded in `cheap-probe-tool-per-category` (field rename observed 2026-06).
- `<N>` = total call count.
- `<per-tool-rollup>` = comma-separated `<count> <tool-suffix>` pairs. Drop the `get-` / `get-websites-` / `get-keywords-` / `get-categories-` / `get-apps-` / `get-brands-` / `get-traffic-` prefix and the `-agg` suffix (e.g., `4 rank`, `2 traffic-and-engagement`). Sort by descending count then alphabetical.
- `<optional-status-suffix>` = appended ONLY when something interesting happened. On FULL success (every call 2xx on first attempt, no retries) the line ENDS after the per-tool-rollup's closing period. No "All 200" noise.
  - Failure: ` <failed-count> failed: <tool-1>, <tool-2>.`
  - Retry-and-success: ` <retried-count> retried after rate-limit.` (or `... after transient error.` for non-429).
  - Both: failures first, then retries.
- If costs varied surprisingly within a tool group (e.g., one rank call ran the 36-month series at ~74 data credits), append one optional `*Note:* ...` line below.

Examples (full success / failure / retry):

```
**Sources:** 158 data credits across 12 calls (4 rank, 2 traffic-and-engagement, 2 channels, 1 similar-sites, 1 audience-overlap, 2 ppc-spend).
**Sources:** 84 data credits across 8 calls (2 rank, 2 traffic-and-engagement, 2 channels, 2 ppc-spend). 1 failed: get-websites-audience-overlap-agg.
**Sources:** ... 1 retried after rate-limit.
```

Per-call audit trail NOT pre-rendered; the AI client logs each call.

**2. Handoff JSON appendix.** Only when intent classifies as `handoff` (CSV in cwd that drove the input, downstream chaining detected, or explicit `--out json`). Format per § handoff-json-schema. The full per-call list ships in the handoff `sources` array. When intent is NOT `handoff`, the Sources line is the LAST element of the recipe output.

**Conversational tone, NEXT MOVES and recommendations are natural-language questions, NOT slash-commands or flags.** Users type free-form; the router auto-dispatches. All NEXT MOVES, Caveat unblock-suggestions, and "you could also" hints MUST be the QUESTION the user might ask. Flags live in `argument-hint` for users who want them; rendered output never promotes flag syntax.

- BAD: `/sw-channel-mix adidas.com --window 90d --vs-period previous-quarter`. GOOD: `"How did adidas's channel mix shift over the last quarter?"` Confirms whether the surge is sustained or a campaign blip.
- BAD: Pass `--with-rank-delta` for a 12-month YoY view. GOOD: (omit; the user asks for YoY if they want it.)
- BAD: Add `--campaign-id <uuid>` to lift from proxy to direct. GOOD: If you have an AI Tracker campaign UUID, share it and I'll lift this to direct measurement.
- BAD: Use `--country ww` for global. GOOD: I defaulted to US. Ask if you want a global view.

Composing a NEXT MOVES bullet: derive from data findings in the render. Phrase as the question the user might ask in chat. Reference specific domains, metrics, time windows, brands, or keywords from the current run. Each bullet: backtick-quoted question first, then ONE sentence on "why this next." 2 bullets max.
