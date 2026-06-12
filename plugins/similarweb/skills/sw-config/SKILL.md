---
name: sw-config
description: Inspect, refresh, or reset the Similarweb plugin capability map. Use when the user asks which Similarweb MCP tools they can access, wants a fresh capability probe after a plan or auth change, or wants the cached state wiped. Reads the local capabilities cache under the home directory. The map is optional; recipes run lazily without it. Also hosts the opt in Cowork only scheduled grounding sub mode that re validates fragile MCP assertions on a cadence.
---
# sw-config: inspect, refresh, or reset the capability map

**Inherits:**
- sw-foundation-core: capability map schema

User-invocable. Always produces visible output. The capability map at `~/.similarweb-plugin/capabilities.json` is an OPTIONAL append-only cache of observed access denials, plus an optional richer `tools_available` map written by `--refresh`.

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

Render the capability summary via the bundled renderer at `scripts/capmap.py` (a build-time copy of sw-foundation-core's single source), subcommand show, no stdin:

```bash
python3 scripts/capmap.py show
```

It prints the human summary, never the raw JSON: the last-updated and refresh_after header, state, tool-surface line, per-category probed-tool counts with denied-on-this-plan and limited-plan suffixes, the 403-denied list, the not-exposed list with stale-stamp and legacy markers, and the MCP server version. A missing map prints the lazy-mode hint; a corrupted map prints the reset hint. If the script file itself is missing, read the JSON directly and render the same summary shape by hand (summary only, never a raw dump), and surface one line that the plugin bundle is incomplete (reinstall to restore it).

After printing the capability summary, also render the grounding-schedule state:

```bash
python3 - <<'PYEOF'
import json, os, glob
sched_path = os.path.expanduser("~/.similarweb-plugin/grounding-schedule.json")
print("")
if os.path.isfile(sched_path):
    try:
        sched = json.load(open(sched_path))
        cadence = sched.get("cadence", "unknown")
        task_id = sched.get("task_id", "unknown")
        created = sched.get("created_at", "unknown")
        print(f"Grounding schedule: active ({cadence}, task {task_id}, created {created})")
    except (ValueError, OSError):
        print("Grounding schedule: state file unreadable; on Cowork, turn scheduled grounding off and on again to repair.")
else:
    print("Grounding schedule: not active.")
drift_dir = os.path.expanduser("~/.similarweb-plugin/")
drift_files = sorted(glob.glob(os.path.join(drift_dir, "drift-*.md")))
if drift_files:
    latest = drift_files[-1]
    print(f"Latest drift report: {latest}")
PYEOF
```

## Step B: --refresh

Apply the sw-setup skill inline (it ships in this plugin; follow its Step 1 to Step 3 directly in this conversation, or invoke it through the platform's skill mechanism if it is listed) to perform a thorough proactive probe across all 6 categories and OVERWRITE `capabilities.json` with a fresh known-state map (replacing any lazy-built append-only state). Never attempt to run sw-setup as a slash command; it has none.

```bash
CAPS_PATH="$HOME/.similarweb-plugin/capabilities.json"
if [ -f "$CAPS_PATH" ]; then
  # Move to recycle bin on Windows; on Linux/macOS use ~/.local/share/Trash/
  python3 - <<'PYEOF'
import os, sys, subprocess
path = os.path.expanduser("~/.similarweb-plugin/capabilities.json")
if sys.platform == "win32":
    subprocess.run([
        "powershell", "-NoProfile", "-Command",
        f'Add-Type -AssemblyName Microsoft.VisualBasic; '
        f'[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('
        f'"{path}", "OnlyErrorDialogs", "SendToRecycleBin")'
    ], check=False)
else:
    import shutil
    trash = os.path.expanduser("~/.local/share/Trash/files")
    os.makedirs(trash, exist_ok=True)
    shutil.move(path, os.path.join(trash, "capabilities.json"))
PYEOF
fi
```

Then follow sw-setup's probe steps. sw-setup performs the proactive probe and writes the new `capabilities.json`. After it completes, print:

```
Refreshed. <N> tools accessible across <K> categories.
```

(Compute N and K by reading the new capabilities.json.)

## Step C: --reset

`--reset` deletes `capabilities.json` without re-probing. The next recipe runs in pure lazy mode. Print:

```
Reset. Capability map cleared. Recipes will discover access lazily; run /sw-config --refresh for a thorough up-front probe.
```

## Edge cases

- **capabilities.json corrupted**: catch JSON parse error in Step A, print "Capability map is corrupted; run /sw-config --reset (then optionally --refresh)."
- **MCP server changed since last probe**: detected by `mcp_server_version` field; print one line "Note: MCP server version changed since last probe; consider /sw-config --refresh." Do not auto-refresh.
- **--reset on a clean state**: idempotent; print "Already reset."
