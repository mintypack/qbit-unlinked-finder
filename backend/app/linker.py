from __future__ import annotations

import errno
import os
import threading
from collections.abc import Mapping
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
    existing_target: str | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    dest_path: str
    files: tuple[PlanFile, ...]
    will_link: int
    will_skip: int
    collisions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LinkPatch:
    item_rel_path: str
    file_targets: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ExecuteResult:
    dest_path: str
    linked: int
    skipped: int
    rolled_back: bool
    patch: LinkPatch


def _dev_of(path: Path) -> int:
    return os.stat(path).st_dev


class Linker:
    """The only module that writes to disk."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()

    def _validate(self, req: HardlinkRequest,
                  index: Index) -> tuple[DownloadItem, Path, Path, Path]:
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
        return item, source, dest, root

    def _existing_link(self, entry, src: Path, root: Path) -> str | None:
        # The scan records link targets by inode, so a file renamed for the
        # media server is still found here even though its path no longer
        # matches. Targets are re-stat'd because the snapshot can be stale.
        for target in entry.linked_targets:
            path = Path(target)
            if not path.is_relative_to(root):
                continue
            try:
                st = os.stat(path, follow_symlinks=False)
                src_st = os.stat(src, follow_symlinks=False)
            except OSError:
                continue
            if (st.st_dev, st.st_ino) == (src_st.st_dev, src_st.st_ino):
                return target
        return None

    def _plan(self, item: DownloadItem, source: Path, dest: Path,
              root: Path) -> Plan:
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
                existing = self._existing_link(f, src, root)
                if existing is not None:
                    files.append(
                        PlanFile(f.rel_path, str(target), "SKIP", existing))
                    will_skip += 1
                else:
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
        item, source, dest, root = self._validate(req, index)
        return self._plan(item, source, dest, root)

    def execute(self, req: HardlinkRequest, index: Index) -> ExecuteResult:
        with self._lock:
            # Never trust a previous preview, re-validate from scratch
            item, source, dest, root = self._validate(req, index)
            plan = self._plan(item, source, dest, root)
            if plan.collisions:
                raise LinkError("COLLISION",
                                f"existing file differs: {plan.collisions[0]}")
            created_dirs: list[Path] = []
            created_links: list[tuple[Path, tuple[int, int]]] = []
            try:
                for pf in plan.files:
                    if pf.action != "LINK":
                        continue
                    target = Path(pf.dest_path)
                    self._mkdirs(target.parent, created_dirs)
                    src = source / pf.source_rel_path if item.is_dir else source
                    st = os.stat(src, follow_symlinks=False)
                    os.link(src, target)
                    created_links.append((target, (st.st_dev, st.st_ino)))
            except OSError as exc:
                rolled_back = self._rollback(created_links, created_dirs)
                if exc.errno == errno.EXDEV:
                    raise LinkError(
                        "CROSS_FILESYSTEM",
                        "link failed with EXDEV despite matching st_dev. On union "
                        "filesystems (mergerfs, unRAID) source and destination can "
                        "land on different branches.",
                        rolled_back=rolled_back) from exc
                raise LinkError("LINK_FAILED", str(exc),
                                rolled_back=rolled_back) from exc
            targets = {pf.source_rel_path: pf.dest_path
                       for pf in plan.files if pf.action == "LINK"}
            return ExecuteResult(
                dest_path=plan.dest_path,
                linked=plan.will_link,
                skipped=plan.will_skip,
                rolled_back=False,
                patch=LinkPatch(item_rel_path=item.rel_path, file_targets=targets),
            )

    def _mkdirs(self, directory: Path, created: list[Path]) -> None:
        missing: list[Path] = []
        d = directory
        while not d.exists():
            missing.append(d)
            d = d.parent
        for d in reversed(missing):
            d.mkdir()
            created.append(d)

    def _rollback(self, links: list[tuple[Path, tuple[int, int]]],
                  dirs: list[Path]) -> bool:
        # Best effort: report failure to undo, never raise over the original
        ok = True
        for path, key in reversed(links):
            try:
                st = os.stat(path, follow_symlinks=False)
                if (st.st_dev, st.st_ino) == key:
                    os.unlink(path)
                # A foreign inode at our path is left alone
            except OSError:
                ok = False
        for d in reversed(dirs):
            try:
                d.rmdir()
            except OSError:
                ok = False
        return ok
