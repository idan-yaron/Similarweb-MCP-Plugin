#!/usr/bin/env bash
set -e

if [ -z "${CLAUDE_TRANSCRIPT_PATH:-}" ]; then
  exit 0
fi

if [ ! -f "$CLAUDE_TRANSCRIPT_PATH" ]; then
  exit 0
fi

if tail -n 200 "$CLAUDE_TRANSCRIPT_PATH" 2>/dev/null | grep -q '## NEXT MOVES'; then
  printf '[similarweb-plugin] NEXT MOVES suggested, see assistant output for 2 follow-up prompts.\n'
fi

exit 0
