from __future__ import annotations

import os
from dataclasses import dataclass

import qbittorrentapi

from .config import QbitConfig
from .path_mapper import PathMapper


class QbitError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TorrentInfo:
    name: str
    category: str
    content_path: str
    files: tuple[str, ...]
    added_on: int = 0


class QbitClient:
    def __init__(
        self, conf: QbitConfig, mapper: PathMapper, client: object | None = None
    ) -> None:
        self._mapper = mapper
        self._client = client or qbittorrentapi.Client(
            host=conf.url, username=conf.username, password=conf.password
        )
        self._rid = 0
        self._known_hashes: set[str] = set()
        self.connected = False
        self.ever_connected = False
        self.last_error: str | None = None

    def _mark_ok(self) -> None:
        self.connected = True
        self.ever_connected = True
        self.last_error = None

    def _mark_fail(self, exc: Exception) -> QbitError:
        self.connected = False
        self._rid = 0
        self.last_error = str(exc)
        return QbitError(str(exc))

    def fetch_all(self) -> list[TorrentInfo]:
        try:
            out = []
            for t in self._client.torrents_info():
                files = tuple(
                    os.path.normpath(self._mapper.map(os.path.join(t.save_path, f.name)))
                    for f in self._client.torrents_files(torrent_hash=t.hash)
                )
                out.append(TorrentInfo(
                    name=t.name,
                    category=t.category or "",
                    content_path=os.path.normpath(self._mapper.map(t.content_path)),
                    files=files,
                    added_on=int(getattr(t, "added_on", 0) or 0),
                ))
            self._mark_ok()
            return out
        except Exception as exc:
            raise self._mark_fail(exc) from exc

    def poll(self) -> bool:
        """Return True when the torrent set changed since the last poll.

        Speed and progress updates arrive on every sync and must not count;
        only additions, removals, renames, and path changes matter."""
        try:
            data = self._client.sync_maindata(rid=self._rid)
            self._rid = data.get("rid", 0)
            self._mark_ok()
            if data.get("full_update"):
                self._known_hashes = set(data.get("torrents") or {})
                return True
            changed = False
            for h, fields in (data.get("torrents") or {}).items():
                if h not in self._known_hashes:
                    self._known_hashes.add(h)
                    changed = True
                elif {"save_path", "content_path", "name"} & set(fields):
                    changed = True
            for h in data.get("torrents_removed") or []:
                self._known_hashes.discard(h)
                changed = True
            return changed
        except Exception as exc:
            raise self._mark_fail(exc) from exc
