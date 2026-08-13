from __future__ import annotations

from collections.abc import Sequence


class PathMapper:
    """Pure qBittorrent to app path translation. No I/O."""

    def __init__(self, mappings: Sequence[tuple[str, str]]) -> None:
        self._mappings = [
            (src.rstrip("/") or "/", dst.rstrip("/") or "/") for src, dst in mappings
        ]

    def map(self, path: str) -> str:
        # First mapping matching on a path segment boundary wins
        for src, dst in self._mappings:
            if path == src:
                return dst
            prefix = src if src == "/" else src + "/"
            if path.startswith(prefix):
                return dst + path[len(src):]
        return path
