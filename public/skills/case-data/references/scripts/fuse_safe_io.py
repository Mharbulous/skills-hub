#!/usr/bin/env python3
"""FUSE-safe text reads for local case-data utility scripts.

Cowork operation docs should prefer host-side Read for skill references.
This module remains available for local script/testing use where direct I/O is
supported.
"""

import errno
import mmap
import os

_ERRNO_NOT_SUPPORTED = getattr(errno, "ENOTSUP", getattr(errno, "EOPNOTSUPP", errno.EINVAL))
_DIRECT_UNSUPPORTED_ERRNOS = {
    errno.EINVAL,
    _ERRNO_NOT_SUPPORTED,
    getattr(errno, "EOPNOTSUPP", errno.EINVAL),
}


def _read_direct(path: str, chunk_size: int = 1024 * 1024) -> bytes:
    if not hasattr(os, "O_DIRECT") or not hasattr(os, "readv"):
        raise OSError(_ERRNO_NOT_SUPPORTED, "O_DIRECT/readv not available")

    flags = os.O_RDONLY | os.O_DIRECT
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    fd = os.open(path, flags)
    chunks = []
    try:
        while True:
            buf = mmap.mmap(-1, chunk_size)
            view = memoryview(buf)
            try:
                n = os.readv(fd, [view])
                if n == 0:
                    break
                chunks.append(bytes(view[:n]))
            finally:
                view.release()
                buf.close()
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_normal(path: str) -> bytes:
    with open(path, "rb") as f:
        chunks = []
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def read_text(path: str, encoding: str = "utf-8", required_markers=()) -> str:
    """Read text, preferring O_DIRECT, then require all semantic markers."""
    try:
        raw = _read_direct(path)
    except OSError as e:
        if e.errno not in _DIRECT_UNSUPPORTED_ERRNOS:
            raise
        raw = _read_normal(path)

    text = raw.decode(encoding)
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        joined = ", ".join(repr(marker) for marker in missing)
        raise RuntimeError(
            f"FUSE-safe read of {path!r} is missing required marker(s): {joined}. "
            "The file may be truncated."
        )
    return text
