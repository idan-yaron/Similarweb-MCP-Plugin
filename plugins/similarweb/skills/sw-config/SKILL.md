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

## Edge cases

- **capabilities.json corrupted**: catch JSON parse error in Step A, print "Capability map is corrupted; run /sw-config --reset (then optionally --refresh)."
- **MCP server changed since last probe**: detected by `mcp_server_version` field; print one line "Note: MCP server version changed since last probe; consider /sw-config --refresh." Do not auto-refresh.
- **--reset on a clean state**: idempotent; print "Already reset."
