"""Utility functions for handover skill."""
import re
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict


def resolve_handovers_base(repo_path: Path) -> Path:
    """Resolve handover base directory with legacy fallback.

    Primary: handovers/ (at repo root)
    Fallback: .handovers/ (legacy)

    If handovers/ exists, use it. Otherwise fall back to .handovers/.
    For new repos (neither exists), default to handovers/.
    """
    primary = repo_path / "handovers"
    legacy = repo_path / ".handovers"

    if primary.exists():
        return primary
    if legacy.exists():
        return legacy
    return primary


def detect_chains(queued_dir: Path) -> List[Dict]:
    """
    Detect handover chains in queued directory.

    A chain is a group of files with same numeric prefix and letter suffixes.
    Example: 005A_task1.md, 005B_task2.md, 005C_task3.md

    Returns list of chains, sorted by number descending.
    Each chain: {"number": "005", "files": [Path, ...]}
    """
    pattern = re.compile(r'^(\d+)([A-Z])_.*\.md$')

    # Group files by numeric prefix
    chains_map = defaultdict(list)

    for file in queued_dir.glob("*.md"):
        match = pattern.match(file.name)
        if match:
            number = match.group(1)
            letter = match.group(2)
            chains_map[number].append((letter, file))

    # Only keep groups with 2+ files (actual chains)
    chains = []
    for number, files in chains_map.items():
        if len(files) >= 2:
            # Sort by letter (A, B, C, ...)
            sorted_files = [f for _, f in sorted(files, key=lambda x: x[0])]
            chains.append({"number": number, "files": sorted_files})

    # Sort chains by number descending
    chains.sort(key=lambda c: c["number"], reverse=True)

    return chains


def sort_handovers(queued_dir: Path) -> List[Path]:
    """
    Sort handover files for processing order.

    Rules:
    - Numbers sort DESCENDING (006 → 005 → 004) - LIFO
    - Letters sort ASCENDING (A → B → C) - FIFO within number

    Returns sorted list of file paths.
    """
    pattern = re.compile(r'^(\d+)([A-Z])?_.*\.md$')

    files_with_keys = []
    for file in queued_dir.glob("*.md"):
        match = pattern.match(file.name)
        if match:
            number = int(match.group(1))
            letter = match.group(2) or ""  # Empty string for no letter
            # Sort key: (-number, letter) gives descending number, ascending letter
            files_with_keys.append(((-number, letter), file))

    files_with_keys.sort(key=lambda x: x[0])
    return [f for _, f in files_with_keys]


def generate_subagent_prompt(handover_file: Path, repo_root: Path, handovers_base: Optional[Path] = None) -> str:
    """
    Generate prompt for work subagent to process a single handover.

    The subagent gets a fresh context window and processes one handover file.
    """
    content = handover_file.read_text(encoding='utf-8')
    filename = handover_file.name

    # Resolve base path relative to repo root
    if handovers_base is None:
        handovers_base = resolve_handovers_base(repo_root)
    base_rel = str(handovers_base.relative_to(repo_root)).replace("\\", "/")

    # Relative paths for the subagent
    queued_rel = f"{base_rel}/queued"
    wip_rel = f"{base_rel}/WIP"
    completed_rel = f"{base_rel}/completed"

    prompt = f"""You are processing a single handover file with a fresh context window.

**Handover file:** {filename}

**Content:**
```markdown
{content}
```

## Instructions

1. **Move to WIP**: Move the file from `{queued_rel}/{filename}` to `{wip_rel}/{filename}`

2. **Check for required_skill**: If the YAML frontmatter contains `required_skill`, invoke that skill FIRST using the Skill tool before proceeding.

3. **Execute the handover**: Follow the instructions in the handover body. The `write_targets` field lists files you will modify. The `read_only_targets` field lists files for context only.

4. **Archive**: Move the file from `{wip_rel}/{filename}` to `{completed_rel}/{filename}`

5. **Commit archive**: Use git-agent to commit all changes with an appropriate message.

6. **Return JSON summary**: End your response with a JSON block:

```json
{{
  "status": "success",
  "files_modified": ["list", "of", "files"],
  "commit_message": "feat: description of what was done",
  "new_handovers_created": 0
}}
```

If you encounter an error you cannot resolve:

```json
{{
  "status": "failed",
  "error": "Description of what went wrong",
  "files_modified": [],
  "commit_message": null,
  "new_handovers_created": 0
}}
```

## Important

- You have a FRESH context window - no prior conversation history
- Process ONLY this handover file
- Do NOT read or process other handover files
- The orchestrator will handle the next handover after you complete
"""

    return prompt


class OrchestratorState:
    """
    Tracks cumulative state across handover chain processing.

    Designed to be minimal - only what's needed between subagent runs.
    Previous handover details are NOT stored to prevent context bloat.
    """

    def __init__(self):
        self.processed = 0
        self.succeeded = 0
        self.failed: List[str] = []  # filenames only
        self.new_handovers = 0

    def record_result(self, filename: str, result: Dict) -> None:
        """Record result from a completed subagent."""
        self.processed += 1

        if result.get("status") == "success":
            self.succeeded += 1
        else:
            self.failed.append(filename)

        self.new_handovers += result.get("new_handovers_created", 0)

    def get_summary(self) -> str:
        """Generate human-readable summary of chain processing."""
        lines = [
            f"## Chain Processing Complete",
            f"",
            f"**Processed:** {self.processed}",
            f"**Succeeded:** {self.succeeded}",
            f"**Failed:** {len(self.failed)}",
        ]

        if self.failed:
            lines.append(f"")
            lines.append(f"**Failed handovers:**")
            for filename in self.failed:
                lines.append(f"- {filename}")

        if self.new_handovers > 0:
            lines.append(f"")
            lines.append(f"**New handovers created:** {self.new_handovers}")

        return "\n".join(lines)
