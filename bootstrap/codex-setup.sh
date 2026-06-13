#!/usr/bin/env bash
# Install verified Skills-hub skills into a Codex environment.
#
# Usage:
#   SKILLS_BASE_URL="https://skills-hub.web.app" ./codex-setup.sh [--full] [dest]
#
# Default installs the full verified bundle before skill enumeration. --full is
# accepted as a compatibility alias.

set -euo pipefail
PATH="/usr/bin:/bin:$PATH"

HARNESS="codex"
DEFAULT_DEST="$HOME/.codex/skills"
FULL=1
DEST=""
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFY_SCRIPT="$SCRIPT_DIR/skills_hub_verify.py"
ALLOWED_SIGNERS="${SKILLS_HUB_ALLOWED_SIGNERS:-$SCRIPT_DIR/skills_hub_allowed_signers}"

usage() {
  echo "Usage: SKILLS_BASE_URL=<base-url> $0 [--full] [dest]" >&2
}

find_python() {
  local candidate
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
      command -v "$candidate"
      return
    fi
  done
  echo "python3 or python is required for Skills-hub manifest verification" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --full)
      FULL=1
      ;;
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
ARCHIVE_NAME="skills.tar.gz"
ARCHIVE_PATH="$HARNESS/$ARCHIVE_NAME"
ARCHIVE_URL="$BASE_URL/$ARCHIVE_PATH"
MANIFEST_URL="$BASE_URL/manifest.json"
SIGNATURE_URL="$BASE_URL/manifest.json.sig"
MARKER="$DEST/.skills-hub-managed-skills"

TMP_PARENT="${TMPDIR:-/tmp}"
TMP_ROOT="$TMP_PARENT/skills-hub-bootstrap-$$-${RANDOM:-0}"
mkdir -p "$TMP_ROOT"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

MANIFEST_FILE="$TMP_ROOT/manifest.json"
SIGNATURE_FILE="$TMP_ROOT/manifest.json.sig"
ARCHIVE_FILE="$TMP_ROOT/$ARCHIVE_NAME"
MEMBERS_FILE="$TMP_ROOT/members.txt"
NEW_MARKER="$TMP_ROOT/managed-skills.txt"
CLEANUP_SET="$TMP_ROOT/cleanup-set.txt"

if ! curl -fsSL "$MANIFEST_URL" -o "$MANIFEST_FILE"; then
  echo "Failed to download $MANIFEST_URL. Existing install left unchanged." >&2
  exit 1
fi

if ! curl -fsSL "$SIGNATURE_URL" -o "$SIGNATURE_FILE"; then
  echo "Failed to download $SIGNATURE_URL. Existing install left unchanged." >&2
  exit 1
fi

if ! ssh-keygen -Y verify -f "$ALLOWED_SIGNERS" -I skills-hub-manifest -n skills-hub-manifest -s "$SIGNATURE_FILE" < "$MANIFEST_FILE" >/dev/null; then
  echo "Skills-hub manifest signature verification failed. Existing install left unchanged." >&2
  exit 1
fi

if ! curl -fsSL "$ARCHIVE_URL" -o "$ARCHIVE_FILE"; then
  echo "Failed to download $ARCHIVE_URL. Existing install left unchanged." >&2
  exit 1
fi

if ! "$PYTHON_BIN" "$VERIFY_SCRIPT" "$MANIFEST_FILE" "$ARCHIVE_PATH" "$ARCHIVE_FILE"; then
  echo "Skills-hub archive verification failed. Existing install left unchanged." >&2
  exit 1
fi

if ! tar -tzf "$ARCHIVE_FILE" > "$MEMBERS_FILE"; then
  echo "Downloaded archive from $ARCHIVE_URL is not a valid tar.gz. Existing install left unchanged." >&2
  exit 1
fi

awk -F/ 'NF > 1 && $1 != "" {print $1}' "$MEMBERS_FILE" | sort -u > "$NEW_MARKER"
if [ ! -s "$NEW_MARKER" ]; then
  echo "Archive from $ARCHIVE_URL did not contain any top-level skill directories. Existing install left unchanged." >&2
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

tar -xzf "$ARCHIVE_FILE" -C "$DEST"
cp "$NEW_MARKER" "$MARKER"

echo "Installed verified Skills-hub full skills to $DEST from $ARCHIVE_URL"
echo "Manifest signature and archive hash were verified before extraction."
