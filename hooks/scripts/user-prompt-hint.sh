#!/usr/bin/env bash
set -e

# Similarweb keyword surface (case-insensitive egrep pattern).
# Mirrors sw-router/sw-foundation-core auto-trigger keywords plus specific MCP tool names.
KEYWORDS_PATTERN='similarweb|web traffic|web rank|traffic-and-engagement|traffic and engagement|channel mix|audience overlap|similar sites|ppc spend|keyword opportunity|keyword gap|aeo|market sizing|market size|page mix|competitive teardown|organic search share|paid search share|brand sales|market share|app downloads|category performance|lead enrichment|share of voice|get-websites-traffic-channels|get-websites-audience-overlap-agg|get-websites-traffic-and-engagement|get-websites-similar-sites-agg|get-websites-website-rank|get-websites-ppc-spend|get-keywords-overview|get-keywords-seo-overview|get-brands-sales-performance-agg|get-categories-performance-agg|get-pages-popular-pages-agg|get-traffic-channels-share|get-lead-enrichment-website|get-lead-enrichment-company'

# Never block on stdin: if the harness does not feed it (observed on some Codex builds), time out fast instead of stalling to the hook timeout.
prompt=""
IFS= read -r -d '' -t 2 prompt 2>/dev/null || true

if printf '%s' "$prompt" | grep -iqE "$KEYWORDS_PATTERN"; then
  printf '[similarweb-plugin] Similarweb-shaped prompt detected, available recipes: /sw-competitive-teardown, /sw-audience-overlap, /sw-channel-mix, /sw-market-size, /sw-aeo-audit, /sw-page-mix, /sw-keyword-opportunity. Free-form prompts route via sw-router.\n'
fi

exit 0
