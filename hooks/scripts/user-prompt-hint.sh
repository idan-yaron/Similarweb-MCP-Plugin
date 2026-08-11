#!/usr/bin/env bash
set -e

# Similarweb keyword surface (case-insensitive egrep pattern), the canonical list for
# this hook's hint. Short tokens are word-anchored so paths and unrelated words
# (archaeology, aeolus) cannot fire it.
KEYWORDS_PATTERN='similarweb|web traffic|web rank|traffic-and-engagement|traffic and engagement|channel mix|audience overlap|similar sites|ppc spend|keyword opportunity|keyword gap|\baeo\b|seo audit|ai visibility|answer engine|market sizing|market size|page mix|competitive teardown|organic search share|paid search share|brand sales|market share|best sellers|top selling products|app downloads|category performance|lead enrichment|share of voice|marketing analysis|brand health|brand protection|shopper intelligence|retail shelf|get-website-analysis-traffic-channels|get-websites-audience-overlap-agg|get-websites-traffic-and-engagement|get-websites-similar-sites-agg|get-websites-website-rank|get-website-analysis-search-spend|get-keywords-overview|get-keywords-seo-overview|get-brands-sales-performance-agg|get-categories-performance-agg|get-pages-popular-pages-agg|get-website-analysis-traffic-channels-share|get-lead-enrichment-website|get-lead-enrichment-company|buying signal|buying signals|intent signal|intent data|tech stack|technology stack|ad network|search demand|search volume|demand trends|amazon sales|marketplace sales|\basin\b|top brands|category leaderboard|cross retailer|retail media|get-ai-traffic-overview|get-sales-signals-intent|get-sales-signals-traffic|get-sales-signals-technology|get-demand-search-trends-aggregated|get-retail-cross-analysis-describe|get-categories-search|get-brands-search'

# Never block on stdin: bounded read so the script cannot stall when the harness
# holds stdin open without writing.
raw=""
IFS= read -r -d '' -t 2 raw 2>/dev/null || true

# UserPromptSubmit delivers a JSON object on stdin; match against its prompt field
# only. Matching the whole envelope false-fires on paths like .../similarweb-plugin
# inside transcript_path or cwd. Non-JSON stdin falls back to the raw text.
prompt="$raw"
if command -v python3 >/dev/null 2>&1; then
  prompt=$(printf '%s' "$raw" | python3 -c 'import json, sys
text = sys.stdin.read()
try:
    d = json.loads(text)
    out = d.get("prompt", "") if isinstance(d, dict) else ""
except Exception:
    out = text
print(out)' 2>/dev/null || printf '%s' "$raw")
fi

if printf '%s' "$prompt" | grep -iqE "$KEYWORDS_PATTERN"; then
  printf '[similarweb-plugin] Similarweb-shaped prompt detected. Matching recipe skills: sw-competitive-teardown, sw-audience-overlap, sw-channel-mix, sw-market-size, sw-aeo-audit, sw-page-mix, sw-keyword-opportunity. Apply the matching recipe skill, or the sw-router skill for free-form routing; these are skills, not slash commands, so never invoke them as /commands.\n'
  printf 'CLIENT OUTPUT RULE: in anything a client will receive (briefs, dashboards, files), never name MCP tools (get-...), endpoints, or data credits, and never use Similarweb product-line names: Shopper Intelligence, Sales Intelligence, Digital Research Intelligence, Digital Marketing Intelligence, App Intelligence, Stock Intelligence, CRIQ. This covers filenames, headings, and chart titles, in any casing or hyphenation, even when the user'"'"'s own prompt uses the term; substitute a plain description of the surface instead. One plain provenance line naming the data source is the only source mention.\n'
  printf 'Before any MCP call with no row bound, or any tool the catalog marks large, state the expected response size and bound it, split it, or divert it per the payload budget in the sw-foundation-core skill.\n'
fi

exit 0
