# § derived-metric glossing, canonical gloss table (sw-foundation-render reference)

Any metric the plugin DERIVES (computes client-side, not returned verbatim by the MCP) MUST carry a plain-language gloss every place it is surfaced. A bare derived number is a usability bug: a reader who sees `Best engagement: 3.23` or `HHI: 1,101` has no idea what it means, what the unit is, or which direction is good. The raw MCP metrics (visits, bounce_rate, country_rank, revenue_share) are self-explanatory and do NOT need this; only the derived ones do.

**The derived metrics that require a gloss:**

| Metric | Formula | Unit / direction | One-line reader gloss |
|--------|---------|------------------|------------------------|
| Engagement quality score | `(1 - bounce_rate) * pages_per_visit` | unitless index, higher = stickier | "Pages per visit scaled by non-bounce share; unitless, higher = stickier. Not a %, not comparable across very different site types." |
| PPC cost per visit (CAC proxy) | `ppc_spend / visits` | USD/visit, lower = more efficient | "Paid spend divided by visits; a rough customer-acquisition-cost proxy. Comparable across domains, not across categories." |
| HHI (market concentration) | `sum(share_i^2) * 10000` over top-N | 0 to 10000, higher = more concentrated | "Herfindahl index from the top-N revenue shares; higher = more concentrated. From top-N only, so the true value is higher." |
| Share of union (audience overlap) | `overlap_unique_visitors / union_unique_users` | %, higher = more duplication | "Percent of the two domains' combined unique audience that visits both; higher = more duplicated eyeballs." |
| Persona Jaccard (interest overlap) | `intersection / union` of top interests | 0 to 1, higher = more similar | "Set-overlap of the two domains' top audience interests; 0 = no shared interests, 1 = identical." |
| Affinity (similar-sites) | server-supplied 0 to 1 score | higher = more co-visited | "How strongly the two domains share visitors, per Similarweb's similar-sites model; higher = more co-visited." |

**Where the gloss appears:**

- **Markdown.** A one-line footnote on the metric's FIRST appearance (the `$/visit is a CAC proxy ...` footnote pattern already in sw-competitive-teardown is the model). One footnote per metric per output; do not repeat it on every row.
- **Handoff JSON.** No gloss needed; the `data` schema documents the field. Glossing is a human-rendering concern only.
- Rich-tier artifact surfaces carry the gloss per the placement bullet in SKILL.md § derived-metric glossing.

**Hard rules:**
- NEVER render a derived score as a bare number with no gloss anywhere a human reads it.
- A superlative label ("Best engagement", "Reach leader", "Lowest PPC/visit") names the WINNER; it does NOT explain the METRIC. When the underlying metric is derived, the gloss is still required alongside the superlative.
- The gloss states what the number measures and its direction, NOT the winning brand (the value/label already shows the winner).
