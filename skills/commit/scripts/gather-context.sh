#!/usr/bin/env bash
# gather-context.sh
#
# Gathers git context for commit message drafting.
# Deterministic replacement for ad-hoc LLM bash calls.
#
# Usage:
#   gather-context.sh [--max-sample-files N]
#
# Output: JSON to stdout
#   { "branch", "has_changes", "status_porcelain", "diff_stat",
#     "sample_diffs", "recent_commits", "file_count",
#     "prev_commit_message", "prev_commit_diff_stat", "prev_commit_pushed" }

set -euo pipefail

MAX_SAMPLE=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-sample-files)
      MAX_SAMPLE="$2"
      shift 2
      ;;
    *)
      echo "{\"error\":\"Unknown argument: $1\"}"
      exit 1
      ;;
  esac
done

# --- Verify git repo ---
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo '{"error":"not a git repository"}'
  exit 1
fi

# --- Helper: escape string for JSON ---
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

# --- Branch ---
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

# --- Previous commit info ---
PREV_MSG=$(git log -1 --format="%B" 2>/dev/null || true)
PREV_DIFF_STAT=$(git diff --stat HEAD~1..HEAD 2>/dev/null || true)

# --- Is HEAD already pushed to remote? ---
REMOTE_BRANCH="origin/$BRANCH"
if git rev-parse --verify "$REMOTE_BRANCH" >/dev/null 2>&1; then
  if git merge-base --is-ancestor HEAD "$REMOTE_BRANCH" 2>/dev/null; then
    PREV_PUSHED=true
  else
    PREV_PUSHED=false
  fi
else
  PREV_PUSHED=false
fi

# --- Status ---
PORCELAIN=$(git status --porcelain 2>/dev/null || true)

if [[ -z "$PORCELAIN" ]]; then
  # No changes — early exit
  cat <<EOJSON
{"branch":"$(json_escape "$BRANCH")","has_changes":false,"status_porcelain":"","diff_stat":"","sample_diffs":"","recent_commits":[],"file_count":0,"prev_commit_message":"$(json_escape "$PREV_MSG")","prev_commit_diff_stat":"$(json_escape "$PREV_DIFF_STAT")","prev_commit_pushed":${PREV_PUSHED}}
EOJSON
  exit 0
fi

# --- File count (unique files from porcelain) ---
FILE_COUNT=$(echo "$PORCELAIN" | wc -l | tr -d ' ')

# --- Diff stat (unstaged + staged) ---
DIFF_STAT_UNSTAGED=$(git diff --stat 2>/dev/null || true)
DIFF_STAT_STAGED=$(git diff --cached --stat 2>/dev/null || true)
DIFF_STAT=""
if [[ -n "$DIFF_STAT_STAGED" && -n "$DIFF_STAT_UNSTAGED" ]]; then
  DIFF_STAT="Staged:
${DIFF_STAT_STAGED}

Unstaged:
${DIFF_STAT_UNSTAGED}"
elif [[ -n "$DIFF_STAT_STAGED" ]]; then
  DIFF_STAT="$DIFF_STAT_STAGED"
elif [[ -n "$DIFF_STAT_UNSTAGED" ]]; then
  DIFF_STAT="$DIFF_STAT_UNSTAGED"
fi

# --- Recent commits ---
RECENT_RAW=$(git log --oneline -5 2>/dev/null || true)
RECENT_JSON="["
first=true
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  if $first; then
    first=false
  else
    RECENT_JSON+=","
  fi
  RECENT_JSON+="\"$(json_escape "$line")\""
done <<< "$RECENT_RAW"
RECENT_JSON+="]"

# --- Sample diffs ---
if [[ "$FILE_COUNT" -le "$MAX_SAMPLE" ]]; then
  SAMPLE_DIFFS=$(git diff -U3 2>/dev/null || true)
  SAMPLE_STAGED=$(git diff --cached -U3 2>/dev/null || true)
  if [[ -n "$SAMPLE_STAGED" ]]; then
    SAMPLE_DIFFS="${SAMPLE_STAGED}
${SAMPLE_DIFFS}"
  fi
else
  # Get file list and limit to N files
  CHANGED_FILES=$(git diff --name-only 2>/dev/null; git diff --cached --name-only 2>/dev/null)
  CHANGED_FILES=$(echo "$CHANGED_FILES" | sort -u | head -n "$MAX_SAMPLE")
  SAMPLE_DIFFS=""
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    chunk=$(git diff -U1 -- "$f" 2>/dev/null || true)
    if [[ -z "$chunk" ]]; then
      chunk=$(git diff --cached -U1 -- "$f" 2>/dev/null || true)
    fi
    if [[ -n "$chunk" ]]; then
      SAMPLE_DIFFS+="$chunk"$'\n'
    fi
  done <<< "$CHANGED_FILES"
fi

# --- Build JSON ---
cat <<EOJSON
{"branch":"$(json_escape "$BRANCH")","has_changes":true,"status_porcelain":"$(json_escape "$PORCELAIN")","diff_stat":"$(json_escape "$DIFF_STAT")","sample_diffs":"$(json_escape "$SAMPLE_DIFFS")","recent_commits":${RECENT_JSON},"file_count":${FILE_COUNT},"prev_commit_message":"$(json_escape "$PREV_MSG")","prev_commit_diff_stat":"$(json_escape "$PREV_DIFF_STAT")","prev_commit_pushed":${PREV_PUSHED}}
EOJSON
