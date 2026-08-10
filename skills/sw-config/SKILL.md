---
name: sw-config
description: Inspect, refresh, or reset the Similarweb plugin capability map. Use when the user asks which Similarweb MCP tools they can access, wants a fresh capability probe after a plan or auth change, or wants the cached state wiped. Reads the local capabilities cache under the home directory. The map is optional; recipes run lazily without it. Also hosts the opt in Cowork only scheduled grounding sub mode that re validates fragile MCP assertions on a cadence.
---
# sw-config: inspect, refresh, or reset the capability map

**Inherits:**
- sw-foundation-core: capability map schema

User-invocable. Always produces visible output. The capability map at `~/.similarweb-plugin/capabilities.json` is an OPTIONAL append-only cache of observed access denials, plus an optional richer `tools_available` map written by `--refresh`.

Every command below runs the bundled `scripts/capmap.py` with `python3` (use `python` if `python3` is not on PATH, e.g. on Windows). The script takes no shell features (no heredoc, no pipe), so the same command works under bash and PowerShell.

## Hard rules

- NEVER print the raw JSON. Render a human summary only.
- NEVER show user-identifying data from probe responses.
- NEVER delete via `rm` or `Remove-Item`; use the recycle-bin pattern below (project rule).

## Parse the argument

Inspect `$ARGUMENTS` (or whatever the AI client passes after `/sw-config`):
- No args or `--show` => Step A
- `--refresh` => Step B
- `--reset` => Step C
- `--schedule-grounding weekly` | `monthly` | `off` => Step D (Cowork-only)
- Anything else => print usage hint and exit

## Step A: --show (default)

**First refresh the tool-surface fingerprint, then render.** `/sw-config --show` is one of the three fingerprint triggers in sw-foundation-core § capability-map-schema, and it is the one a user reaches for precisely when they suspect the connector has changed. Rendering the summary without it reports the surface as it stood at the last write, so a connector that gained or lost tools since then still looks unchanged, and the refresh suggestion that exists to catch exactly that never fires.

Resolve the live tool list per sw-foundation-core § tool-surface presence. Only a QUALIFYING enumeration counts (a closed list meeting the sentinel quorum). When presence is UNKNOWN, skip straight to the summary below, silently and with no write; an unknown surface is not a changed one.

With a qualifying list, write ONE JSON document `{"tools": [the unqualified names], "prefix": "the observed prefix"}` to a temp file with the Write tool (cross-platform, no shell heredoc), then:

```bash
python3 scripts/capmap.py fingerprint --file <tempfile>
```

Render the refresh suggestion ONLY when it prints `changed`; `first` and `same` are silent. Never auto-probe on drift: the suggestion is the whole response, and re-probing stays user-consented. Upserting the hash here is also what re-stamps the map, so any `tools_absent` entry recorded under an older surface now renders with its stale-stamp marker in the summary rather than passing as current.

