# § expert-heuristics, full ladders (sw-foundation-render reference)

Quantified thresholds recipes cite when interpreting raw data. These are calibrated against real Similarweb behavior; do not soften without grounding. Recipes that surface a derived verdict, a confidence label, or a strategic recommendation MUST cite the relevant heuristic from this reference instead of inventing a threshold.

**Engagement profile heuristics:**
- Bounce <30% + pages/visit >5 = utility / login pattern (power-user site).
- Bounce 30-50% + duration >3min = engaged content / research site.
- Bounce >65% + duration <60s = intent mismatch (often paid landing pages or low-quality traffic).
- Bounce >65% + duration <1min = single-purpose entry.

**Channel mix red flags:**
- Direct >50% = strong brand OR bot / dark-traffic noise (sanity check).
- Paid Search >35% = margin-sensitive (cost shock will tank traffic).
- Organic Search <20% on a content-heavy site = SEO underinvestment.
- Any single channel >40% = concentration risk.

**Derived metrics (each carries a canonical reader gloss; see § derived-metric glossing):**
- Engagement quality score = `(1 - bounce_rate) * pages_per_visit`. Unitless index, higher = stickier. Reader gloss: "Pages per visit scaled by the share of visits that did not bounce; unitless, higher = stickier. Not a percentage; not comparable across very different site types."
- Cost per visit (CAC proxy) = `ppc_spend / visits`. USD per visit, lower = more efficient. Reader gloss: "Monthly paid spend divided by visits; a rough customer-acquisition-cost proxy. Comparable across domains, NOT across categories."

**Period-over-period verdict ladder (use on every delta computation):**
- `|delta_pct| < 5%` -> WITHIN NOISE (do not invent root causes; report and stop).
- `5% <= |delta_pct| < 15%` -> MATERIAL CHANGE.
- `|delta_pct| >= 15%` -> MAJOR CHANGE (high stakes).

**Audience-overlap labels (use whenever computing pairwise overlap %):**
- `overlap >= 40%` -> SAME POND (heavy duplication; buying both = paying twice for many of the same eyeballs).
- `15% <= overlap < 40%` -> ADJACENT (meaningful overlap, distinct audiences).
- `5% <= overlap < 15%` -> COMPLEMENTARY (extends reach efficiently).
- `overlap < 5%` -> DISJOINT (essentially independent audiences).

**Market concentration (HHI from top-N revenue shares):**
- `HHI < 1500` = FRAGMENTED / competitive (room to enter).
- `1500 <= HHI < 2500` = MODERATE.
- `HHI >= 2500` = CONCENTRATED (entrenched incumbents).
- HHI from top-N only is an underestimate; absolute HHI rises when the long tail is added.

**Hypothesis calibration:** when a recipe surfaces a hypothesis, label `HIGH` / `MEDIUM` / `LOW` confidence based on evidence weight. NEVER deliver an uncalibrated hypothesis.
- HIGH = simplest explanation fitting ALL the data the recipe pulled (no contradicting signal).
- MEDIUM = fits the headline signal but has at least one ambiguity / alternative not ruled out by the data in hand.
- LOW = consistent with the data but other explanations fit equally well; or signal-to-noise is poor.
- DO NOT introduce external-world speculation (algorithm-update dates, news events) unless the user supplied that context. If you must, label `UNCONFIRMED EXTERNAL HYPOTHESIS` and put it LAST.

**Refusal-as-feature:** if signal is thin (no defensible hook, no recent data, no meaningful delta), REFUSE to render the recommendation section. A generic recommendation is worse than no recommendation. Render an `INSUFFICIENT SIGNAL` block with the explicit reason (e.g., "no winning SERP positions across audited keywords; no answer-box-adjacent features on any landing page; recommend re-run after domain accumulates SERP presence"). Sources line still ships.
