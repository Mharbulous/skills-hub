#!/usr/bin/env python3
"""Recursively scan a folder for PDF files, excluding temp and hidden files."""
import os, sys
from pathlib import Path

def scan_folder(folder: str, matter_root: str) -> list:
    """Walk folder recursively, return sorted list of absolute paths to PDFs.

    Excludes files starting with '~' (Office temp files) or '.' (hidden files).
    """
    folder_path = Path(matter_root) / folder
    if not folder_path.is_dir():
        print(f"WARNING: {folder_path} is not a directory", file=sys.stderr)
        return []
    results = []
    for root, _dirs, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(".pdf") and not fname.startswith("~") and not fname.startswith("."):
                results.append(os.path.join(root, fname))
    return sorted(results)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: scan_folder.py <folder> <matter_root>", file=sys.stderr)
        sys.exit(1)
    for p in scan_folder(sys.argv[1], sys.argv[2]):
        print(p)
