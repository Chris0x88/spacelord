#!/usr/bin/env bash
set -euo pipefail

# Archive chat history from OpenClaw sessions to a gitignored directory.
# Intended for future training data collection.
#
# Runs every hour from 9 AM to 9 PM for 5 days starting 2026-03-20.
# After 2026-03-24, self-disables.

# Date range: 2026-03-20 through 2026-03-24 (5 days inclusive)
START_DATE="2026-03-20"
END_DATE="2026-03-24"

TODAY="$(date +%Y-%m-%d)"

# If today is outside the range, exit silently (cron keeps running but no-op)
if [[ "$TODAY" < "$START_DATE" || "$TODAY" > "$END_DATE" ]]; then
  echo "Outside active date range ($START_DATE to $END_DATE). Skipping."
  exit 0
fi

ARCHIVE_BASE="$(pwd)/data/chat_archive"
SOURCE_DIR="${HOME}/.openclaw/agents/pacman/sessions"

mkdir -p "$ARCHIVE_BASE"
DATE_DIR="$ARCHIVE_BASE/$(date +%Y-%m-%d)"
mkdir -p "$DATE_DIR"

if [ -d "$SOURCE_DIR" ]; then
  # Copy all session JSONL files (preserve structure)
  cp -r "$SOURCE_DIR/." "$DATE_DIR/" 2>/dev/null || true
  echo "Archived chat sessions to $DATE_DIR"
else
  echo "Source directory not found: $SOURCE_DIR" >&2
  exit 1
fi
