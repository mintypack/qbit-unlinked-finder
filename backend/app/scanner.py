from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .config import DestinationRoot, ScanConfig
from .models import (
    DownloadItem,
    FileEntry,
    LinkStatus,
    ManagedStatus,
    aggregate_link_status,
)
from .qbit_client import TorrentInfo

ARTIFACT_SUFFIXES = (".!qB", ".parts")


def is_portable(name: str) -> bool:
    try:
        name.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def sanitize(name: str) -> str:
    return name.encode("utf-8", "replace").decode("utf-8")


@dataclass(frozen=True, slots=True)
class QbitView:
    torrent_roots: Mapping[str, TorrentInfo]
    managed_files: frozenset[str]

    @classmethod
    def build(cls, torrents: Sequence[TorrentInfo], downloads_root: str) -> "QbitView":
        root = os.path.normpath(downloads_root)
        roots: dict[str, TorrentInfo] = {}
        managed: set[str] = set()
        for t in torrents:
            managed.update(t.files)
            cp = os.path.normpath(t.content_path)
            if cp == root or cp.startswith(root + os.sep):
                roots.setdefault(cp, t)
        return cls(torrent_roots=roots, managed_files=frozenset(managed))


@dataclass(frozen=True, slots=True)
class ScanResult:
    items: tuple[DownloadItem, ...]
    warnings: int
    root_file_counts: Mapping[str, int]


class _Walker:
    """Stateful single-scan walker so counters do not thread through every call."""

    def __init__(self, conf: ScanConfig, qbit_view: QbitView | None) -> None:
        self.conf = conf
        self.view = qbit_view
        self.warnings = 0
        self.incomplete = (
            os.path.normpath(str(conf.incomplete_dir)) if conf.incomplete_dir else None
        )

    def _excluded(self, path: str, name: str) -> bool:
        if name.endswith(ARTIFACT_SUFFIXES):
            return True
        return self.incomplete is not None and os.path.normpath(path) == self.incomplete

    def _is_container(self, path: str) -> bool:
        if self.view is None:
            return False
        prefix = path + os.sep
        return any(r.startswith(prefix) for r in self.view.torrent_roots)

    def stat_files(self, path: str, rel: str = "") -> list[tuple[str, str, os.stat_result]]:
        """All regular files under path, symlinks and artifacts skipped."""
        out: list[tuple[str, str, os.stat_result]] = []
        try:
            entries = list(os.scandir(path))
        except PermissionError:
            self.warnings += 1
            return out
        except FileNotFoundError:
            return out
        for e in entries:
            child_rel = f"{rel}/{e.name}" if rel else e.name
            try:
                if e.is_symlink():
                    continue
                if self._excluded(e.path, e.name):
                    continue
                if e.is_dir(follow_symlinks=False):
                    out.extend(self.stat_files(e.path, child_rel))
                elif e.is_file(follow_symlinks=False):
                    out.append((e.path, child_rel, e.stat(follow_symlinks=False)))
            except FileNotFoundError:
                # File vanished between scandir and stat, not an error
                continue
        return out

    def enumerate_items(self, path: str, rel_prefix: str = "") -> list[tuple[str, str, bool]]:
        """Item roots as (abs_path, rel_path, is_dir) via container descent."""
        items: list[tuple[str, str, bool]] = []
        try:
            entries = list(os.scandir(path))
        except (PermissionError, FileNotFoundError):
            self.warnings += 1
            return items
        for e in entries:
            rel = f"{rel_prefix}/{e.name}" if rel_prefix else e.name
            try:
                if e.is_symlink() or self._excluded(e.path, e.name):
                    continue
                is_dir = e.is_dir(follow_symlinks=False)
            except FileNotFoundError:
                continue
            norm = os.path.normpath(e.path)
            is_torrent_root = self.view is not None and norm in self.view.torrent_roots
            if is_dir and not is_torrent_root and self._is_container(norm):
                items.extend(self.enumerate_items(e.path, rel))
            else:
                items.append((norm, rel, is_dir))
        return items


