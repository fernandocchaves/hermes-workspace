#!/bin/bash
# Hermes webhook --script filter for the meeting-transcript route.
# Runs deterministically before the agent (no LLM, no untrusted-content tool
# access needed) — saves the transcript via the meeting-transcripts skill's
# CLI, then passes the original payload through unchanged so the agent can
# still summarize it.
set -uo pipefail

SKILL_SCRIPT="/opt/data/skills/meeting-transcripts/scripts/meetings.sh"

payload=$(cat)

title=$(printf '%s' "$payload" | jq -r '.title // "Untitled Meeting"')
meeting_id=$(printf '%s' "$payload" | jq -r '.meeting_id // empty')
transcript_text=$(printf '%s' "$payload" | jq -r '.transcript_text // empty')
today=$(date +%Y-%m-%d)

if [ -n "$transcript_text" ] && [ -x "$SKILL_SCRIPT" ]; then
  # Skill script's own stdout ("Saved: ...") must not leak into our stdout —
  # only the JSON payload below may go to stdout, or templating breaks.
  printf '%s' "$transcript_text" | "$SKILL_SCRIPT" save "$title" "$today" "$meeting_id" >&2 || true
fi

printf '%s' "$payload"
