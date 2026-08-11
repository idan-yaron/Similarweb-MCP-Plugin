# § client-register, output that leaves the building (sw-foundation-render reference)

Read this when intent classifies as `client`. It changes THREE things: who the reader is, what vocabulary is allowed, and what the Sources line says. It changes nothing about what was measured, and it never relaxes a caveat.

## When `client` applies

Signals: "for the client", "goes to <company>", "hand this to", "deliverable", "content brief", "positioning doc", "landing page copy", "campaign brief", or an explicit request for a file to send onward. When in doubt use `narrative`: over-hedging an internal read costs a reader nothing, while vendor jargon in a client artifact has to be stripped by hand.

## 1. Register: assert, do not explain

An analysis explains where its numbers came from. A brief asserts. The same finding is written differently:

| Internal register | Client register |
|---|---|
| "Similarweb panel data shows organic search at 34.2% of visits (3-month window, US, 158 data credits across 12 calls)" | "Organic search carries 34.2% of visits in the US, across the three months to July 2026." |
| "Estimated from a top-25 sample covering 71% of the channel" | "Based on the top 25 sources, which account for 71% of the channel." |

What survives the translation, always: the number, the market, the window, the coverage or sample basis, and every caveat that changes how the number should be read. What goes: the vendor, the tooling, the credit economy, and the machinery of how the answer was assembled.

**A caveat is never dropped for being awkward.** If a figure needs "this is a floor, not a total", that sentence ships in both registers. Register controls VOICE, never completeness. Dropping a limitation to make a deliverable read cleanly is fabrication by omission.

## 2. Vocabulary boundary

In `client` mode these NEVER appear in rendered output:

- **The vendor and its product names.** The data source is named once, plainly, as the provenance line requires; internal product and module names are not. The denylist, explicit because an abstract rule failed live while the concrete term sat in the user's own prompt: Shopper Intelligence, Sales Intelligence, Digital Research Intelligence, Digital Marketing Intelligence, App Intelligence, Stock Intelligence, CRIQ. The list binds in any casing, spacing, or hyphenation (a lowercase hyphenated FILENAME was the leak actually observed), and it covers filenames, headings, and chart titles as well as prose. A term appearing in the user's own prompt does not license it into a deliverable; substitute a plain description of the surface. This same list ships inline in sw-foundation-core § client-output so it reaches sessions where this file never loads; keep the two lists identical when editing either.
- **Tooling.** MCP tool names, any `get-` or `post-` method name, the word endpoint, parameter names such as `limit` or `granularity`.
- **The credit economy.** "data credits", credit counts, call counts. This is our own coinage and means nothing outside the plugin.
- **Plugin surface.** Recipe names, `/sw-` commands, flag syntax, section names that are ours rather than the reader's.
- **Internal shorthand** for a metric where a plain-English name exists. Derived metrics keep their gloss per § derived-metric-glossing; they lose the internal metric name.

## 3. The Sources line becomes a provenance line

Default modes end with a rollup that counts credits and names tools. That line is the single largest vocabulary leak in the plugin's own output, and a client-readiness gate written by a real user blocklisted both halves of it.

In `client` mode replace it with a one-line provenance statement carrying, in this order: the data source, the market, the window, and the freshness date from `meta.last_updated`.

```
Source: Similarweb, US, February to July 2026. Data current to 31 July 2026.
```

Coverage or sample basis joins that line when the answer rests on a bounded sample:

```
Source: Similarweb, US, July 2026. Data current to 31 July 2026. Based on the top 25 pages, 71% of AI-referred traffic.
```

No credits, no call counts, no tool names. The internal Sources line is still correct for every other mode and is unchanged there.

## 4. Output hygiene

- **No em dashes.** Use commas, colons, parentheses, or a sentence break. This applies to rendered output in every mode; it is listed here because client artifacts are where it gets noticed.
- **No unresolved placeholders.** No `<target>`, no `X%`, no TODO.
- **No internal correction traces.** If a figure was revised during the run, ship the current figure. The revision history belongs in the internal read, not in a deliverable.
- **Unconfirmed forward-looking claims carry their basis.** Anything not yet announced or not yet measured is labelled as a working assumption where it appears, not left to read as fact.

## What this mode does NOT change

It does not change which calls run, which country or window resolves, or which caveats apply. It does not license a claim the data cannot support. A finding that is "not decidable" internally is "not decidable" in a client deliverable too, phrased for that reader.
