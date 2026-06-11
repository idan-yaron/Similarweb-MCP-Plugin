#!/usr/bin/env bash
set -e

# Stop hooks receive a JSON object on stdin carrying transcript_path; there is no
# CLAUDE_TRANSCRIPT_PATH env var in the hooks contract. Bounded read so the script
# cannot stall when the harness holds stdin open.
raw=""
IFS= read -r -d '' -t 2 raw 2>/dev/null || true

command -v python3 >/dev/null 2>&1 || exit 0

transcript=$(printf '%s' "$raw" | python3 -c 'import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get("transcript_path", "") if isinstance(d, dict) else "")' 2>/dev/null || true)

if [ -z "$transcript" ] || [ ! -f "$transcript" ]; then
  exit 0
fi

# Plain stdout from a Stop hook is not user-visible; systemMessage is.
if tail -n 200 "$transcript" 2>/dev/null | grep -q '## NEXT MOVES'; then
  printf '{"systemMessage": "[similarweb-plugin] NEXT MOVES suggested, see the assistant output for 2 follow-up prompts."}\n'
fi

exit 0
