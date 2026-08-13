from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from rapidfuzz import fuzz, process

from .models import DownloadItem, LinkStatus, ManagedStatus, NOT_IMPORTED

NOT_LINKED = NOT_IMPORTED | {LinkStatus.PARTIAL}
SCORE_CUTOFF = 60


@dataclass(frozen=True)
class Index:
    """Immutable snapshot. Readers hold a reference, never a lock."""

    items: tuple[DownloadItem, ...]
    by_rel_path: Mapping[str, DownloadItem]
    counts: Mapping[str, int]

    @classmethod
    def build(cls, items: Sequence[DownloadItem]) -> "Index":
        items = tuple(sorted(items, key=lambda i: i.name.lower()))
        counts = {
            "total": len(items),
            "unlinked": 0, "cross_seeded": 0, "partial": 0,
            "linked": 0, "linked_elsewhere": 0, "empty": 0,
            "unmanaged": 0,
        }
        for i in items:
            counts[i.link_status.lower()] += 1
            if i.managed_status == ManagedStatus.UNMANAGED:
                counts["unmanaged"] += 1
        return cls(
            items=items,
            by_rel_path=MappingProxyType({i.rel_path: i for i in items}),
            counts=MappingProxyType(counts),
        )

    @classmethod
    def empty(cls) -> "Index":
        return cls.build(())

    def search(
        self,
        q: str = "",
        link_status: str | None = None,
        managed_status: str | None = None,
    ) -> list[DownloadItem]:
        pool: Sequence[DownloadItem] = self.items
        if link_status == "not_linked":
            pool = [i for i in pool if i.link_status in NOT_LINKED]
        elif link_status:
            pool = [i for i in pool if i.link_status == link_status]
        if managed_status:
            pool = [i for i in pool if i.managed_status == managed_status]
        if not q:
            return list(pool)
        matches = process.extract(
            q, {i: i.name for i in pool}, scorer=fuzz.WRatio,
            score_cutoff=SCORE_CUTOFF, limit=None,
        )
        return [key for _name, _score, key in matches]
