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

```bash
CAPS_PATH="$HOME/.similarweb-plugin/capabilities.json"
if [ ! -f "$CAPS_PATH" ]; then
  echo "No capability map yet. The plugin runs lazily and will discover access as recipes execute."
  echo "Run /sw-config --refresh to force a thorough probe."
  exit 0
fi
python3 - <<'PYEOF'
import json, os, collections
caps = json.load(open(os.path.expanduser("~/.similarweb-plugin/capabilities.json")))
last_updated = caps.get("last_updated") or caps.get("last_full_probe") or caps.get("probed_at", "unknown")
expires = caps.get("refresh_after", "n/a")
version = caps.get("mcp_server_version", "unknown")
state = caps.get("state", "lazy")
tools = caps.get("tools_available", {})
inaccessible = caps.get("tools_inaccessible", [])
surface = caps.get("tool_surface", {})
absent = caps.get("tools_absent", [])
legacy = not surface
legacy_absent = sorted(t for t, s in tools.items() if s is False and t not in inaccessible) if legacy else []
print(f"Similarweb MCP capabilities (last updated {last_updated}, refresh_after {expires})")
print(f"State: {state}")
if surface:
    print(f"Tool surface: {surface.get('count', '?')} tools observed {surface.get('observed_at', 'unknown')}")
if tools:
    by_cat = collections.defaultdict(lambda: [0, 0])
    for tool, status in tools.items():
        if tool in legacy_absent:
            continue
        parts = tool.split("-")
        cat = parts[1] if len(parts) > 1 and parts[0] == "get" else "other"
        by_cat[cat][1] += 1
        if status is True:
            by_cat[cat][0] += 1
    for cat in sorted(by_cat):
        accessible, total = by_cat[cat]
        suffix = ""
        if accessible == 0:
            suffix = " (denied on this plan)"
        elif accessible < total:
            suffix = " (limited plan)"
        print(f"  {cat:16s} {accessible}/{total} probed tools accessible{suffix}")
else:
    print("  (no full-probe data; lazy mode)")
if inaccessible:
    print("")
    print("Denied during recipe runs or probes (403 claims; the tool exists on the connector):")
    for t in sorted(inaccessible):
        print(f"  - {t}")
if absent or legacy_absent:
    print("")
    print("Not exposed on this connector (absent from the tool list; NOT a claims denial):")
    cur = surface.get("hash", "")
    for e in sorted(absent, key=lambda x: x.get("name", "")):
        stale = " [stale: tool surface changed; run /sw-config --refresh to re-check]" if e.get("observed_under") != cur else ""
        print(f"  - {e.get('name', '?')}{stale}")
    for t in legacy_absent:
        print(f"  - {t} [legacy record; re-checked on the next enumerating run]")
print("")
print(f"MCP server version: {version}")
PYEOF
```

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
