#!/usr/bin/env bash
# Install Skills-hub skills into a Codex environment.
#
# Usage:
#   SKILLS_BASE_URL="https://skills-hub.web.app" ./codex-setup.sh [dest]

set -euo pipefail
PATH="/usr/bin:/bin:$PATH"

HARNESS="codex"
DEFAULT_DEST="$HOME/.codex/skills"
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
  echo "python3 or python is required for Skills-hub manifest verification" >&2
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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERIFY_SCRIPT="${SKILLS_HUB_VERIFY_SCRIPT:-$SCRIPT_DIR/skills_hub_verify.py}"
ALLOWED_SIGNERS="${SKILLS_HUB_ALLOWED_SIGNERS:-$SCRIPT_DIR/skills_hub_allowed_signers}"

TMP_PARENT="${TMPDIR:-/tmp}"
TMP_ROOT="$TMP_PARENT/skills-hub-bootstrap-$$-${RANDOM:-0}"
mkdir -p "$TMP_ROOT"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

MANIFEST_FILE="$TMP_ROOT/manifest.json"
MANIFEST_SIG_FILE="$TMP_ROOT/manifest.json.sig"
NEW_MARKER="$TMP_ROOT/managed-skills.txt"
DOWNLOAD_LIST="$TMP_ROOT/download-list.tsv"
CLEANUP_SET="$TMP_ROOT/cleanup-set.txt"
STAGE_DIR="$TMP_ROOT/staged"

if ! curl -fsSL "$BASE_URL/manifest.json" -o "$MANIFEST_FILE"; then
  echo "Failed to download $BASE_URL/manifest.json. Existing install left unchanged." >&2
  exit 1
fi

if ! curl -fsSL "$BASE_URL/manifest.json.sig" -o "$MANIFEST_SIG_FILE"; then
  echo "Failed to download $BASE_URL/manifest.json.sig. Existing install left unchanged." >&2
  exit 1
fi

if ! "$PYTHON_BIN" - "$VERIFY_SCRIPT" "$MANIFEST_FILE" "$MANIFEST_SIG_FILE" "$ALLOWED_SIGNERS" "$HARNESS" "$NEW_MARKER" "$DOWNLOAD_LIST" <<'PYEOF'
import importlib.util
import sys
from pathlib import Path

verify_script, manifest_path, signature_path, allowed_signers, harness, marker_out, dl_out = sys.argv[1:]
spec = importlib.util.spec_from_file_location("skills_hub_verify", verify_script)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
try:
    verifier.verify_signature(Path(manifest_path), Path(signature_path), Path(allowed_signers))
    manifest = verifier.load_manifest(Path(manifest_path))
except Exception as exc:
    print(f"manifest verification failed: {exc}", file=sys.stderr)
    sys.exit(1)

def safe_name(value):
    return value and value not in {".", ".."} and not value.startswith(".") and "/" not in value and "\\" not in value

def safe_relpath(value):
    if not value or value.startswith("/") or "\\" in value:
        return False
    return all(part and part not in {".", ".."} and not part.startswith(".") for part in value.split("/"))

skills = []
rows = []
manifest_files = manifest.get("files", {})
for entry in manifest.get("skills", []):
    name = entry["name"]
    if not safe_name(name):
        print(f"Unsafe skill name in manifest: {name!r}", file=sys.stderr)
        sys.exit(1)
    harness_data = entry.get("harnesses", {}).get(harness)
    if not harness_data:
        continue
    skills.append(name)
    base = harness_data["base"]
    for f in harness_data.get("files", []):
        if not safe_relpath(f):
            print(f"Unsafe file path in manifest for {name}: {f!r}", file=sys.stderr)
            sys.exit(1)
        relpath = f"{base}/{f}"
        if relpath not in manifest_files:
            print(f"Manifest lacks file hash entry for {relpath}", file=sys.stderr)
            sys.exit(1)
        rows.append(f"{name}\t{relpath}\t{f}")
if not skills:
    print(f"No skills found for harness {harness!r} in manifest.json", file=sys.stderr)
    sys.exit(1)
with open(marker_out, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(skills) + "\n")
with open(dl_out, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(rows) + "\n")
PYEOF
then
  echo "Failed to verify or parse manifest.json. Existing install left unchanged." >&2
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

mkdir -p "$STAGE_DIR"

while IFS=$'\t' read -r skill_name manifest_rel rel_path; do
  out="$STAGE_DIR/$skill_name/$rel_path"
  mkdir -p "$(dirname "$out")"
  if ! curl -fsSL "$BASE_URL/$manifest_rel" -o "$out"; then
    echo "Failed to download $BASE_URL/$manifest_rel. Existing install left unchanged." >&2
    exit 1
  fi
  if ! "$PYTHON_BIN" "$VERIFY_SCRIPT" "$MANIFEST_FILE" "$MANIFEST_SIG_FILE" "$ALLOWED_SIGNERS" "$manifest_rel" "$out"; then
    echo "Verification failed for $manifest_rel. Existing install left unchanged." >&2
    exit 1
  fi
done < "$DOWNLOAD_LIST"

mkdir -p "$DEST"

while IFS= read -r skill_name; do
  target="$DEST/$skill_name"
  if [ -e "$target" ] && [ ! -d "$target" ]; then
    echo "Refusing to replace non-directory path: $target" >&2
    exit 1
  fi
done < "$NEW_MARKER"

while IFS= read -r skill_name; do
  target="$DEST/$skill_name"
  if [ -d "$target" ]; then
    rm -rf "$target"
  elif [ -e "$target" ]; then
    echo "Preserving non-directory path not managed as a skill: $target" >&2
  fi
done < "$CLEANUP_SET"

while IFS= read -r skill_name; do
  cp -R "$STAGE_DIR/$skill_name" "$DEST/$skill_name"
done < "$NEW_MARKER"

cp "$NEW_MARKER" "$MARKER"

echo "Installed Skills-hub skills to $DEST"
