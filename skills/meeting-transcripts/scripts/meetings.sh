#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_DIR="$SCRIPT_DIR/../data"
INDEX_FILE="$DATA_DIR/index.jsonl"

mkdir -p "$DATA_DIR"
touch "$INDEX_FILE"

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-60
}

usage() {
  cat <<'USAGE'
Usage:
  meetings.sh save <title> <date:YYYY-MM-DD> [meeting_id]   (transcript read from stdin)
  meetings.sh list [since:YYYY-MM-DD]
  meetings.sh search <query>
  meetings.sh get <file-or-substring>
USAGE
}

cmd="${1:-}"
if [ -n "$cmd" ]; then shift; fi

case "$cmd" in
  save)
    title="$1"
    mdate="$2"
    mid="${3:-$(date +%s)}"
    if [ -z "$title" ] || [ -z "$mdate" ]; then
      usage
      exit 1
    fi

    slug=$(slugify "$title")
    file="${mdate}_${slug}.md"
    path="$DATA_DIR/$file"

    {
      echo "---"
      echo "title: $title"
      echo "date: $mdate"
      echo "meeting_id: $mid"
      echo "file: $file"
      echo "---"
      echo
      cat
    } > "$path"

    jq -nc --arg date "$mdate" --arg title "$title" --arg file "$file" --arg id "$mid" \
      '{date: $date, title: $title, file: $file, meeting_id: $id}' >> "$INDEX_FILE"

    echo "Saved: $file"
    ;;

  list)
    since="${1:-}"
    if [ -n "$since" ]; then
      jq -c --arg since "$since" 'select(.date >= $since)' "$INDEX_FILE"
    else
      cat "$INDEX_FILE"
    fi
    ;;

  search)
    query="$1"
    if [ -z "$query" ]; then
      usage
      exit 1
    fi
    find "$DATA_DIR" -maxdepth 1 -name '*.md' -type f 2>/dev/null | while read -r f; do
      if grep -qi -- "$query" "$f"; then
        base=$(basename "$f")
        jq -c --arg file "$base" 'select(.file == $file)' "$INDEX_FILE"
      fi
    done
    ;;

  get)
    file="$1"
    if [ -z "$file" ]; then
      usage
      exit 1
    fi
    match=$(find "$DATA_DIR" -maxdepth 1 -name "*${file}*" -type f | head -1)
    if [ -z "$match" ]; then
      echo "No meeting found matching: $file" >&2
      exit 1
    fi
    cat "$match"
    ;;

  *)
    usage
    exit 1
    ;;
esac
