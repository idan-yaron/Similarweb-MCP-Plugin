#!/usr/bin/env python3
"""UserPromptSubmit hook for the claude-code bundle.

Injects a compact context block on Similarweb-shaped prompts: the recipe and
router surface, the client-output rule with the supplier product-name denylist,
and the payload pre-call step. Python because Windows sessions have no
guaranteed bash; stdin is read defensively so the hook can never stall or
crash the prompt (every failure path exits 0 with no output).

Emits hookSpecificOutput.additionalContext per the documented hook contract.
Keep the block under 1,200 characters: it rides on every matching prompt.
"""
import json
import re
import sys

KEYWORDS = re.compile(
    r"similarweb|web traffic|web rank|traffic-and-engagement|traffic and engagement"
    r"|channel mix|audience overlap|similar sites|ppc spend|keyword opportunity"
    r"|keyword gap|\baeo\b|seo audit|ai visibility|answer engine|market sizing"
    r"|market size|page mix|competitive teardown|organic search share"
    r"|paid search share|brand sales|market share|best sellers"
    r"|top selling products|app downloads|category performance|lead enrichment"
    r"|share of voice|marketing analysis|brand health|brand protection"
    r"|shopper intelligence|retail shelf|buying signal|buying signals"
    r"|intent signal|intent data|tech stack|technology stack|ad network"
    r"|search demand|search volume|demand trends|amazon sales|marketplace sales"
    r"|" r"\basin\b" r"|top brands|category leaderboard|cross retailer|retail media"
    r"|get-website-analysis-|get-websites-|get-keywords-|get-brands-"
    r"|get-categories-|get-ai-traffic-|get-sales-signals-|get-retail-cross-"
    r"|get-demand-search-|get-apps-|get-lead-enrichment-|get-pages-"
    r"|get-industry-|get-gen-ai-|get-custom-industries-|get-user-segments-",
    re.IGNORECASE)

CONTEXT = (
    "[similarweb-plugin] Similarweb-shaped prompt detected.\n"
    "- Recipes: sw-competitive-teardown, sw-audience-overlap, sw-channel-mix, "
    "sw-market-size, sw-aeo-audit, sw-page-mix, sw-keyword-opportunity; free-form "
    "asks route via the sw-router skill. These are skills, never /commands.\n"
    "- CLIENT OUTPUT RULE: in anything a client will receive (briefs, dashboards, "
    "files), never name MCP tools (get-...), endpoints, or data credits, and never "
    "use Similarweb product-line names: Shopper Intelligence, Sales Intelligence, "
    "Digital Research Intelligence, Digital Marketing Intelligence, "
    "App Intelligence, Stock Intelligence, CRIQ. This covers filenames, headings, and "
    "chart titles, in any casing or hyphenation, even when the user's own prompt "
    "uses the term; substitute a plain description of the surface instead. One "
    "plain provenance line naming the data source is the only source mention.\n"
    "- Before any MCP call with no row bound, or any tool the catalog marks large, "
    "state the expected response size and bound it, split it, or divert it per "
    "the payload budget in the sw-foundation-core skill.")


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    prompt = raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            prompt = data.get("prompt", "")
    except Exception:
        pass
    if isinstance(prompt, str) and KEYWORDS.search(prompt):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": CONTEXT,
        }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
