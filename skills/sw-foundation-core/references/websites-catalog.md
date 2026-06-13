# Websites domain-shaped queries (sw-foundation-core catalog reference)

| Intent | Tool | Key params | Notes |
|--------|------|------------|-------|
| Rank a domain | `get-websites-website-rank` | domain, country | Cheap. Use as a smoke test. Response has `country_rank` + `category_rank` only; NO `global_rank` field. For global rank, pass `country: "ww"` and use the returned `country_rank` (see `website-rank-no-global-field`). `web_source` constraint: `total` only. |
| Traffic + engagement of one domain | `get-websites-traffic-and-engagement` | domain, country, start_date, end_date | Default window: last 90 days. |
| Compare N domains' traffic | `get-websites-traffic-and-engagement` (same tool, looped over each domain) | as above; one call per domain | No batched-over-entities variant exists for this tool. Loop the non-agg tool. |
| Traffic channels (absolute visits) | `get-websites-traffic-channels` | domain, country, window | Returns absolute visits by channel across the live 10-channel taxonomy: Affiliates, Direct, Display Ads, Gen AI, Mail, Organic Search, Organic Social, Paid Search, Paid Social, Referrals. Use `get-traffic-channels-share` for share-percentage view. |
| Marketing channels by source | `get-traffic-referrals-incoming` | domain | Per-domain inbound referrers (`get-segments-traffic-sources` takes a Segment ID, not a domain). |
| Similar sites | `get-websites-similar-sites-agg` | domain, limit (NO country param; the live schema does not accept one and a client-side validation rejects it) | Default limit 10. WINDOW CONSTRAINT: explicit start_date/end_date must span EXACTLY 3 months (use start_date 2_months_ago, end_date latest) or the call 400s with "must span exactly 3 month(s)"; omitting both dates is also safe. Response rows carry `affinity` (0..1 similarity); there is NO `similarity_score` field. Per `similar-sites-window-constraint`. |
| Audience overlap | `get-websites-audience-overlap-agg` | domain, domains (comma-joined string, 2-5 domains) | Returns 2^N-1 subset rows in a single batched call. |
| Demographics | `get-websites-demographics-agg` | domain, country | Age + gender breakdown. |
| Geography | `get-websites-geography-agg` | domain | Country share. |
| Conversion rates | `get-websites-conversion-rates-agg` | domain, vertical | Vertical-specific. Presence varies by account (both variants absent from the grounded connector 2026-06-11, present 2026-05-16); resolve per sw-foundation-core § tool-surface presence. |
| PPC spend | `get-websites-ppc-spend` | domain, country, window, currency | Returns estimated monthly PPC spend as a single scalar per month (no by-channel breakdown). |
| Domain keywords with enrichment (latest period) | `get-keywords-latest-agg` | domain, country, branded_type, limit | LATEST-PERIOD-ONLY (last month, or last 28 days daily). Returns the domain's top keywords WITH inline `volume` / `difficulty` / `cpc` / `cpc_low_bid` / `cpc_high_bid` / `zero_clicks` per row, plus requested `clicks` / `traffic_share` / `primary_intent` / `serp_features`. `position` returns null; `difficulty` is occasionally null; `branded_type: non_branded` is a LOOSE filter (keeps athlete/event/sponsorship proper nouns). Row-priced (~1 credit per 5-10 rows). Primary keyword+enrichment source for sw-keyword-opportunity (no per-keyword overview loop needed). Per `keywords-latest-agg-shape`. |
| SERP positions | `get-websites-serp-players-agg` | keyword, country | Domain rankings for a keyword. |
| Landing pages | `get-websites-landing-pages-agg` | domain, source_channel | Top entry points by channel. |
| Popular pages on a domain | `get-pages-popular-pages-agg` | domain | URL-level traffic. |
