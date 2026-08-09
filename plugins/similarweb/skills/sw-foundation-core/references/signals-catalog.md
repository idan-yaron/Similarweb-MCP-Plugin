# Buying-signals catalog: the sales-signals family (sw-foundation-core reference)

Six event-detection tools that answer "what changed at this company recently", keyed on a company rather than on a page or keyword. Read this before planning any sales-signals call.

Grounded in `sales-signals-family-shape` and `payload-measurements`.

## The family at a glance

Every tool takes `company_domain` OR `company_name` (domain wins when both are passed) and no `limit`. Five of the six charged a FLAT 10 credits per call, measured across row counts from 1 to 12 and windows from one day to two years. Neither a narrower window nor a smaller result reduces the charge, so plan on 10 credits per tool per company and choose WHICH tools to call rather than how much to ask for.

| Intent | Tool | Cadence and window behavior | Credits |
|---|---|---|---|
| Topic interest, a buying-intent proxy | `get-sales-signals-intent` | Weekly, POINT-IN-TIME. Only signals scoring 60 or above are surfaced. | 10 |
| Technology added, removed, or up for renewal | `get-sales-signals-technology` | Daily, bounded to about 730 days ending at the last update day. | 10 |
| Online revenue and transaction-volume shifts | `get-sales-signals-ecommerce` | Monthly, latest snapshot, released around the 6th of the following month. | 10 |
| Traffic growth or decline and new market entries | `get-sales-signals-traffic` | Monthly, latest snapshot, same release cadence. | 10 |
| Ad networks started or stopped | `get-sales-signals-ad-network` | Monthly snapshot over a 12-month rolling window of paid referral data. | 10 |
| Company news mentions | `get-sales-signals-news` | Near-real-time. About 8 KB at a 7-day window and 1.7 MB at the server default, so PIN THE WINDOW to at most 7 days. | not recorded |

## Three traps

**1. The intent tool accepts exactly ONE window.** Its valid range is a single day, the last intent update day. Any other window returns HTTP 400 VALIDATION_ERROR reading `"Dates not in range. Dates must be between <day> and <day>"`. The only reliably correct call passes NO dates and lets the server resolve them. Do not compute a window for this tool.

**2. An empty result is a populated row, not an empty array.** When a company has no signal in the period, the response is `data: [{"message": "no new signals were found for this company/domain during the selected timeframe"}]`. A renderer that tests `len(data)` sees one row and reports a signal that does not exist. Detect the message-only row (it carries no `domain` key) and render it as "no signals in this period", which is a real and useful answer.

**3. `Dates not in range` is NOT a country-coverage gap.** The technology tool returns that message with HTTP 400 and `category: client_error`, the same status and category the country gap uses. Only the MESSAGE distinguishes them, which is why the country-gap detection in § country-coverage is gated on its own message substrings. Route this one to the validation path: fix the window and retry.

## Rendering and privacy

These payloads name real third-party companies, products, and vendors: an ERP product as an intent topic, a JavaScript framework as a removed technology, named ad networks as partners. Two consequences.

- **Catalog rows, recipe examples, and router examples use SYNTHETIC names.** Never paste a captured signal into a shipped file.
- **A signal is an inference, not a fact about the company's plans.** Render intent as "topic interest detected", never as "this company is evaluating X" or "this company is about to buy X". The composite score is a ranking aid; do not present it as a probability.

The traffic tool reports per-channel movement including a `gen_ai_visits` channel, which is consistent with Gen AI being a first-class channel elsewhere on the surface. Its `current_metric_value` is absolute visits and its `change` is a fraction, so a 0.1835 renders as "grew about 18%", never as "grew 0.18%".
