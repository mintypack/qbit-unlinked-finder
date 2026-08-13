from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from .config import Settings
from .index import Index
from .models import DownloadItem


class HardlinkRequest(BaseModel):
    source_rel_path: str
    dest_root: str
    subpath: str


class LinkError(Exception):
    def __init__(self, code: str, message: str,
                 rolled_back: bool | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.rolled_back = rolled_back


@dataclass(frozen=True, slots=True)
class PlanFile:
    source_rel_path: str
    dest_path: str
    action: str


@dataclass(frozen=True, slots=True)
class Plan:
    dest_path: str
    files: tuple[PlanFile, ...]
    will_link: int
    will_skip: int
    collisions: tuple[str, ...]


def _dev_of(path: Path) -> int:
    return os.stat(path).st_dev


class Linker:
    """The only module that writes to disk."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()

    def _validate(self, req: HardlinkRequest,
                  index: Index) -> tuple[DownloadItem, Path, Path]:
        downloads = Path(self._settings.scan.downloads_root).resolve()
        item = index.by_rel_path.get(req.source_rel_path)
        source = (downloads / req.source_rel_path).resolve()
        if item is None or item.non_portable or not source.is_relative_to(downloads):
            raise LinkError("SOURCE_OUTSIDE_DOWNLOADS",
                            f"{req.source_rel_path} is not a known download item")
        roots = {str(r.path) for r in self._settings.destination_roots}
        if req.dest_root not in roots:
            raise LinkError("ROOT_NOT_CONFIGURED",
                            f"{req.dest_root} is not a configured destination root")
        root = Path(req.dest_root).resolve()
        dest = (root / req.subpath).resolve()
        if not dest.is_relative_to(root):
            raise LinkError("DEST_OUTSIDE_ROOT", f"subpath resolves outside {root}")
        if _dev_of(source) != _dev_of(root):
            raise LinkError(
                "CROSS_FILESYSTEM",
                f"{root} is on a different filesystem than the source. "
                "Hardlinks only work within one filesystem.")
        return item, source, dest

    def _plan(self, item: DownloadItem, source: Path, dest: Path) -> Plan:
        # Collision resolution: skip same inode, refuse different inode
        files: list[PlanFile] = []
        collisions: list[str] = []
        will_link = will_skip = 0
        for f in item.files:
            src = source / f.rel_path if item.is_dir else source
            target = dest / f.rel_path if item.is_dir else dest
            try:
                st = os.stat(target, follow_symlinks=False)
            except FileNotFoundError:
                files.append(PlanFile(f.rel_path, str(target), "LINK"))
                will_link += 1
                continue
            src_st = os.stat(src, follow_symlinks=False)
            if (st.st_dev, st.st_ino) == (src_st.st_dev, src_st.st_ino):
                files.append(PlanFile(f.rel_path, str(target), "SKIP"))
                will_skip += 1
            else:
                files.append(PlanFile(f.rel_path, str(target), "COLLISION"))
                collisions.append(str(target))
        return Plan(dest_path=str(dest), files=tuple(files),
                    will_link=will_link, will_skip=will_skip,
                    collisions=tuple(collisions))

    def preview(self, req: HardlinkRequest, index: Index) -> Plan:
        item, source, dest = self._validate(req, index)
        return self._plan(item, source, dest)
