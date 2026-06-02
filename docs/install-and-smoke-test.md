# Install and smoke test

Per-platform install instructions, verification steps, smoke tests, known limitations, and troubleshooting for the Similarweb MCP plugin.

## Where to get the bundles

Download the bundle for your AI client from the [Releases page](https://github.com/idan-yaron/Similarweb-MCP-Plugin/releases/latest). The four AI-environment bundles ship as `.zip` assets attached to each release:

- `similarweb-cowork-0.1.10.zip` (Cowork-native flagship; also accepted as `.plugin`)
- `similarweb-claude-code-0.1.10.zip` (Claude Code bundle; skills-only subset)
- `similarweb-codex-0.1.10.zip` (Codex CLI bundle; skills-only subset)
- `similarweb-cursor-0.1.10.zip` (Cursor bundle; skills-only subset)

The Cowork bundle is the flagship target with the full surface (skills + agents + hooks + artifacts + connectors). The other three are skills-only subsets.

**Claude.ai support** ships as 13 per-skill `.zip` files (uploaded one at a time via Claude.ai's skill UI) and the **Codex sub-agents companion** ships as a set of three `.toml` files. Neither is attached to the official release to keep the downloads page focused; both are produced by `python3 build.py --build` if you clone the source. See the "Claude.ai" and "Codex sub-agents companion" sections below.

Filenames in this document reference the bare asset names as served by GitHub Releases. If you built from source, the same files live under `dist/` of the repo root.

Every platform requires the Similarweb MCP server registered in that environment's MCP config; the plugin is a co-pilot layer, not the MCP itself.

## Prerequisite (all platforms)

This plugin ships pure skill content. It does NOT bundle the Similarweb MCP server, and the bundles do NOT contain any `mcpServers` configuration. Two consequences:

1. **Plugin install will not trigger any "this plugin includes local MCP servers" security dialog.** This is by design and is the dominant pattern for MCP-companion plugins.
2. **You are fully responsible for configuring the Similarweb MCP server in your client BEFORE installing the plugin.** Use Similarweb's official install instructions for your account. If you do not have them, contact your Similarweb account team.

For each platform below, the "Verify MCP is configured" section tells you where the MCP entry lives in that client's config. The plugin install itself does not modify that config in any way.

---

## Cowork (Claude Desktop)

### Where the bundle lives

`similarweb-cowork-0.1.10.zip`

Contents (23 files):

```
.claude-plugin/plugin.json
skills/sw-aeo-audit/SKILL.md
skills/sw-audience-overlap/SKILL.md
skills/sw-channel-mix/SKILL.md
skills/sw-competitive-teardown/SKILL.md
skills/sw-config/SKILL.md
skills/sw-foundation-core/SKILL.md
skills/sw-foundation-data/SKILL.md
skills/sw-foundation-render/SKILL.md
skills/sw-keyword-opportunity/SKILL.md
skills/sw-market-size/SKILL.md
skills/sw-page-mix/SKILL.md
skills/sw-router/SKILL.md
skills/sw-setup/SKILL.md
agents/similarweb-analyst.md
agents/competitive-deep-dive.md
agents/aeo-strategist.md
hooks/hooks.json
hooks/scripts/session-start.sh
hooks/scripts/user-prompt-hint.sh
hooks/scripts/stop.sh
CONNECTORS.md
README.md
```

What you're installing: everything the other four platforms get (7 recipes + 3 foundations + 2 operators + sw-router), plus three Cowork-only autonomous agents, three event-driven hooks, the cross-plugin connector declarations, and the artifact-pattern docs. v0.3.0 failed Cowork validation with "Plugin validation failed."; v0.1.8 fixes that by normalizing CRLF to LF at zip-time (the Cowork VM is Linux) and moving the `depends_on` ledger references out of YAML frontmatter into a `## Grounded assertions` body block (Cowork rejects non-canonical fields).

### Verify the Similarweb MCP connector is enabled (do this BEFORE installing the plugin)

In Cowork: **Customize > Connectors > Similarweb**. If the toggle is off or the connector is missing, follow Similarweb's official Cowork install instructions for your account. To test independently: open a fresh Cowork chat and invoke a Similarweb MCP tool by name; the call should succeed without the plugin installed.

### Install

1. Open Cowork.
2. Click **Customize > Plugins > Upload plugin**.
3. Select `similarweb-cowork-0.1.10.zip`.
4. Cowork validates the bundle (LF line endings, canonical frontmatter, hooks.json shape). The validator should accept the bundle on first try.
5. Cowork loads the plugin into the active session. No restart required.

### Verify install

- `/sw-config --show` is available in the `/` menu and renders the current capability map (or "lazy mode" if no map yet).
- `/` menu lists the seven user-invocable recipes.
- The three agents (similarweb-analyst, competitive-deep-dive, aeo-strategist) appear under the agent palette.
- A Similarweb-shaped natural-language prompt (e.g., "who are payoneer's competitors") triggers the UserPromptSubmit hook, which injects a one-line recipe-availability hint.

### Smoke tests

1. **Recipe via slash command:** `/sw-competitive-teardown apple.com --vs samsung.com`. The recipe renders Executive read + tables + strategic insights + sources + NEXT MOVES.
2. **Free-form routing:** "compare nike.com and adidas.com on similarweb". sw-router auto-fires, cites the routing decision in one line, dispatches sw-competitive-teardown.
3. **Agent dispatch:** "do a comprehensive competitive analysis of shopify.com". similarweb-analyst agent activates, orchestrates 2-3 recipes in its own context window, returns a synthesized brief.
4. **Hook in action:** open a fresh session. The SessionStart hook injects a one-line summary of the capability map (if present). Free-form prompts that match Similarweb keywords get the UserPromptSubmit recipe-hint line.
5. **Interactive artifact (opt-in):** "compare nike, adidas, puma, under armour on similarweb, show me a dashboard". The recipe emits markdown PLUS an `mcp__cowork__create_artifact` call producing an inline HTML panel with sortable tables.
6. **Connector export:** "build me a deck of this teardown". The recipe delegates to `~~deck` (resolves to pptx in Cowork by default); a PPTX appears in the Cowork files panel.
7. **Schedule grounding (opt-in):** `/sw-config --schedule-grounding weekly`. Confirms a Cowork scheduled task is created. Drift reports will appear in `~/.similarweb-plugin/drift-<date>.md` when shape changes are detected. `--schedule-grounding off` cancels.

### Known limitations

- Connector targets (pptx, xlsx, pdf, slack-by-salesforce, etc.) are NOT bundled. The plugin calls them via the `Skill` tool at runtime. If the user has not installed the upstream Cowork plugin, the connector call returns a graceful one-line error telling the user which Cowork plugin to install.
- The interactive HTML artifact is supplemental, not a replacement for the markdown. If `mcp__cowork__create_artifact` is unavailable or errors, the recipe silently emits markdown only.
- Scheduled grounding requires Cowork; on non-Cowork runtimes `--schedule-grounding` aborts with a one-line message directing the user to the manual checklist in CONTRIBUTING.md.

### Troubleshoot

- **"Plugin validation failed."** on upload: this was the v0.3.0 issue. v0.1.8 fixed CRLF and the depends_on frontmatter field. If you still see this on v0.1.8, log the Cowork validator output and check `python tests/structural-validation.py` locally to compare expected bundle shape against what shipped.
- **Hook fires too aggressively on UserPromptSubmit:** the keyword surface is in `hooks/scripts/user-prompt-hint.sh`. Edit `KEYWORDS_PATTERN` if your workflow has lots of false positives.
- **Agent does not auto-trigger:** check that the agent's `description` frontmatter contains 2-4 `<example>` blocks (Cowork's auto-router uses those to match natural-language prompts to agents).

---

## Claude Code

### Where the bundle lives

`similarweb-claude-code-0.1.10.zip`

Contents:

```
.claude-plugin/plugin.json
skills/sw-aeo-audit/SKILL.md
skills/sw-audience-overlap/SKILL.md
skills/sw-channel-mix/SKILL.md
skills/sw-competitive-teardown/SKILL.md
skills/sw-config/SKILL.md
skills/sw-foundation-core/SKILL.md
skills/sw-foundation-data/SKILL.md
skills/sw-foundation-render/SKILL.md
skills/sw-keyword-opportunity/SKILL.md
skills/sw-market-size/SKILL.md
skills/sw-page-mix/SKILL.md
skills/sw-router/SKILL.md
skills/sw-setup/SKILL.md
```

What you're installing: 7 user-invocable recipes (competitive-teardown, audience-overlap, aeo-audit, channel-mix, market-size, page-mix, keyword-opportunity), 1 router, 2 operator skills (sw-setup + sw-config), and the 3 sub-foundation skills (sw-foundation-core / data / render) that auto-load together on every Similarweb-shaped turn. v0.1.8 splits the original sw-foundation into 3 sub-foundations carrying the same description surface so all three auto-load in lockstep; recipes declare their inheritance explicitly via an `Inherits:` block.

Note: no `.mcp.json` ships in the bundle. The Similarweb MCP server must already be configured in your client (see Prerequisite above).

### Verify MCP is configured (do this BEFORE installing the plugin)

Open the Claude Code MCP config (`~/.claude/settings.json` or the project `.mcp.json`) and confirm there is a `similarweb` server entry, populated with the transport and command from Similarweb's official install instructions for your account. The plugin does not modify this config and does not ship a template; the entry is fully yours to maintain. To test the connection independently of this plugin: invoke any Similarweb MCP tool by name from a fresh chat. If the MCP is unreachable, recipes will surface access-denied errors at runtime; run `/sw-config --refresh` after fixing the MCP config to populate `state: mcp_not_configured` (or the appropriate state) in `~/.similarweb-plugin/capabilities.json`.

### Install

Option A (marketplace flow):

1. `/plugin marketplace add https://github.com/idan-yaron/similarweb-mcp-plugin` (or the local path).
2. `/plugin install similarweb@similarweb-mcp-plugin`.
3. Restart the Claude Code session.

Option B (direct):

1. Unzip `similarweb-claude-code-0.1.10.zip` into `~/.claude/plugins/similarweb/` (or the user-plugins directory your install uses).
2. Restart the Claude Code session.

### Verify install

- `/sw-config --show` should be available in the slash-command palette.
- Running `/sw-config --show` before any Similarweb question prints two lines: `No capability map yet. The plugin runs lazily and will discover access as recipes execute.` followed by `Run /sw-config --refresh to force a thorough probe.`
- Asking a free-form Similarweb question like "what is the audience overlap between apple.com and samsung.com on similarweb" should cause sw-router to auto-fire and either dispatch to `/sw-audience-overlap` or ask one clarifier.

### Smoke test

```
/sw-competitive-teardown apple.com --vs samsung.com
```

Look for in the output:

- An "Executive read" paragraph at the top.
- A traffic-and-engagement table (visits, pages/visit, avg duration, bounce rate) for both domains.
- A channel-mix table on the 10-channel taxonomy.
- A `## Sources` block at the bottom citing each MCP tool called (rank, traffic-and-engagement looped per domain, channels, etc.).
- No fabricated numbers; if a tool returned null, the cell shows `n/a`.

Also try the router:

```
how is samsung.com doing on similarweb
```

Look for: a one-line routing decision (e.g. "Routing to /sw-competitive-teardown on samsung.com with no explicit competitors") followed by the recipe's output, OR one clarifier with 2-3 explicit options.

### Known limitations

- The bundle does not ship a `.mcp.json`. The Similarweb MCP server must be configured separately in your client config before the MCP probe succeeds (see Prerequisite section above).
- Claude Code reads `~/.similarweb-plugin/capabilities.json` (HOME-scoped, not project-scoped); the same probe state is shared across all projects.

### Troubleshooting

- **Slash commands do not appear**: confirm the plugin is installed (`/plugin list`) and restart the session. The `.claude-plugin/plugin.json` manifest must parse; run `python3 build.py --validate` against the source if you are building locally.
- **`mcp_not_configured` state persists**: the Similarweb MCP server entry in your settings is missing or the command/transport is wrong. Verify it independently with another MCP-aware tool.
- **`auth_invalid` state**: your Similarweb API key is missing or rejected. Confirm `SIMILARWEB_API_KEY` is set in the MCP server's env.
- **sw-router does not auto-fire on free-form prompts**: confirm the prompt mentions a Similarweb-shaped keyword (similarweb, web traffic, web rank, traffic and engagement, channel mix, audience overlap, market size, AEO, similar sites, PPC spend, keywords, app downloads, brand sales, category performance, or a specific Similarweb MCP tool name). Without one of these, sw-router stays dormant by design.

---

## Codex (OpenAI CLI)

The Codex bundle is a spec-compliant Codex MARKETPLACE per [developers.openai.com/codex/plugins/build](https://developers.openai.com/codex/plugins/build). The marketplace manifest lives at `.agents/plugins/marketplace.json`, the plugin payload lives under `plugins/similarweb/`. That layout is what `codex plugin marketplace add` expects (verified live 2026-05-27 against codex-cli 0.133.0-alpha.1). An optional sister artifact ships three sub-agents.

### Where the bundles live

- `similarweb-codex-0.1.10.zip` is attached to the [latest release](https://github.com/idan-yaron/Similarweb-MCP-Plugin/releases/latest); download it from there.
- `similarweb-codex-subagents-0.1.10/` (optional companion: 3 sub-agent TOMLs) is NOT attached to the official release. To get it, clone the repo and run `python3 build.py --build`; the directory and TOMLs appear under `dist/`.

### Codex marketplace bundle contents

```
.agents/plugins/marketplace.json                            (Codex marketplace manifest)
plugins/similarweb/.codex-plugin/plugin.json                (plugin manifest with full interface block)
plugins/similarweb/.mcp.json.template                       (template; rename to .mcp.json after filling)
plugins/similarweb/assets/logo.png                          (install-card icon and logo)
plugins/similarweb/hooks/hooks.json                         (SessionStart, UserPromptSubmit, Stop)
plugins/similarweb/hooks/scripts/session-start.sh
plugins/similarweb/hooks/scripts/user-prompt-hint.sh
plugins/similarweb/hooks/scripts/stop.sh
plugins/similarweb/skills/sw-aeo-audit/SKILL.md
plugins/similarweb/skills/sw-aeo-audit/agents/openai.yaml
... (13 skills, each with its own agents/openai.yaml)
```

Per-skill `skills/<name>/agents/openai.yaml` carries `interface` and `policy.allow_implicit_invocation` per the Codex spec. The seven user-invocable recipes get a full interface block (displayName, defaultPrompt) plus implicit invocation. Operator skills (sw-config, sw-setup), the router, and the three foundations get `policy.allow_implicit_invocation: true` only.

### Verify MCP is configured (do this BEFORE installing the plugin)

Your Codex `mcp.json` must contain a `mcpServers.similarweb` block with the transport, command, and `SIMILARWEB_API_KEY` env var. Populate it from Similarweb's official Codex install instructions for your account.

The bundle ships `plugins/similarweb/.mcp.json.template` as a shape reference (transport, command, args, env var name). To use it: unzip the bundle, rename `.mcp.json.template` to `.mcp.json`, fill in your real values. Codex never reads `.mcp.json.template` directly, so no auto-spawn happens on the placeholder values.

### Install (recommended: Codex Desktop UI)

The canonical Codex marketplace tree is committed at the repo root (`.agents/plugins/marketplace.json` plus `plugins/similarweb/`). Codex Desktop's **Add marketplace** dialog can fetch it directly from GitHub.

1. Open Codex Desktop, click **Plugins** in the left sidebar.
2. Click the marketplace dropdown next to the search bar (it defaults to **Built by OpenAI**) and choose **+ Add more**.
3. In the **Add marketplace** dialog:
   - **Source**: `idan-yaron/Similarweb-MCP-Plugin`
   - **Git ref**: `v0.1.10` (or `main` for the latest)
   - **Sparse paths**: leave blank
4. Click **Add marketplace**. The marketplace registers; the Similarweb plugin appears under the marketplace dropdown.
5. Open a new chat in Codex and type `compare nike.com and adidas.com on similarweb`. The `sw-router` skill auto-dispatches to `sw-competitive-teardown` and you should see a structured response with rank, traffic, channels, audience overlap, and strategic insights.

Codex's manifest loader looks at the staging ROOT for `.agents/plugins/marketplace.json`; the **Sparse paths** field is a fetch filter, not a root-redirector (verified 2026-05-28 by inspecting Codex's staging `.git/info/sparse-checkout`). That is why the marketplace tree lives at the repo root rather than under a subdirectory.

### Install (alternative: CLI marketplace add)

For users who prefer the terminal or want to point Codex at an unzipped Release bundle:

1. Download `similarweb-codex-0.1.10.zip` from the [latest release](https://github.com/idan-yaron/Similarweb-MCP-Plugin/releases/latest).
2. From the directory containing the downloaded zip, run:

```bash
unzip similarweb-codex-0.1.10.zip -d ./similarweb-codex
codex plugin marketplace add ./similarweb-codex
codex plugin add similarweb@similarweb
```

The subcommand is `codex plugin add`, not `codex plugin install`. After install, `codex plugin list` shows `similarweb@similarweb (installed, enabled)`.

The subcommand is `codex plugin add`, not `codex plugin install`. Codex renders the install card from the manifest `interface` block: display name "Similarweb", brand color, logo, three example default prompts.

After install, the plugin appears in `codex plugin list` under marketplace `similarweb` as `(installed, enabled)`. A fresh `codex exec` session shows all ten user-facing sw-* skills in the developer prompt's `### Available skills` block.

### Install (fallback: per-skill copy)

If your Codex version does not support local marketplaces, unzip the bundle and copy each `plugins/similarweb/skills/sw-*/` folder into `~/.codex/skills/`. This skips the install card, hooks, and marketplace registration. The skills still trigger via natural language; the per-skill `agents/openai.yaml` carries the `policy.allow_implicit_invocation` flag Codex needs.

Do NOT unzip the entire bundle into `~/.codex/plugins/sw/`. Codex's plugin loader resolves plugins only through marketplace registration; a manually-placed plugin directory under `~/.codex/plugins/` is silently ignored (no error, no listing in `codex plugin list`, no skill discovery).

### Install the sub-agents companion (optional, source-build only)

Per the Codex spec, sub-agents live in `~/.codex/agents/` (or `.codex/agents/` for project scope), not inside any plugin. The three TOMLs (`similarweb-analyst`, `competitive-deep-dive`, `aeo-strategist`) are NOT attached to the GitHub release; the official release pages stay focused on the four installable AI environments. To get the companion:

```bash
git clone https://github.com/idan-yaron/Similarweb-MCP-Plugin.git
cd Similarweb-MCP-Plugin
python3 build.py --build
mkdir -p ~/.codex/agents
cp dist/similarweb-codex-subagents-0.1.10/*.toml ~/.codex/agents/
```

After install the three agents are available in Codex's agent palette and via `@<agent-name>` dispatch.

### Verify install

- `codex plugin list` shows `similarweb@similarweb (installed, enabled)`.
- A fresh `codex exec --sandbox read-only "List the similarweb plugin skills"` enumerates all ten user-facing `similarweb:sw-*` skills.
- The install card renders with the Similarweb display name, brand color, and logo.
- A Similarweb-shaped natural-language prompt (e.g. "compare nike and adidas on similarweb") triggers the router skill via implicit invocation.

### Smoke test

```
/sw-channel-mix apple.com --window last-90d --vs-period prior-90d
```

Or natural language:

```
break down apple.com's traffic channels over the last 90 days vs the prior 90 days on similarweb
```

Look for: the 10-channel taxonomy table, a delta column (current vs prior), an inbound-referrers table, and the Sources block. The window-to-window comparison should run TWO sequential `get-websites-traffic-channels` calls (flat time series cannot split current from prior).

### Known limitations

- Codex slash-command surface varies by version; if `/sw-config` is not accepted, invoke by saying "run sw-config" or "show similarweb config" and let the router dispatch.
- Per-skill `policy.allow_implicit_invocation: true` causes the router and recipes to fire on natural-language prompts. If your Codex policy disables implicit invocation, invoke each recipe by name.
- Sub-agents are NOT bundled with the plugin (Codex spec puts them outside plugins). Install the companion artifact separately to get them.
- **Hooks are no-ops on codex-cli 0.133.0-alpha.1**: the bundle ships `SessionStart`, `UserPromptSubmit`, and `Stop` hook scripts for forward-compatibility with future Codex versions and Cowork parity, but live probes against codex-cli 0.133.0-alpha.1 show no hook execution and no hook output in session rollouts. The capability-map summary those hooks would inject is instead discoverable lazily via the foundation skills at runtime. None of the OpenAI-bundled or curated plugins ship hooks today; we will revisit when Codex documents hook execution in `exec` mode.

### Troubleshooting

- **`Error: invalid marketplace file ...: marketplace root does not contain a supported manifest`**: you pointed `codex plugin marketplace add` at a path that is not a Codex marketplace root. The bundle root must contain `.agents/plugins/marketplace.json`. If you unzipped to `./similarweb-codex/`, that directory IS the marketplace root and the manifest sits at `./similarweb-codex/.agents/plugins/marketplace.json`. Re-check the unzip step.
- **Skills not discovered**: confirm each `plugins/similarweb/skills/sw-*/SKILL.md` exists and each frontmatter parses. Every SKILL.md must start with `---\n` and have `name:` and `description:` fields.
- **Per-skill `agents/openai.yaml` errors on load**: validate the YAML structurally (`python3 -c "import yaml; yaml.safe_load(open('plugins/similarweb/skills/sw-competitive-teardown/agents/openai.yaml'))"`); each file is hand-rolled by `build.py`, not yaml-library-emitted.
- **`mcp_not_configured`**: same diagnosis as Claude Code; verify the `.mcp.json` exists at the plugin root after the rename step, or the `mcpServers.similarweb` block is in your global Codex MCP config.
- **Recipe runs but renders no Sources block**: the foundation skill did not load. Confirm `plugins/similarweb/skills/sw-foundation-render/SKILL.md` is present and that the Similarweb-keyword trigger fired. All 3 sub-foundations share the same description-surface so they auto-load together.
- **Sub-agent palette empty**: confirm the companion TOMLs landed in `~/.codex/agents/` (or `.codex/agents/` for project scope). Validate each with `python3 -c "import tomllib; tomllib.load(open('similarweb-analyst.toml','rb'))"`.

---

## Cursor

### Where the bundle lives

`similarweb-cursor-0.1.10.zip`

Contents:

```
.cursor-plugin/plugin.json
.cursor-plugin/marketplace.json
.cursor-plugin/skills/sw-aeo-audit/SKILL.md
.cursor-plugin/skills/sw-audience-overlap/SKILL.md
.cursor-plugin/skills/sw-channel-mix/SKILL.md
.cursor-plugin/skills/sw-competitive-teardown/SKILL.md
.cursor-plugin/skills/sw-config/SKILL.md
.cursor-plugin/skills/sw-foundation-core/SKILL.md
.cursor-plugin/skills/sw-foundation-data/SKILL.md
.cursor-plugin/skills/sw-foundation-render/SKILL.md
.cursor-plugin/skills/sw-keyword-opportunity/SKILL.md
.cursor-plugin/skills/sw-market-size/SKILL.md
.cursor-plugin/skills/sw-page-mix/SKILL.md
.cursor-plugin/skills/sw-router/SKILL.md
.cursor-plugin/skills/sw-setup/SKILL.md
```

Note: no `.cursor-plugin/mcp.json` ships in the bundle. The Similarweb MCP server must already be configured in Cursor's MCP settings (see Prerequisite above).

### Verify MCP is configured (do this BEFORE installing the plugin)

Open Cursor Settings > MCP and confirm a `similarweb` server entry exists with a valid command, populated from Similarweb's official Cursor install instructions for your account. The plugin does not ship a template and does not modify your MCP settings.

### Install

Option A (in-app):

1. In Cursor, run `/add-plugin` from the command palette.
2. Point at the local path of `similarweb-cursor-0.1.10.zip` (or a directory containing the unzipped `.cursor-plugin/` tree).
3. Reload the Cursor window.

Option B (marketplace):

1. Browse to `cursor.com/marketplace` if the plugin has been published there.
2. Click "Add to Cursor" and follow the in-app prompt.

### Verify install

- `/sw-config --show` is available in the Cursor chat command palette.
- Settings > Plugins should list `similarweb` with version 0.1.10.
- A free-form Similarweb prompt triggers sw-router.

### Smoke test

```
/sw-audience-overlap apple.com --against samsung.com,google.com
```

Look for:

- A subset overlap table showing each of the 2^3-1 = 7 subsets (apple only, samsung only, google only, apple+samsung, apple+google, samsung+google, all three) with share-of-union percentages.
- Demographics rendered as TWO adjacent tables (age and gender are independent dimensions, NOT cross-tabulated).
- Geography top 10 with `rank=0` cells rendered as `n/a` (not as 0).
- Per-domain deduplicated reach (three rows, one per domain), looped because the dedup tool takes a single domain.
- Sources block citing one batched `get-websites-audience-overlap-agg` call (NOT three looped overlap calls).

### Known limitations

- Cursor's plugin surface is newer than Claude Code's; some plugin-manifest fields may be ignored. The minimum that must parse is `.cursor-plugin/plugin.json` and `.cursor-plugin/marketplace.json`.
- The `.cursor-plugin/` wrapper is mandatory; Cursor will not discover skills at the root of the zip.

### Troubleshooting

- **`/add-plugin` does not accept the zip**: confirm the zip's root contains `.cursor-plugin/`. If the zip's root is the platform's contents (no wrapper dir), Cursor may reject it; in that case, unzip first and point Cursor at the unzipped directory.
- **`marketplace.json` schema mismatch**: Cursor's marketplace schema is evolving. The bundle ships the minimum fields (`name`, `version`, `description`, `author`); if Cursor reports a missing required field, add it manually and report so we can update the build script.
- **Skills do not auto-trigger on free-form prompts**: confirm sw-router's SKILL.md is present at `.cursor-plugin/skills/sw-router/SKILL.md` and that its frontmatter `description` field is intact (truncation breaks auto-trigger).

---

## Claude.ai

### Where the bundles live

`similarweb-claude-ai-0.1.10/` (a directory, NOT a single zip)

Contents (13 per-skill zips, uploaded one at a time):

```
sw-aeo-audit.zip
sw-audience-overlap.zip
sw-channel-mix.zip
sw-competitive-teardown.zip
sw-config.zip
sw-foundation-core.zip
sw-foundation-data.zip
sw-foundation-render.zip
sw-keyword-opportunity.zip
sw-market-size.zip
sw-page-mix.zip
sw-router.zip
sw-setup.zip
```

Each zip contains a single `<skill-name>/SKILL.md`. Frontmatter is stripped of `allowed-tools` and `argument-hint` (Claude.ai's sandbox does not honor these per cross-CLI research).

### Install

1. Open Claude.ai in your browser.
2. Settings > Features > Skills.
3. Click "Upload skill".
4. Upload the 3 sub-foundations first (they are the auto-load skills the others rely on): `sw-foundation-core.zip`, `sw-foundation-data.zip`, `sw-foundation-render.zip`.
5. Upload `sw-setup.zip`, `sw-router.zip`, `sw-config.zip`.
6. Upload each user-invocable recipe: `sw-competitive-teardown.zip`, `sw-audience-overlap.zip`, `sw-channel-mix.zip`, `sw-market-size.zip`, `sw-aeo-audit.zip`, `sw-page-mix.zip`, `sw-keyword-opportunity.zip`.

Each skill must be uploaded individually; Claude.ai does not accept the directory as a bundle.

### Verify install

- Settings > Features > Skills should list 13 entries (one per skill).
- Asking a Similarweb-shaped question in chat ("compare apple.com and samsung.com on similarweb") should cause sw-foundation-core / data / render to auto-load and sw-router to dispatch.
- Saying "run sw-config" should produce a capability-map summary (or, before any probe has run, the two-line lazy-discovery message: `No capability map yet. The plugin runs lazily and will discover access as recipes execute.` / `Run /sw-config --refresh to force a thorough probe.`).

### Verify MCP is configured (do this BEFORE uploading the skills)

In Claude.ai, Settings > Connectors (or Custom Connectors, depending on plan) must show the Similarweb MCP connector enabled. Configure it from Similarweb's official Claude.ai install instructions for your account. The connector is a separate install from the skill plugin; the plugin assumes it is present and never carries connector configuration.

### Smoke test

Claude.ai has NO slash commands. Invoke recipes by name in natural language:

```
run sw-competitive-teardown on apple.com vs samsung.com
```

Or:

```
compare apple.com and samsung.com on similarweb
```

Or one of the new v0.1.10 recipes:

```
what's nike.com's content surface? map the top pages and folders.
what keywords is adidas.com winning that nike.com isn't?
```

Look for the same shape as Claude Code: executive read, tables, sources block. If sw-router dispatches, it should cite the routing decision in one line ("Routing to sw-competitive-teardown on apple.com vs samsung.com" or "Routing to sw-page-mix on nike.com").

### Known limitations

- **No slash commands.** Every recipe is invoked by name in natural language. The router skill handles the dispatch from free-form prompts.
- **`allowed-tools` and `argument-hint` frontmatter is stripped** at build time because Claude.ai's sandbox does not honor them. The recipes still run, but tool gating is implicit (sandbox restricts whatever the skill body actually calls).
- **Description cap at 1024 chars** per skill. Build enforces this; uploads will fail if a description grows beyond the cap.
- **No HOME-scoped capability map persistence** is guaranteed across Claude.ai sessions; the probe may re-run more frequently than on CLI platforms.
- **Upload is one-at-a-time.** There is no batch import for 13 skills today; expect 13 manual uploads on first install.

### Troubleshooting

- **Upload rejected with "description too long"**: regenerate the bundle from the latest source (`python3 build.py --build`). If still over 1024, the skill author needs to shorten the frontmatter description.
- **Recipe does not fire on natural language**: confirm sw-router was uploaded and is listed in Settings > Features > Skills. Without it, free-form prompts will not auto-dispatch.
- **Recipe fires but uses unexpected tools**: Claude.ai's sandbox controls available tools at the account level, not the skill level (because `allowed-tools` is stripped). Check the connector settings.
- **MCP connector not visible**: the Similarweb MCP connector is a separate install from the skill plugin. Without the connector, every recipe will land in `mcp_not_configured` state.

---

## Cross-platform notes

### What the foundation skill assumes

- The 3 sub-foundations (`sw-foundation-core`, `sw-foundation-data`, `sw-foundation-render`) auto-load together on Similarweb-shaped keyword triggers: similarweb, web traffic, web rank, traffic and engagement, channel mix, audience overlap, market size, AEO, similar sites, PPC spend, keywords, app downloads, brand sales, category performance, or a specific Similarweb MCP tool name. All three share the same description-surface so they auto-load in lockstep. If none of these appears in the prompt, the foundations stay dormant. `sw-setup` does NOT auto-fire; it runs ONLY when invoked via `/sw-config --refresh`.
- Recipes optionally read `~/.similarweb-plugin/capabilities.json` for the capability map. The map is written by `/sw-config --refresh` (full probe) or appended to lazily by recipes when they observe access-denied at runtime. It is per-HOME (shared across all projects). Recipes do NOT require the map to run.

### Verifying end-to-end on any platform

Run all four checks in order:

1. **Visibility**: `/sw-config --show` (or natural-language equivalent) responds at all.
2. **Foundation load**: a free-form Similarweb prompt produces a router dispatch line or asks one explicit clarifier.
3. **Recipe run**: a `/sw-competitive-teardown apple.com --vs samsung.com` (or NL equivalent) produces an executive read, tables, AND a `## Sources` block.
4. **MCP wired**: the Sources block cites real Similarweb MCP tool names (e.g. `get-websites-traffic-and-engagement`), not error placeholders.

### When a smoke test fails

- If step 1 fails: the plugin did not install. Re-run the platform-specific install.
- If step 2 fails: a sub-foundation is missing or the keyword trigger did not match. Confirm `sw-foundation-core`, `sw-foundation-data`, and `sw-foundation-render` are all in the installed-skills list and use a prompt that mentions "similarweb" explicitly.
- If step 3 fails: the recipe ran but skipped the Sources block. The foundation skill did not load (recipes delegate the Sources block to foundation).
- If step 4 fails: the MCP server is not wired or `SIMILARWEB_API_KEY` is wrong. Re-check the MCP config for your platform.

### Bundle re-build

```bash
python3 build.py --validate   # exit 0 expected
python3 build.py --build      # emits all four bundles
```

`--validate` checks frontmatter, the Claude.ai 1024-char description cap, file presence, and that every `depends_on:` citation resolves to an entry in `tests/grounding-ledger.json`. CI runs `--validate` and `--build`; local re-grounding is per the CONTRIBUTING release checklist.
