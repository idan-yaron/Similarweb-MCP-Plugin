# Apps-shaped queries (sw-foundation-core catalog reference)

The apps surface is module-gated: plans without the Apps module do not expose these tools AT ALL (absent from the tool list rather than returning 403). Resolve presence per sw-foundation-core § tool-surface presence before planning any apps call; absent means module_not_exposed, zero calls.

## Active guidance

`get-apps-details` is the ONLY apps tool on the live surface as of the 2026-08-06 enumeration (113 tools). It is itself 403 claims-gated on the grounded connector, so its presence is proven by the denial: plan for a Pattern 3 "not accessible on this plan" render, not a Pattern 7 absence render.

| Intent | Tool | Key params |
|--------|------|------------|
| App metadata | `get-apps-details` | store (required, live-grounded 2026-06-11), plus the app identifier per the live schema |

Any other apps-shaped question has no live tool behind it. Do NOT plan a call to a documented-absent name below; say the app surface is not exposed on this connector (§ error-rendering Pattern 7) and offer the website-side equivalent where one exists.

## Documented-absent as of 2026-08-06

These six names come from the 2026-05-16 full-Apps-module enumeration. They were absent at the 2026-06-11 enumeration and absent again at the 2026-08-06 enumeration, that is two consecutive enumerations, and notably they did NOT return during the plus-33 tool expansion that produced the 113-tool surface. That strengthens the module-gating reading without settling it: whether the Apps module simply is not on this account or the tools were removed product-wide is still OPEN, and resolving it needs a second account carrying the Apps module. They stay documented here on purpose, per the presence-first discipline: a name the catalog has seen is a known quantity, not a typo.

| Intent | Tool | Key params (as last grounded) |
|--------|------|-------------------------------|
| Find an app | `get-apps-search` | term |
| App downloads | `get-apps-downloads` | app_id, country, window |
| App active users | `get-apps-active-users` | app_id, country, window |
| App rankings | `get-apps-ranks` | app_id, country, category |
| App retention | `get-apps-retention` | app_id, country |
| App audience | `get-apps-audience-demographics` | app_id, country |
