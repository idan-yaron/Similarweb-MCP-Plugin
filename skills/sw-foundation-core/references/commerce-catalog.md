# Commerce catalog: the shopper and criq families (sw-foundation-core reference)

Two commerce product families live on this surface. Neither takes a Similarweb domain, and neither shares identifiers with the other. Read this before planning any call to a tool listed here.

Grounded in `commerce-surface-entity-models`, `criq-performance-cost-shape`, and `web-family-cost-shapes-2026-08`.

## Read this first: three entity models, no shared inputs

Family membership below is taken from the live tool-name enumeration in `mcp-tool-catalog-v1`. Each tool description also OPENS with a bracketed family tag, which is the fastest per-tool confirmation; the tags were read on a sample of each family rather than on all 44, so trust the tag on the tool in front of you over any grouping here.

| Tag | Primary entity | Discovery tool (uncharged) | What its numbers measure |
|---|---|---|---|
| `[shopper]` | an Amazon MARKETPLACE domain plus a numeric Amazon category id, a brand name, or an ASIN | `get-categories-search`, `get-brands-search` | on-site search inside that marketplace |
| `[criq]` | an ACCOUNT-SCOPED custom-category UUID plus a two-letter market code | `get-retail-cross-analysis-describe` | retailer views and SKU counts across retailers |
| `[web]` | a Similarweb domain, keyword, segment id, or industry category | see `references/websites-catalog.md` | web visits |

**The `domain` parameter on a shopper tool is the marketplace, NOT the analysed brand.** It accepts only `amazon.com`, `amazon.co.uk`, `amazon.it`, `amazon.fr`, `amazon.de`, `amazon.ca`. The brand under analysis is a separate `brand` parameter. Passing `nike.com` as `domain` is a category error, not a narrower query.

**Never sum shopper `clicks` with web `visits`.** They are different quantities measured on different surfaces. A brand's Amazon on-site search clicks are not a channel of its website traffic.

**Category ids and ASINs are marketplace-specific** and do not transfer between Amazon domains. criq category UUIDs are account-scoped: they come from the account's own custom categories, so no default can be shipped and none is named here.

**Same prefix, different product.** `get-keywords-performance`, `get-keywords-performance-agg`, `get-keywords-top-brands`, `get-keywords-top-brands-agg`, `get-keywords-top-products`, and `get-keywords-top-products-agg` are `[shopper]` tools about Amazon on-site search. `get-keywords-overview`, `get-keywords-seo-overview`, and `get-keywords-latest-agg` are `[web]` SEO tools and live in `references/websites-catalog.md`. The shared `get-keywords-` prefix is not a family.

## Discovery comes first, and it is free

A shopper or criq analytics call needs an identifier that only its own discovery tool can supply. Both discovery tools charged 0.

| Intent | Tool | Key params | Notes |
|---|---|---|---|
| Find an Amazon category id | `get-categories-search` | domain, search_term, limit, children_depth | Rows `{category_id, category_name, category_path, category_depth, parent_category_id, parent_category_name}`. `children_depth` above 0 multiplies the response size; leave it at the default unless the hierarchy is the question. |
| Find an Amazon brand | `get-brands-search` | domain, search_term, limit | Returns matching brands with units sold. |
| Discover criq categories, markets, and the data window | `get-retail-cross-analysis-describe` | limit, criq_category_id, name_contains | Returns `dates` (weekly window plus `fresh_data`), `custom_categories` (account data: NEVER quote a UUID, name, or description in a shipped file or a rendered answer beyond what the user asked for), and 43 `markets` codes. Pass `limit: 1` when only the window or market list is needed: it is 53.4 KB at the server default and 1.3 KB at `limit: 1`. |
| List retailer domains in a criq category | `get-retail-cross-analysis-category-domains` | category_id, market_code, limit | Weekly granularity only. |
| Check criq coverage for a domain | `get-retail-cross-analysis-domain-coverage` | category_id, market_code, limit | Presence and coverage check before a performance call. |
| Find brands inside a criq category | `get-retail-cross-analysis-brands-search` | category_id, market_code, limit | criq's own brand vocabulary; not interchangeable with shopper brand names. |

## Shopper family: Amazon on-site search

Every tool below takes the marketplace `domain` plus its own entity, supports `limit`/`offset`/`sort`/`asc`, and defaults to the last 28 days when no window is passed. Pass an explicit `limit` and an explicit window on every call. The `-agg` sibling of each name batches the same intent over several entities in one call; prefer it over looping when analysing more than one entity, per sw-foundation-data.

