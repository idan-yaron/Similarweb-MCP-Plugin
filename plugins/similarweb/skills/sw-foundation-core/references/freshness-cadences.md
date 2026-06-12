# Freshness cadences (sw-foundation-core reference)

Cadences observed in production (subject to drift; re-grounded each release). `meta.last_updated` on each response remains the source of truth.

| Bucket | Approximate cadence | Example tools |
|--------|---------------------|---------------|
| Near-real-time | Updated within the last 24 hours | `get-apps-*` active users, downloads (Apps module only; absent from the grounded connector's tool list 2026-06-11) |
| Monthly | Updated at month boundary | `get-websites-traffic-and-engagement`, `get-brands-sales-performance-agg`, `get-categories-performance-agg` [^cat-perf-window] |

[^cat-perf-window]: `get-categories-performance-agg` rolls its `meta.last_updated` monthly but its data window defaults to a 3-year aggregate (`2023-04-01` through last-completed-month), NOT a rolling 30-day window. Pass explicit `start_date` / `end_date` to override.
