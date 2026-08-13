from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class LinkStatus(StrEnum):
    UNLINKED = "UNLINKED"
    CROSS_SEEDED = "CROSS_SEEDED"
    LINKED = "LINKED"
    LINKED_ELSEWHERE = "LINKED_ELSEWHERE"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"


class ManagedStatus(StrEnum):
    MANAGED = "MANAGED"
    UNMANAGED = "UNMANAGED"
    UNKNOWN = "UNKNOWN"


NOT_IMPORTED = frozenset({LinkStatus.UNLINKED, LinkStatus.CROSS_SEEDED})


@dataclass(frozen=True, slots=True)
class FileEntry:
    rel_path: str
    size: int
    dev: int
    inode: int
    nlink: int
    link_status: LinkStatus
    linked_targets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DownloadItem:
    name: str
    rel_path: str
    is_dir: bool
    total_size: int
    file_count: int
    category: str
    managed_status: ManagedStatus
    link_status: LinkStatus
    non_portable: bool
    files: tuple[FileEntry, ...]
    added_at: int = 0


def aggregate_link_status(files: Sequence[FileEntry]) -> LinkStatus:
    # Folder aggregate precedence, first match wins
    if not files:
        return LinkStatus.EMPTY
    statuses = {f.link_status for f in files}
    not_imported = statuses & NOT_IMPORTED
    imported = statuses - NOT_IMPORTED
    if not_imported and imported:
        return LinkStatus.PARTIAL
    if statuses == {LinkStatus.UNLINKED}:
        return LinkStatus.UNLINKED
    if not imported:
        return LinkStatus.CROSS_SEEDED
    if statuses == {LinkStatus.LINKED}:
        return LinkStatus.LINKED
    return LinkStatus.LINKED_ELSEWHERE