def scan(
    scan_conf: ScanConfig,
    dest_roots: Sequence[DestinationRoot],
    qbit_view: QbitView | None,
) -> ScanResult:
    walker = _Walker(scan_conf, qbit_view)
    root_counts: dict[str, int] = {}

    # Destination roots first: inode map keyed on the (st_dev, st_ino) pair,
    # single linked files dropped since they can never match a download
    dest_map: dict[tuple[int, int], list[str]] = {}
    for root in dest_roots:
        files = walker.stat_files(str(root.path))
        root_counts[str(root.path)] = len(files)
        for abs_path, _rel, st in files:
            if st.st_nlink > 1:
                dest_map.setdefault((st.st_dev, st.st_ino), []).append(abs_path)

    downloads = os.path.normpath(str(scan_conf.downloads_root))
    item_roots = walker.enumerate_items(downloads)

    # First pass over downloads: stat everything, count inode occurrences
    per_item: list[tuple[str, str, bool, list[tuple[str, str, os.stat_result]]]] = []
    downloads_paths: dict[tuple[int, int], list[str]] = {}
    total_files = 0
    for abs_path, rel, is_dir in item_roots:
        if is_dir:
            files = walker.stat_files(abs_path)
        else:
            try:
                st = os.stat(abs_path, follow_symlinks=False)
                files = [(abs_path, os.path.basename(abs_path), st)]
            except FileNotFoundError:
                files = []
        for fpath, _frel, st in files:
            downloads_paths.setdefault((st.st_dev, st.st_ino), []).append(fpath)
        total_files += len(files)
        per_item.append((abs_path, rel, is_dir, files))
    root_counts[downloads] = total_files

    items = tuple(
        _build_item(abs_path, rel, is_dir, files, dest_map, downloads_paths, qbit_view)
        for abs_path, rel, is_dir, files in per_item
    )
    return ScanResult(items=items, warnings=walker.warnings, root_file_counts=root_counts)


def _file_status(
    st: os.stat_result,
    abs_path: str,
    dest_map: Mapping[tuple[int, int], list[str]],
    downloads_paths: Mapping[tuple[int, int], list[str]],
) -> tuple[LinkStatus, tuple[str, ...]]:
    # nlink counts every hardlink including this path itself
    if st.st_nlink == 1:
        return LinkStatus.UNLINKED, ()
    key = (st.st_dev, st.st_ino)
    if key in dest_map:
        return LinkStatus.LINKED, tuple(dest_map[key])
    occurrences = downloads_paths.get(key, [])
    if st.st_nlink == len(occurrences):
        # Every link accounted for inside downloads: a cross seed
        siblings = tuple(p for p in occurrences if p != abs_path)
        return LinkStatus.CROSS_SEEDED, siblings
    return LinkStatus.LINKED_ELSEWHERE, ()


def _build_item(abs_path, rel, is_dir, files, dest_map, downloads_paths, qbit_view) -> DownloadItem:
    entries = []
    for fpath, frel, st in sorted(files, key=lambda f: f[1]):
        status, targets = _file_status(st, fpath, dest_map, downloads_paths)
        entries.append(FileEntry(
            rel_path=frel if is_portable(frel) else sanitize(frel),
            size=st.st_size, dev=st.st_dev, inode=st.st_ino,
            nlink=st.st_nlink, link_status=status, linked_targets=targets,
        ))
    name = os.path.basename(abs_path)
    added_at = 0
    if qbit_view is None:
        managed = ManagedStatus.UNKNOWN
        category = ""
    else:
        info = qbit_view.torrent_roots.get(abs_path)
        if info is not None:
            managed, category = ManagedStatus.MANAGED, info.category
            added_at = info.added_on
        elif not is_dir and abs_path in qbit_view.managed_files:
            managed, category = ManagedStatus.MANAGED, ""
        else:
            managed, category = ManagedStatus.UNMANAGED, ""
    if added_at == 0:
        # Fallback so unmanaged items still sort by age
        try:
            added_at = int(os.stat(abs_path, follow_symlinks=False).st_mtime)
        except OSError:
            added_at = 0
    portable = is_portable(rel)
    return DownloadItem(
        name=name if portable else sanitize(name),
        rel_path=rel if portable else sanitize(rel),
        is_dir=is_dir,
        total_size=sum(f.size for f in entries),
        file_count=len(entries),
        category=category,
        managed_status=managed,
        link_status=aggregate_link_status(entries),
        non_portable=not portable,
        files=tuple(entries),
        added_at=added_at,
    )
