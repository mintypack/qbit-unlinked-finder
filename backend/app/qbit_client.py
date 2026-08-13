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


class QbitClient:
    def __init__(
        self, conf: QbitConfig, mapper: PathMapper, client: object | None = None
    ) -> None:
        self._mapper = mapper
        self._client = client or qbittorrentapi.Client(
            host=conf.url, username=conf.username, password=conf.password
        )
        self._rid = 0
        self.connected = False
        self.ever_connected = False

    def _mark_ok(self) -> None:
        self.connected = True
        self.ever_connected = True

    def _mark_fail(self, exc: Exception) -> QbitError:
        self.connected = False
        self._rid = 0
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
                ))
            self._mark_ok()
            return out
        except Exception as exc:
            raise self._mark_fail(exc) from exc

    def poll(self) -> bool:
        """Return True when the torrent set changed since the last poll."""
        try:
            data = self._client.sync_maindata(rid=self._rid)
            self._rid = data.get("rid", 0)
            self._mark_ok()
            return bool(
                data.get("full_update")
                or data.get("torrents")
                or data.get("torrents_removed")
            )
        except Exception as exc:
            raise self._mark_fail(exc) from exc
