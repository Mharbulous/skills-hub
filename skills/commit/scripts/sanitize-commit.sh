#!/usr/bin/env bash
# sanitize-commit.sh
#
# Wraps `git commit` to enforce Co-Authored-By stripping.
# Three-phase deterministic enforcement:
#   Phase 1: Check previous commit, amend if contaminated
#   Phase 2: Strip message, commit
#   Phase 3: Verify new commit, amend if contaminated
#
# Usage:
#   sanitize-commit.sh --message "commit message here" [--files "file1,file2"]
#
# If --files is omitted or "all", stages all changes (git add -A).
# If --files is provided, stages only those files.
#
# Output: JSON to stdout
#   {"status":"success","hash":"<short>","message":"<first line>"}
#   {"status":"error","reason":"<description>"}

set -euo pipefail

# --- Pattern: matches Co-Authored-By lines from any Claude model at Anthropic ---
# Case-insensitive to catch "Co-authored-by" and "Co-Authored-By"
PATTERN='[Cc]o-[Aa]uthored-[Bb]y: Claude.*noreply@anthropic\.com'

MESSAGE=""
FILES_RAW=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message)
      MESSAGE="$2"
      shift 2
      ;;
    --files)
      FILES_RAW="$2"
      shift 2
      ;;
    *)
      echo "{\"status\":\"error\",\"reason\":\"Unknown argument: $1\"}" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$MESSAGE" ]]; then
  echo '{"status":"error","reason":"--message is required"}'
  exit 1
fi

# --- Helper: strip Co-Authored-By lines and trailing blank lines from a message ---
strip_coauthored() {
  local msg="$1"
  # Remove matching lines (grep -v, case-insensitive via pattern)
  local cleaned
  cleaned=$(echo "$msg" | grep -viE "$PATTERN" || true)
  # Remove trailing blank lines
  cleaned=$(echo "$cleaned" | sed -e :a -e '/^[[:space:]]*$/{ $d; N; ba; }')
  echo "$cleaned"
}

# ============================================================
# Phase 1: Check previous commit for Co-Authored-By
# ============================================================
prev_msg=$(git log -1 --format="%B" 2>/dev/null || true)
if [[ -n "$prev_msg" ]] && echo "$prev_msg" | grep -qiE "$PATTERN"; then
  cleaned_prev=$(strip_coauthored "$prev_msg")
  git commit --amend -m "$cleaned_prev" --no-edit 2>/dev/null || \
    git commit --amend -m "$cleaned_prev" 2>/dev/null || true
fi

# ============================================================
# Phase 2: Strip message and commit
# ============================================================
cleaned_msg=$(strip_coauthored "$MESSAGE")

if [[ -z "$cleaned_msg" ]]; then
  echo '{"status":"error","reason":"Commit message is empty after stripping Co-Authored-By"}'
  exit 1
fi

# Stage files
if [[ -z "$FILES_RAW" || "$FILES_RAW" == "all" ]]; then
  git add -A
else
  IFS=',' read -ra file_list <<< "$FILES_RAW"
  for f in "${file_list[@]}"; do
    f_trimmed=$(echo "$f" | xargs)
    git add "$f_trimmed"
  done
fi

# Check there's something to commit
if git diff --cached --quiet 2>/dev/null; then
  echo '{"status":"error","reason":"Nothing staged to commit"}'
  exit 1
fi

# Commit
git commit -m "$cleaned_msg" 2>/dev/null
commit_exit=$?

if [[ $commit_exit -ne 0 ]]; then
  echo "{\"status\":\"error\",\"reason\":\"git commit failed with exit code $commit_exit\"}"
  exit 1
fi

# ============================================================
# Phase 3: Post-commit verification
# ============================================================
post_msg=$(git log -1 --format="%B")
if echo "$post_msg" | grep -qiE "$PATTERN"; then
  cleaned_post=$(strip_coauthored "$post_msg")
  git commit --amend -m "$cleaned_post" 2>/dev/null
fi

# Return success
short_hash=$(git log -1 --format="%h")
first_line=$(echo "$cleaned_msg" | head -1)
echo "{\"status\":\"success\",\"hash\":\"$short_hash\",\"message\":\"$first_line\"}"