Then render the capability summary via the bundled renderer at `scripts/capmap.py` (a build-time copy of sw-foundation-core's single source), subcommand show, no stdin:

```bash
python3 scripts/capmap.py show
```

It prints the human summary, never the raw JSON: the last-updated and refresh_after header, state, tool-surface line, per-category probed-tool counts with denied-on-this-plan and limited-plan suffixes, the 403-denied list, the not-exposed list with stale-stamp and legacy markers, and the MCP server version. A missing map prints the lazy-mode hint; a corrupted map prints the reset hint. If the script file itself is missing, read the JSON directly and render the same summary shape by hand (summary only, never a raw dump), and surface one line that the plugin bundle is incomplete (reinstall to restore it).

After printing the capability summary, also render the grounding-schedule state:

```bash
python3 scripts/capmap.py sched
```

## Step B: --refresh

Apply the sw-setup skill inline (it ships in this plugin; follow its Step 1 to Step 3 directly in this conversation, or invoke it through the platform's skill mechanism if it is listed) to perform a thorough proactive probe across all 10 categories and OVERWRITE `capabilities.json` with a fresh known-state map (replacing any lazy-built append-only state). Never attempt to run sw-setup as a slash command; it has none.

NEVER clear the existing map first. `capmap.py init` writes through `os.replace`, an atomic rename over `capabilities.json`, so the previous map survives byte-intact until the replacement lands and no pre-clear is needed. Recycling before the probes means any mid-probe failure leaves the user with no map at all, which is the opposite of what a refresh promises. Recycling AFTER the write is worse, not better: a bare `capmap.py recycle` resolves to `capabilities.json` itself, so it would bin the map that was just written. `--refresh` runs no recycle at any point; only `--reset` (Step C) recycles.

Follow sw-setup's probe steps. sw-setup performs the proactive probe and writes the new `capabilities.json`. After it completes, print:

```
Refreshed. <N> tools accessible across <K> categories.
```

(Compute N and K by reading the new capabilities.json.)

## Step C: --reset

`--reset` recycles `capabilities.json` without re-probing (recycle bin / Trash, never a hard delete); the next recipe runs in pure lazy mode:

```bash
python3 scripts/capmap.py recycle
```

Print:

```
Reset. Capability map cleared. Recipes will discover access lazily; run /sw-config --refresh for a thorough up-front probe.
```

## Step D: --schedule-grounding [weekly|monthly|off] (Cowork-only)

Opt-in. Default: no schedule active. Creates a Cowork scheduled task that re-validates the 10 highest-impact grounded assertions against a rotating pool of 20 public test domains. Drift is logged locally. No notifications fire unless the user explicitly enables them in Cowork settings.

### When this sub-mode is appropriate

- After installing the plugin in Cowork for production analysis work.
- When unexplained MCP response-shape changes have appeared (e.g., a previously working tool returns null for a field a recipe expects).
- After Similarweb announces an MCP server version bump.

### What the scheduled task does

A weekly (or monthly) cron that:

1. Re-validates the 10 highest-impact grounded shape assumptions the recipes depend on, in priority order: the partial-access envelope, the auth-invalid envelope, the country-coverage-gap message (HTTP 400 form), the website-rank field set (no global_rank), the `get-website-analysis-traffic-channels` 10-channel taxonomy with absolute visits (the taxonomy includes `Gen AI`), the audience-overlap subset-row shape with absolute counts, the similar-sites exact-3-month window plus affinity field, the keywords-competitors exact-3-month window, the landing-pages single-month constraint, and the `get-website-analysis-search-spend` row shape (the `ppc_spend` field name survived the 2026-08 rename).
2. Rotates the test domain through this 20-brand public pool, diversified across 6 verticals (apparel, consumer tech, e-commerce SaaS, fintech, media/streaming, mass retail): nike.com, adidas.com, lululemon.com, underarmour.com, apple.com, samsung.com, bestbuy.com, sephora.com, shopify.com, stripe.com, payoneer.com, wise.com, revolut.com, monzo.com, spotify.com, netflix.com, amazon.com, ebay.com, walmart.com, target.com.
3. Probes each assumption's documented MCP shape via the live `similarweb` MCP server and compares against the expected shape as documented in the foundation skills (the source of truth that ships with the plugin). Resolve presence FIRST per sw-foundation-core § tool-surface presence: a probe name missing from the live enumeration is itself drift (a rename or a module gate), so record it in the drift report as an absent probe target and move on; never retry it as a call failure.
4. On drift, writes `~/.similarweb-plugin/drift-<YYYY-MM-DD>.md` containing: assertion id, observed shape, expected shape, fragility tier, and dependent recipes.
5. NO push notifications. Drift surfaces silently in `~/.similarweb-plugin/`. `--show` summarizes the most recent drift report (if any) under the capability summary.

### Implementation contract

On `--schedule-grounding weekly` or `--schedule-grounding monthly`:

1. Build a task payload: cadence ("every Monday 09:00 UTC" or "the 1st of each month 09:00 UTC") plus a natural-language probe script the Cowork agent re-interprets each fire.
2. Call `mcp__scheduled-tasks__create_scheduled_task`. If the tool is unavailable (non-Cowork runtime), abort with: `Scheduled grounding requires Cowork. Use the manual checklist in CONTRIBUTING.md instead.`
3. Write schedule metadata to `~/.similarweb-plugin/grounding-schedule.json` (`cadence`, `task_id`, `created_at`).
4. Print: `Weekly (or monthly) grounding scheduled. Drift reports will appear in ~/.similarweb-plugin/drift-<date>.md when shape changes are detected.`

On `--schedule-grounding off`:

1. Read `grounding-schedule.json`. If missing, print `No grounding schedule active.` and exit.
2. Cancel the Cowork scheduled task by `task_id`. If a cancel-style MCP tool is unavailable, instruct the user to remove the task from Cowork's scheduled-tasks UI.
3. Recycle the schedule file: `python3 scripts/capmap.py recycle grounding-schedule.json`.
4. Print `Grounding schedule canceled.`

### Failure handling

- `create_scheduled_task` returns error: render one line citing the error, then suggest a different cadence or the manual `--refresh` path.
- Cowork plugin uninstalled mid-schedule: the task survives at the Cowork level. The user cancels via `--schedule-grounding off` or Cowork's scheduled-tasks UI.
- Drift report write fails (disk full, permission): emit a stderr warning; the schedule continues to run.
- Non-Cowork runtime: abort per step 2 above. Never fall back to host-level cron, launchd, or Windows Task Scheduler; the contract is Cowork-only.

## Edge cases

- **capabilities.json corrupted**: catch JSON parse error in Step A, print "Capability map is corrupted; run /sw-config --reset (then optionally --refresh)."
- **MCP server changed since last probe**: detected by `mcp_server_version` field; print one line "Note: MCP server version changed since last probe; consider /sw-config --refresh." Do not auto-refresh.
- **--reset on a clean state**: idempotent; print "Already reset."
- **--schedule-grounding weekly when a schedule is already active**: cancel the prior task first (Step D off-path), then create the new one. Print `Replaced existing <old-cadence> schedule with <new-cadence>.` (Cowork-only)
