#!/usr/bin/env bash
# Install published skills into a Codex environment.
#
# Usage:
#   SKILLS_BASE_URL="https://<project-id>.web.app/<token>" ./codex-setup.sh [dest]
#
# Default destination is ~/.codex/skills — adjust to wherever your Codex
# version discovers skills. In Codex cloud environments, put the equivalent
# two lines in the environment's setup script.

set -euo pipefail

BASE_URL="${SKILLS_BASE_URL:?Set SKILLS_BASE_URL to https://<project-id>.web.app/<token>}"
DEST="${1:-$HOME/.codex/skills}"

mkdir -p "$DEST"
curl -fsSL "$BASE_URL/codex/skills.tar.gz" | tar -xz -C "$DEST"
echo "Installed skills to $DEST from $BASE_URL"
