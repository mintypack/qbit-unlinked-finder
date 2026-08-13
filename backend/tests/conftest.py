from pathlib import Path

import pytest

from app.config import DestinationRoot, ScanConfig, Settings
from app.qbit_client import QbitError, TorrentInfo


@pytest.fixture
def tree(tmp_path):
    """downloads root and one dest root on the same filesystem."""
    downloads = tmp_path / "torrents"
    tv = tmp_path / "media" / "tv"
    downloads.mkdir()
    tv.mkdir(parents=True)
    return tmp_path, downloads, tv


def make_torrent(root: Path, name: str, files: dict[str, bytes],
                 category: str = "") -> TorrentInfo:
    """Create a folder torrent on disk and its TorrentInfo."""
    base = root / name
    abs_files = []
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        abs_files.append(str(p))
    return TorrentInfo(name=name, category=category,
                       content_path=str(base), files=tuple(abs_files))


def scan_conf(downloads: Path, incomplete: Path | None = None) -> ScanConfig:
    return ScanConfig(downloads_root=downloads, incomplete_dir=incomplete)


def dest(root: Path, label: str = "TV",
         categories: list[str] | None = None) -> DestinationRoot:
    return DestinationRoot(path=root, label=label, categories=categories or [])


def settings_for(downloads: Path, tv: Path) -> Settings:
    return Settings(
        qbittorrent={"url": "", "username": ""},
        scan={"downloads_root": str(downloads)},
        destination_roots=[{"path": str(tv), "label": "TV"}],
        server={"allowed_hosts": ["testserver"]},
    )


class NoQbit:
    """Stand-in for a qBittorrent that was never reachable."""

    connected = False
    ever_connected = False
    last_error = "connection refused"

    def fetch_all(self):
        raise QbitError("down")

    def poll(self):
        raise QbitError("down")
