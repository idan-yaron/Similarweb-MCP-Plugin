# Apps-shaped queries (sw-foundation-core catalog reference)

The apps surface is module-gated: plans without the Apps module do not expose these tools AT ALL (absent from the tool list rather than returning 403). On the grounded connector (2026-06-11) `get-apps-details` was the ONLY `get-apps-*` tool exposed; the remaining rows are full-Apps-module names from the 2026-05-16 enumeration. Resolve presence per sw-foundation-core § tool-surface presence before planning any apps call; absent means module_not_exposed, zero calls.

| Intent | Tool | Key params |
|--------|------|------------|
| App metadata | `get-apps-details` | store (required, live-grounded 2026-06-11), plus the app identifier per the live schema |
| Find an app | `get-apps-search` | term |
| App downloads | `get-apps-downloads` | app_id, country, window |
| App active users | `get-apps-active-users` | app_id, country, window |
| App rankings | `get-apps-ranks` | app_id, country, category |
| App retention | `get-apps-retention` | app_id, country |
| App audience | `get-apps-audience-demographics` | app_id, country |
