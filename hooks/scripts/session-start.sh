#!/usr/bin/env bash
set -e

CAPS_FILE="$HOME/.similarweb-plugin/capabilities.json"

if [ ! -f "$CAPS_FILE" ]; then
  exit 0
fi

command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$CAPS_FILE" <<'PYEOF'
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        caps = json.load(f)
except (OSError, json.JSONDecodeError):
    sys.exit(0)

if not isinstance(caps, dict):
    sys.exit(0)

state = caps.get("state") or "unknown"
version = caps.get("mcp_server_version") or "unknown"
probe = caps.get("last_full_probe") or "unknown"

print(f"[similarweb-plugin] Capability map loaded (state: {state}, MCP v{version}, last probe {probe}).")
PYEOF
