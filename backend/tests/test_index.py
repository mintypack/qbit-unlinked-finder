from app.index import Index
from app.models import DownloadItem, LinkStatus, ManagedStatus


def item(name, link=LinkStatus.UNLINKED, managed=ManagedStatus.MANAGED):
    return DownloadItem(name=name, rel_path=name, is_dir=True, total_size=0,
                        file_count=0, category="", managed_status=managed,
                        link_status=link, non_portable=False, files=())


ITEMS = [
    item("True.Detective.S02.720p.WEB-DL"),
    item("The.Wire.S01.1080p", link=LinkStatus.LINKED),
    item("ubuntu-24.04.iso", link=LinkStatus.CROSS_SEEDED,
         managed=ManagedStatus.UNMANAGED),
    item("Empty.Shell", link=LinkStatus.EMPTY),
]


def test_counts():
    idx = Index.build(ITEMS)
    assert idx.counts == {"total": 4, "unlinked": 1, "cross_seeded": 1, "partial": 0,
                          "linked": 1, "linked_elsewhere": 0, "empty": 1,
                          "unmanaged": 1}


def test_fuzzy_search_tolerates_typos():
    idx = Index.build(ITEMS)
    names = [i.name for i in idx.search(q="true detektive")]
    assert names[0] == "True.Detective.S02.720p.WEB-DL"


def test_no_query_returns_all_sorted():
    idx = Index.build(ITEMS)
    assert len(idx.search()) == 4


def test_status_filters():
    idx = Index.build(ITEMS)
    assert [i.name for i in idx.search(link_status="LINKED")] == ["The.Wire.S01.1080p"]
    assert [i.name for i in idx.search(managed_status="UNMANAGED")] == [
        "ubuntu-24.04.iso"]


def test_not_linked_composite_filter():
    idx = Index.build(ITEMS)
    names = {i.name for i in idx.search(link_status="not_linked")}
    assert names == {"True.Detective.S02.720p.WEB-DL", "ubuntu-24.04.iso"}


def test_by_rel_path_lookup():
    idx = Index.build(ITEMS)
    assert idx.by_rel_path["Empty.Shell"].link_status == LinkStatus.EMPTY


def test_snapshot_immutable_reader_view():
    idx = Index.build(ITEMS)
    old = idx.search()
    new_idx = Index.build(ITEMS[:1])
    assert len(old) == 4 and len(new_idx.search()) == 1
