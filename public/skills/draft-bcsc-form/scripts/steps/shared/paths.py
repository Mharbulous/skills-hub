"""Shared workspace output paths for BCSC form workflows."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def workspace_output_dir(matter_path: str | Path) -> Path:
    """Return the standard lawyer-facing AI output folder for a matter."""
    return Path(matter_path) / "0. DRAFT" / f"{date.today():%Y-%m-%d} AI"


def find_latest_workspace_output_dir(matter_path: str | Path) -> Path | None:
    """Return the newest standard dated AI folder under 0. DRAFT, if any."""
    draft_root = Path(matter_path) / "0. DRAFT"
    if not draft_root.exists():
        return None
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} AI$")
    candidates = sorted(
        (d for d in draft_root.iterdir() if d.is_dir() and pattern.match(d.name)),
        key=lambda d: d.name,
        reverse=True,
    )
    return candidates[0] if candidates else None
