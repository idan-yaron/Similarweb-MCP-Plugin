<div align="center">

# Similarweb MCP Plugin

**Turn the Similarweb MCP server into deterministic, analyst-grade playbooks across Cowork, Claude Code, Codex, Cursor, and Claude.ai.**

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.1-blue.svg)](.claude-plugin/plugin.json)
[![Platforms](https://img.shields.io/badge/platforms-Cowork%20%7C%20Claude%20Code%20%7C%20Codex%20%7C%20Cursor%20%7C%20Claude.ai-blueviolet.svg)](#install)
[![Python](https://img.shields.io/badge/python-3.x%20stdlib-blue.svg)](build.py)

[Quickstart](#quickstart) · [What you get](#what-you-get) · [Install](#install) · [How it works](#how-it-works) · [Docs](docs/install-and-smoke-test.md)

</div>

---

## The problem this solves

The Similarweb MCP exposes 90 tools across web traffic, SEO, audience, AEO, apps, brands, categories, and lead enrichment. Out of the box the LLM treats them as a flat menu: it rediscovers tools every turn, picks suboptimal sequences, burns data credits, and produces shallow analyses.

This plugin is the expert layer that sits between your LLM and the Similarweb MCP. Install it once, ask anything Similarweb-shaped in natural language, and get a structured analyst-grade response.

## See it work

A single prompt to your AI client:

```
compare nike.com and adidas.com on similarweb
```

Routes automatically to `sw-competitive-teardown` and returns:

```
nike.com vs adidas.com | us | Feb-Apr 2026 | last_updated 2026-04-30

## Executive read

MATERIAL CHANGE: adidas's Display Ads spiked +54.4% over the last quarter
while nike's channel mix held flat, narrowing the static volume lead from
1.8x to 1.5x. Engagement quality at nike 3.7 stays ahead of adidas 2.9.
Audience overlap places the pair at 10.9% of union (SAME POND tier).

## Rank + reach

| Domain      | Global rank | Country rank |
|-------------|-------------|--------------|
| nike.com    | 274         | 92           |
| adidas.com  | 612         | 188          |

## Channel breakdown

nike.com
  Organic Search  33.6% ████████████████▏
  Direct          24.3% ███████████▋
  Paid Search     15.4% ███████▍
  Display Ads      9.4% ████▌

adidas.com
  Display Ads     28.1% █████████████▌
  Organic Search  22.4% ██████████▊
  Direct          18.9% █████████▏
  Paid Search     14.0% ██████▊

## Audience overlap

27.7% of adidas visits also go to nike   ███████████████▏
13.6% of nike visits also go to adidas   ███████▏
10.9% share of union, SAME POND tier.

## Strategic insights

- DEFEND: nike's 33.6% Organic Search share vs adidas 22.4% covers a
  1.5x reach lead at lower paid cost (confidence: HIGH).
- EXPOSE: adidas's +54.4% Display Ads spike narrowed the volume gap
  by 17%; monitor whether the spike sustains into Q3 (confidence: MEDIUM).
- PLAY: adidas's Affiliates lift is concentrated in 3 referrers; steal
  those partners or invest in equivalent reach (confidence: MEDIUM).

Sources: 158 data credits across 12 calls (4 rank, 2 traffic-and-engagement,
2 channels, 1 similar-sites, 1 audience-overlap, 2 ppc-spend).
```

What the plugin did under the hood: one batched `get-websites-audience-overlap-agg` call instead of two looped overlap calls, derived the effective window from a single rank smoke probe, normalized country to `us` before any call, labelled the audience-overlap pair against the SAME POND / ADJACENT / COMPLEMENTARY / DISJOINT ladder, classified the +54.4% delta against the WITHIN NOISE / MATERIAL / MAJOR thresholds, ended each strategic insight with a confidence tag.

## Highlights

- **Seven analyst recipes** that orchestrate multi-tool Similarweb playbooks the LLM picks poorly on its own.
- **Free-form routing** classifies any Similarweb-shaped question and dispatches to the right recipe (or asks one explicit clarifier).
- **Lazy capability discovery** so recipes never hard-stop on an access-denied tool; they degrade gracefully and remember what your tier exposes.
- **Intent-aware output** renders narrative for chat, tables when comparing, slide bullets when prepping, structured JSON when handing off to another agent.
- **Cross-platform** with one source: bundles for Cowork (flagship), Claude Code, Codex (spec-compliant marketplace), Cursor, and Claude.ai.

## What you get

### Seven user-invocable recipes

| Recipe | What it does |
|---|---|
| [`/sw-competitive-teardown`](skills/sw-competitive-teardown/SKILL.md) | One brand against N competitors: rank, traffic, channels, similar sites, optional audience overlap and PPC, rendered as exec read + tables + sources. |
| [`/sw-audience-overlap`](skills/sw-audience-overlap/SKILL.md) | Target vs up to 4 competitors: subset overlap with share-of-union, demographics, geography top 10, deduplicated reach, persona Jaccard. |
| [`/sw-channel-mix`](skills/sw-channel-mix/SKILL.md) | Channel breakdown on the live 10-channel taxonomy, period-over-period deltas, top inbound referrers, PPC spend, ad networks. |
| [`/sw-aeo-audit`](skills/sw-aeo-audit/SKILL.md) | Answer Engine Optimization proxy via SEO + SERP share-of-voice + answer-box-adjacent pages. Direct signal when a campaign UUID is supplied. |
| [`/sw-market-size`](skills/sw-market-size/SKILL.md) | Category sizing across Amazon shopper categories or Web industry slugs, with optional web companion and traffic enrichment. |
| [`/sw-page-mix`](skills/sw-page-mix/SKILL.md) | URL + folder content surface for a domain: top-N pages, folder hierarchy with traffic share, period-over-period change, HHI concentration verdict. |
| [`/sw-keyword-opportunity`](skills/sw-keyword-opportunity/SKILL.md) | Keyword gap analysis vs a competitor: competitor wins, shared territory, target wins, ROI ranked by volume times position gap. |

### Auto-trigger background skills

- **`sw-router`** classifies any free-form Similarweb-shaped prompt that did NOT invoke a specific `/sw-*` command, dispatches to the best-fit recipe in one line, or asks one crisp clarifier with explicit options.
- **`sw-foundation-core`**, **`sw-foundation-data`**, **`sw-foundation-render`** auto-load together on every Similarweb-shaped turn. They carry the MCP tool catalog with quirks, country and window normalization, freshness rules, citation block, error rendering patterns, and Unicode visualizations.

### Operator skills

- **`/sw-setup`** runs a thorough probe across all six tool categories and writes a known-state capability map to `~/.similarweb-plugin/capabilities.json`. Recipes do not require this map; they run lazily and discover access at runtime.
- **`/sw-config`** inspects, refreshes, or wipes the capability map; on Cowork it can schedule weekly or monthly grounding re-validation.

## Quickstart

Pick the easiest path for your stack. Full per-platform details are in [`docs/install-and-smoke-test.md`](docs/install-and-smoke-test.md).

### Cowork (Claude Desktop), the flagship

```
1. Configure the Similarweb MCP in Cowork (see Prerequisite)
2. Download similarweb-cowork-0.1.1.zip from the Releases page:
   https://github.com/idan-yaron/Similarweb-MCP-Plugin/releases/latest
3. Open Cowork: Customize > Plugins > Upload plugin, select the file
4. Type: "compare nike.com and adidas.com on similarweb"
```

You should see the recipe surface in the slash menu, the three sub-agents in the agent palette, and the UserPromptSubmit hook suggesting recipes on Similarweb-shaped prompts.

### Claude Code, Codex, Cursor, Claude.ai

See the collapsible install blocks below.

### Prerequisite (all platforms)

This plugin teaches the LLM how to use the Similarweb MCP. It does **not** bundle the MCP itself. Before installing the plugin, configure the Similarweb MCP server in your client per Similarweb's official install instructions for your account. Once any `similarweb` MCP tool is callable from your client, the plugin install gives the LLM the playbooks for using the tools well.

The plugin install will not trigger any "this plugin includes local MCP servers" security dialog, because the bundles ship no `mcpServers` configuration of their own. The trade-off is that the MCP must already be configured for the plugin to be useful.

## Install

Grab the bundle for your AI client from the [Releases page](https://github.com/idan-yaron/Similarweb-MCP-Plugin/releases/latest) and follow the per-platform section below. The filename references below assume you downloaded from Releases; if you built from source the same files live under `dist/` of the repo root.

<details>
<summary><b>Cowork (Claude Desktop)</b></summary>

Open Cowork, click **Customize > Plugins > Upload plugin**, select `similarweb-cowork-0.1.1.zip`. The validator should accept the bundle on first try.

After install: `/sw-config --show` confirms the bundle is live, the seven recipes appear in the `/` menu, three sub-agents appear in the agent palette, and Similarweb-shaped free-form prompts auto-suggest recipes via the UserPromptSubmit hook.

Requires the Similarweb MCP connector enabled in Cowork (see Prerequisite).

</details>

<details>
<summary><b>Claude Code</b></summary>

Install via the plugin marketplace flow:

```bash
/plugin marketplace add <git-url>
/plugin install similarweb@<marketplace>
```

Or drop `similarweb-claude-code-0.1.1.zip` into your Claude Code plugins directory and reload. After install: `/sw-config --show` confirms the bundle is live. Skills-only subset (no sub-agents, hooks, or HTML artifacts). Requires the Similarweb MCP server registered in your Claude Code MCP config (see Prerequisite).

</details>

<details>
<summary><b>Codex (OpenAI CLI)</b></summary>

The Codex bundle is a spec-compliant Codex marketplace per [developers.openai.com/codex/plugins/build](https://developers.openai.com/codex/plugins/build). The bundle root contains `.agents/plugins/marketplace.json` and `plugins/similarweb/`, which is what `codex plugin marketplace add` expects.

```bash
unzip similarweb-codex-0.1.1.zip -d ./similarweb-codex
codex plugin marketplace add ./similarweb-codex
codex plugin add similarweb@similarweb-local
```

The subcommand is `codex plugin add`, not `codex plugin install`. After install, `codex plugin list` shows `similarweb@similarweb-local (installed, enabled)` and a fresh `codex exec` session surfaces all ten user-facing `similarweb:sw-*` skills.

The Codex bundle ships `plugins/similarweb/.mcp.json.template` for the MCP shape; rename to `.mcp.json` and fill in your `SIMILARWEB_API_KEY`, or configure the server in your global Codex MCP config.

**Sub-agents companion** (optional): per the Codex spec, sub-agents live in `~/.codex/agents/`. Three TOMLs ship in `similarweb-codex-subagents-0.1.1/`:

```bash
mkdir -p ~/.codex/agents
cp similarweb-codex-subagents-0.1.1/*.toml ~/.codex/agents/
```

**Hooks limitation**: codex-cli 0.133.0-alpha.1 does not execute plugin hooks in `exec` sessions (verified live 2026-05-27). The `hooks/` directory ships for forward-compatibility; the capability-map summary the hooks would inject is discovered lazily by the foundation skills at runtime.

</details>

<details>
<summary><b>Cursor</b></summary>

Install via `/add-plugin` from a local path pointing at `similarweb-cursor-0.1.1.zip`, or via cursor.com/marketplace if published. After install, `/sw-config` should be available in the command palette and chat. Skills-only subset. Requires the Similarweb MCP server in Cursor's MCP settings (see Prerequisite).

</details>

<details>
<summary><b>Claude.ai</b></summary>

Claude.ai installs skills one at a time: **Settings > Features > Skills > upload** each of the 13 per-skill zips from `similarweb-claude-ai-0.1.1/` individually.

Claude.ai has no slash command surface, so invocation is by name in natural language: "run sw-competitive-teardown on apple.com vs samsung.com" or just "compare apple.com and samsung.com on similarweb" (the router handles the natural-language dispatch). Skills-only subset. Requires the Similarweb MCP connector enabled in your Claude.ai account (see Prerequisite).

</details>

For click-by-click instructions, smoke-test prompts, known per-platform limitations, and troubleshooting, see [`docs/install-and-smoke-test.md`](docs/install-and-smoke-test.md).

## How it works

```
                      ┌──────────────────────────────────┐
   user prompt ─────► │   sw-router (free-form classifier) │ ──► one of /sw-* recipes
                      └──────────────────────────────────┘
                                       │
                                       ▼
                      ┌──────────────────────────────────┐
                      │   sw-foundation-core / data / render │
                      │   (silent on every Similarweb turn)  │
                      └──────────────────────────────────┘
                                       │
                                       ▼
                      ┌──────────────────────────────────┐
                      │     Similarweb MCP (90 tools)     │
                      └──────────────────────────────────┘
```

Four moving parts:

1. **Foundation layer**. Three silent skills (`sw-foundation-core`, `sw-foundation-data`, `sw-foundation-render`) auto-load on every Similarweb-shaped turn. They carry the MCP tool catalog with quirks, country and window resolution, freshness rules, citation block, error rendering, and intent-aware output rules so the LLM does not rediscover the surface each session.
2. **Recipes**. Seven deterministic multi-tool playbooks for the high-value analyses. Each one enforces hard rules: no fabrication, no N looped calls when an `-agg` batched variant exists, ISO-2 country normalization, citation block, expert-heuristic confidence tags on every insight.
3. **Router**. Classifies any free-form Similarweb-shaped prompt to the best-fit recipe in one line, asks one crisp clarifier with explicit options when multiple recipes fit, or plans a direct 1-to-3-tool MCP sequence when no recipe fits.
4. **Lazy capability discovery**. Recipes never hard-stop on a missing capability map. When a tool returns 403 or a partial-access envelope, the recipe degrades gracefully (skipping optional steps, aborting only if a required tool is gated) and appends the observation to `~/.similarweb-plugin/capabilities.json`. Future runs pre-filter. Run `/sw-config --refresh` for a proactive probe.

## Cowork-only superpowers

The Cowork bundle ships the full surface; the other four targets are skills-only subsets of the same source. Cowork adds:

- **Three sub-agents** under `agents/`. `similarweb-analyst` is the general orchestrator. `competitive-deep-dive` handles 5+ competitor teardowns with a strongest-rival drill-in. `aeo-strategist` composes AEO + page-mix + keyword-opportunity into a content roadmap. Each runs in its own context window and returns a synthesized brief.
- **Event-driven hooks**. `SessionStart` injects the capability-map summary, `UserPromptSubmit` hints recipe coverage on Similarweb-shaped prompts, `Stop` surfaces NEXT MOVES follow-ups.
- **Interactive HTML dashboards** via `mcp__cowork__create_artifact` for high-dimensionality outputs: 3+ competitors, 10+ top brands, deep folder trees, Sankey audience overlap. Supplemental to markdown; markdown remains canonical.
- **Cross-plugin connectors** declared in [`CONNECTORS.md`](CONNECTORS.md): `~~deck` (pptx), `~~spreadsheet` (xlsx), `~~doc` (pdf/docx), `~~chat` (Slack/Teams/Discord), `~~data warehouse`, `~~CRM`. Each recipe's `## Export options` block cites these placeholders; Cowork resolves them to the user's installed plugins at runtime.

## Build from source

```bash
python3 build.py --validate    # CI-safe structural validation
python3 build.py --build       # emits six artifacts to dist/
```

Six artifacts:

- `similarweb-cowork-<version>.zip`: flagship Cowork bundle with skills + commands + agents + hooks + connectors
- `similarweb-claude-code-<version>.zip`: Claude Code skills + commands
- `similarweb-codex-<version>.zip`: spec-compliant Codex marketplace at `.agents/plugins/` + `plugins/similarweb/`
- `similarweb-codex-subagents-<version>/`: companion with three Codex sub-agent TOMLs
- `similarweb-cursor-<version>.zip`: Cursor `.cursor-plugin/` layout
- `similarweb-claude-ai-<version>/`: 13 per-skill zips for Claude.ai

Python 3 stdlib only, no third-party deps. Text files are normalized to LF line endings at zip-time; bundles ship without a BOM.

## Privacy and grounding

This plugin processes user-supplied data (domains, brands, CSVs) and returns MCP responses verbatim. Runtime use against your own client data is unrestricted.

Every assertion a skill makes about MCP behavior is live-validated against the Similarweb MCP before release. Drift is caught by `build.py --validate` rejecting unknown grounded-assertion references in each skill's `## Grounded assertions` body block, per-recipe runtime checks when `meta.last_updated` shifts, and the opt-in `/sw-config --schedule-grounding` cron on Cowork.

## Contributing

Bug reports, recipe requests, and PRs welcome at [GitHub Issues](https://github.com/idan-yaron/Similarweb-MCP-Plugin/issues). See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the release checklist and grounding-ledger policy.

## License

[MIT](LICENSE) © 2026 Idan Yaron
