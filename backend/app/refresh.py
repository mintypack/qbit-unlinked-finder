from __future__ import annotations

import asyncio
import os
import threading
import time
from datetime import UTC, datetime

from .config import Settings
from .index import Index
from .linker import LinkPatch
from .models import DownloadItem, FileEntry, LinkStatus, aggregate_link_status
from .qbit_client import QbitClient, QbitError
from .scanner import QbitView, scan

POLL_INTERVAL_SECONDS = 5


def _dev_of(path) -> int:
    return os.stat(path).st_dev


class RefreshManager:
    """Owns the snapshot swap. Scans run in a worker thread and publish a
    complete new Index; reference rebinding is atomic so readers never block."""

    def __init__(self, settings: Settings, qbit: QbitClient) -> None:
        self._settings = settings
        self._qbit = qbit
        self._index = Index.empty()
        self._swap_lock = threading.Lock()
        self._scan_task: asyncio.Task | None = None
        self._journal: list[LinkPatch] = []
        self._scan_running = False
        self._last_view: QbitView | None = None
        self._root_counts: dict[str, int] = {}
        self.scan_state = "scanning"
        self.last_scan_at: datetime | None = None
        self.last_scan_duration: float | None = None
        self.last_scan_error: str | None = None
        self.scan_warnings = 0

    @property
    def index(self) -> Index:
        return self._index

    @property
    def qbit_state(self) -> str:
        return "connected" if self._qbit.connected else "disconnected"

    def roots_meta(self) -> list[dict]:
        downloads_dev = _dev_of(self._settings.scan.downloads_root)
        out = []
        for r in self._settings.destination_roots:
            same = _dev_of(r.path) == downloads_dev
            out.append({
                "path": str(r.path), "label": r.label, "categories": r.categories,
                "linkable": same,
                "reason": None if same else (
                    f"{r.path} is on a different disk than the source. Hardlinks "
                    "only work within one filesystem - choose a root on the same "
                    "volume."),
            })
        return out

    async def run_scan(self, force: bool = False) -> None:
        # A rescan during a scan joins the running walk instead of queueing
        if self._scan_task is not None and not self._scan_task.done():
            await self._scan_task
            return
        self._scan_task = asyncio.ensure_future(self._do_scan(force))
        await self._scan_task

    async def _do_scan(self, force: bool) -> None:
        self.scan_state = "scanning"
        with self._swap_lock:
            self._scan_running = True
            self._journal.clear()
        started = time.monotonic()
        try:
            view = await asyncio.to_thread(self._fetch_view)
            result = await asyncio.to_thread(
                scan, self._settings.scan, self._settings.destination_roots, view)
            error = None if force else self._stale_roots(result.root_file_counts)
            if error is None:
                new_index = Index.build(result.items)
                with self._swap_lock:
                    # Re-apply patches recorded while this scan was walking,
                    # so a finishing scan cannot silently revert a hardlink
                    for patch in self._journal:
                        new_index = _patched(new_index, patch)
                    self._index = new_index
                    self._journal.clear()
                self._root_counts = dict(result.root_file_counts)
                self.scan_warnings = result.warnings
                self.last_scan_error = None
            else:
                self.last_scan_error = error
        except Exception as exc:
            self.last_scan_error = str(exc)
        finally:
            with self._swap_lock:
                self._scan_running = False
            self.last_scan_at = datetime.now(UTC)
            self.last_scan_duration = time.monotonic() - started
            self.scan_state = "ready"

    def _fetch_view(self) -> QbitView | None:
        try:
            torrents = self._qbit.fetch_all()
        except QbitError:
            # Keep the last good view while disconnected; None means never seen
            return self._last_view if self._qbit.ever_connected else None
        view = QbitView.build(torrents, str(self._settings.scan.downloads_root))
        self._last_view = view
        return view

    def _stale_roots(self, new_counts) -> str | None:
        for root, old_count in self._root_counts.items():
            if old_count > 0 and new_counts.get(root, 0) == 0:
                return (f"{root} scanned empty but previously held {old_count} "
                        "files; likely a stale mount. Old snapshot kept. Rescan "
                        "with force to accept.")
        return None

    def apply_link_patch(self, patch: LinkPatch) -> None:
        with self._swap_lock:
            self._index = _patched(self._index, patch)
            if self._scan_running:
                self._journal.append(patch)

    async def periodic(self) -> None:
        interval = self._settings.scan.rescan_interval_seconds
        while True:
            await asyncio.sleep(interval)
            await self.run_scan()

    async def poll_qbit(self) -> None:
        # A change event triggers a rescan; joining semantics prevent pileup.
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                changed = await asyncio.to_thread(self._qbit.poll)
            except QbitError:
                continue
            if changed:
                await self.run_scan()


def _patched(index: Index, patch: LinkPatch) -> Index:
    item = index.by_rel_path.get(patch.item_rel_path)
    if item is None:
        return index
    new_files = []
    for f in item.files:
        target = patch.file_targets.get(f.rel_path)
        if target is None:
            new_files.append(f)
        else:
            new_files.append(FileEntry(
                rel_path=f.rel_path, size=f.size, dev=f.dev, inode=f.inode,
                nlink=f.nlink + 1, link_status=LinkStatus.LINKED,
                linked_targets=f.linked_targets + (target,),
            ))
    new_item = DownloadItem(
        name=item.name, rel_path=item.rel_path, is_dir=item.is_dir,
        total_size=item.total_size, file_count=item.file_count,
        category=item.category, managed_status=item.managed_status,
        link_status=aggregate_link_status(new_files),
        non_portable=item.non_portable, files=tuple(new_files),
    )
    items = tuple(new_item if i.rel_path == item.rel_path else i
                  for i in index.items)
    return Index.build(items)
