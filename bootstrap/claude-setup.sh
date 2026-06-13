#!/usr/bin/env bash
# Install Skills-hub skills into a Claude Code environment.
#
# Usage:
#   SKILLS_BASE_URL="https://skills-hub.web.app" ./claude-setup.sh [dest]

set -euo pipefail
PATH="/usr/bin:/bin:$PATH"

HARNESS="claude"
DEFAULT_DEST="$HOME/.claude/skills"
DEST=""

usage() {
  echo "Usage: SKILLS_BASE_URL=<base-url> $0 [dest]" >&2
}

find_python() {
  local candidate
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
      command -v "$candidate"
      return
    fi
  done
  echo "python3 or python is required for Skills-hub index parsing" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      usage
      exit 2
      ;;
    *)
      if [ -n "$DEST" ]; then
        usage
        exit 2
      fi
      DEST="$1"
      ;;
  esac
  shift
done

PYTHON_BIN="$(find_python)"
BASE_URL="${SKILLS_BASE_URL:?Set SKILLS_BASE_URL to https://skills-hub.web.app}"
BASE_URL="${BASE_URL%/}"
DEST="${DEST:-$DEFAULT_DEST}"
MARKER="$DEST/.skills-hub-managed-skills"

TMP_PARENT="${TMPDIR:-/tmp}"
TMP_ROOT="$TMP_PARENT/skills-hub-bootstrap-$$-${RANDOM:-0}"
mkdir -p "$TMP_ROOT"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

INDEX_FILE="$TMP_ROOT/index.json"
NEW_MARKER="$TMP_ROOT/managed-skills.txt"
DOWNLOAD_LIST="$TMP_ROOT/download-list.tsv"
CLEANUP_SET="$TMP_ROOT/cleanup-set.txt"

if ! curl -fsSL "$BASE_URL/index.json" -o "$INDEX_FILE"; then
  echo "Failed to download $BASE_URL/index.json. Existing install left unchanged." >&2
  exit 1
fi

if ! "$PYTHON_BIN" - "$INDEX_FILE" "$HARNESS" "$NEW_MARKER" "$DOWNLOAD_LIST" <<'PYEOF'
import json, sys
from pathlib import Path

index_path, harness, marker_out, dl_out = sys.argv[1:]
data = json.loads(Path(index_path).read_text(encoding="utf-8"))
skills = []
rows = []
for entry in data.get("skills", []):
    name = entry["name"]
    harness_data = entry.get("harnesses", {}).get(harness)
    if not harness_data:
        continue
    skills.append(name)
    base = harness_data["base"]
    for f in harness_data.get("files", []):
        rows.append(f"{name}\t{base}\t{f}")
if not skills:
    print(f"No skills found for harness {harness!r} in index.json", file=sys.stderr)
    sys.exit(1)
with open(marker_out, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(skills) + "\n")
with open(dl_out, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(rows) + "\n")
PYEOF
then
  echo "Failed to parse index.json. Existing install left unchanged." >&2
  exit 1
fi

: > "$CLEANUP_SET"
if [ -f "$MARKER" ]; then
  sed '/^[[:space:]]*$/d' "$MARKER" >> "$CLEANUP_SET"
fi
cat "$NEW_MARKER" >> "$CLEANUP_SET"
sort -u "$CLEANUP_SET" -o "$CLEANUP_SET"

while IFS= read -r skill_name; do
  case "$skill_name" in
    ""|"."|".."|.*|*/*|*\\*)
      echo "Refusing unsafe managed skill name: $skill_name" >&2
      exit 1
      ;;
  esac
done < "$CLEANUP_SET"

mkdir -p "$DEST"

while IFS= read -r skill_name; do
  target="$DEST/$skill_name"
  if [ -d "$target" ]; then
    rm -rf "$target"
  elif [ -e "$target" ]; then
    echo "Preserving non-directory path not managed as a skill: $target" >&2
  fi
done < "$CLEANUP_SET"

while IFS=$'\t' read -r skill_name base rel_path; do
  out="$DEST/$skill_name/$rel_path"
  mkdir -p "$(dirname "$out")"
  if ! curl -fsSL "$BASE_URL/$base/$rel_path" -o "$out"; then
    echo "Failed to download $BASE_URL/$base/$rel_path." >&2
    exit 1
  fi
done < "$DOWNLOAD_LIST"

cp "$NEW_MARKER" "$MARKER"

echo "Installed Skills-hub skills to $DEST"
