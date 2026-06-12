#!/usr/bin/env python3
"""Compute SHA-256 hex digest of a file. Returns lowercase 64-char hex string."""
import hashlib, sys

def compute_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: compute_hash.py <file_path>", file=sys.stderr)
        sys.exit(1)
    print(compute_hash(sys.argv[1]))