| Intent | Tool (and its `-agg` sibling where one exists) | Entity | Notes |
|---|---|---|---|
| Category on-site search performance over time | `get-categories-performance`, `get-categories-performance-agg` | category id | Metrics include category and brand, paid and organic clicks, and search volume. |
| Category sales and revenue | `get-categories-sales-performance`, `get-categories-sales-performance-agg` | category id | Sales-side counterpart to the clicks tools. |
| Top brands inside a category | `get-categories-top-brands`, `get-categories-top-brands-agg` | category id | The brand-discovery path when a category is the starting point. |
| Top keywords inside a category | `get-categories-top-keywords`, `get-categories-top-keywords-agg` | category id | On-site search terms, not web SEO keywords. |
| Top products inside a category | `get-categories-top-products`, `get-categories-top-products-agg` | category id | Returns ASINs usable by the product tools. |
| Brand sales and revenue | `get-brands-sales-performance`, `get-brands-sales-performance-agg` | brand plus category | |
| A brand's closest competitors | `get-brands-top-competitors`, `get-brands-top-competitors-agg` | brand plus category | Competition measured inside the marketplace category, not on the open web. |
| A brand's top on-site keywords | `get-brands-top-keywords`, `get-brands-top-keywords-agg` | brand plus category | |
| A brand's top products | `get-brands-top-products`, `get-brands-top-products-agg` | brand plus category | Wide `metrics` enum (price, revenue, units_sold, rating, reviews, best-seller rank, and more). Every added metric widens the payload; request only what the answer renders. |
| Product sales and revenue | `get-products-sales-performance`, `get-products-sales-performance-agg` | ASIN | ASIN must be exactly 10 uppercase alphanumeric characters. |
| A product's top on-site keywords | `get-products-top-keywords`, `get-products-top-keywords-agg` | ASIN | |
| One keyword's on-site performance | `get-keywords-performance`, `get-keywords-performance-agg` | keyword | FLAT 1 credit per call, window-independent across 1 and 3 months. Returns all seven metrics by default. |
| Brands ranking for a keyword | `get-keywords-top-brands`, `get-keywords-top-brands-agg` | keyword | |
| Products ranking for a keyword | `get-keywords-top-products`, `get-keywords-top-products-agg` | keyword | |
| A brand's click share within a category | `get-clicks-share`, `get-clicks-share-agg` | brand plus category | Share metrics are brand-within-category, so the denominator is the category and not the marketplace. |

## criq family: cross-retailer performance

Weekly granularity ONLY. `start_date` and `end_date` are required on the performance tools and there is no default window.

| Intent | Tool (and its `-agg` sibling) | Notes |
|---|---|---|
| Category or brand performance by retailer domain | `get-retail-cross-performance-categories-performance`, `get-retail-cross-performance-categories-performance-agg` | Rows `{date, domain, views, number_of_skus, category_views, category_number_of_skus, views_share}`. The category comparison metrics stay null unless `brand_name` is supplied. |
| Top brands in a criq category | `get-retail-cross-performance-categories-top-brands`, `get-retail-cross-performance-categories-top-brands-agg` | |
| Top products in a criq category | `get-retail-cross-performance-categories-top-products`, `get-retail-cross-performance-categories-top-products-agg` | |
| Top on-site keywords in a criq category | `get-retail-cross-oss-categories-top-keywords`, `get-retail-cross-oss-categories-top-keywords-agg` | |

**Two cost axes at once, and both must be bounded.** `get-retail-cross-performance-categories-performance` fits `credits = rows x (populated metrics + 1)` across four measured shapes: `limit` 5 with the default metric set charged 15, `limit` 10 with two metrics charged 20, and `limit` 20 with the default set charged 60. Widening `metrics` raises the charge at a fixed `limit`, and widening `limit` raises it at a fixed `metrics`. This is the same combined shape `get-websites-geography-agg` follows, so treat a single-axis assumption about any aggregation tool as unverified.

**Unrequested metrics come back as null.** The `metrics` list selects what is POPULATED and CHARGED, never what is returned, so the response shape does not tell you what was asked for.

**The server can WIDEN a window you narrowed.** A request for a single week was echoed in `meta.request` as the surrounding three weeks and charged the same. Narrowing the window is not a reliable cost lever here, and the ECHOED window rather than the requested one is what the answer describes. Read `meta.request` before labelling any criq period in a render.

## Synthetic examples only

Payloads in these families name real retailers, brands, and products. When a catalog row, a recipe, or a router example needs an illustrative call, invent the brand and category rather than pasting a captured one. The same rule applies to the account's own criq custom categories, whose names and UUIDs are account data.
