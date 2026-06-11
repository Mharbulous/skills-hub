#!/usr/bin/env bash
# Install published skills into a Claude Code environment.
#
# Usage:
#   SKILLS_BASE_URL="https://<project-id>.web.app/<token>" ./claude-setup.sh [dest]
#
# In a Claude Code web/Desktop sandbox, put the equivalent two lines straight
# into the environment's setup script (and add the hosting domain to the
# environment's allowed network domains if needed):
#
#   mkdir -p ~/.claude/skills
#   curl -fsSL "$SKILLS_BASE_URL/claude/skills.tar.gz" | tar -xz -C ~/.claude/skills

set -euo pipefail

BASE_URL="${SKILLS_BASE_URL:?Set SKILLS_BASE_URL to https://<project-id>.web.app/<token>}"
DEST="${1:-$HOME/.claude/skills}"

mkdir -p "$DEST"
curl -fsSL "$BASE_URL/claude/skills.tar.gz" | tar -xz -C "$DEST"
echo "Installed skills to $DEST from $BASE_URL"
