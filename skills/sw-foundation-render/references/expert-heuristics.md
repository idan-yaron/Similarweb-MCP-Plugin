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

## Sample composition, coverage and concentration (bounded-call ladder)

Every bounded call returns a SAMPLE. Two free checks decide whether that sample can carry the claim, and they catch opposite failures, so run both before reporting on any ranked-share list.

**Coverage.** When rows carry a share normalized against the entity total (`get-ai-traffic-landing-pages-agg` is the grounded case, per `ai-landing-pages-composition`), `sum(returned shares)` IS the fraction of the whole you actually saw. It costs nothing. State it whenever it is computable, and NEVER present a bounded sample as the whole.

**Concentration.** `max(returned share)`, and the same by host, says whether one row or one surface is the story.

**Operating thresholds.** These are CHOSEN thresholds, not measured constants, and they are stated here so recipes do not invent their own:

| Signal | Threshold | Response |
|---|---|---|
| Coverage below 0.50 | the sample is a minority of the entity | widen ONCE, or caveat the section as a partial view and never quote a rank as if complete |
| One URL or host above 0.25 of the entity total | one surface dominates | inspect composition BEFORE reporting; the headline is about that surface, not the category |
| Both clean | proceed | report normally, still stating coverage |

**Widen ONCE, then stop.** Diminishing returns are real: on a concentrated domain a 5x limit increase moved coverage 77.9% to 82.2%. A second widening is almost never worth its credits, and the payload budget still binds the turn.

**Non-marketing surfaces are not performance.** Rows whose host or path indicates identity (`/auth/`, `/oauth`, `signin`, `iforgot`, `idmsa`, `account.`, `appstoreconnect`, a `/login` path), support, developer, or careers are real traffic and real findings, but they are NOT answer-engine or marketing content performance. Report them as a separate line, never inside a content ranking. Whether they dominate is a DOMAIN property: one grounded domain showed 8 of its top 10 rows as identity while a control domain at the identical shape showed none, so this is a detector applied to returned rows and never an assumption.

This ladder is the defined trigger that makes tight default bounds safe: cheap by default, spend only on a signal.
