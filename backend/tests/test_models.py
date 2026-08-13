from app.models import (
    FileEntry,
    LinkStatus,
    ManagedStatus,
    aggregate_link_status,
)


def fe(status: LinkStatus) -> FileEntry:
    return FileEntry(
        rel_path="a.mkv", size=1, dev=1, inode=1, nlink=1, link_status=status
    )


def test_statuses_serialize_as_plain_strings():
    assert LinkStatus.CROSS_SEEDED == "CROSS_SEEDED"
    assert ManagedStatus.UNKNOWN == "UNKNOWN"


def test_aggregate_empty_folder_is_empty():
    assert aggregate_link_status([]) == LinkStatus.EMPTY


def test_aggregate_partial_beats_everything():
    files = [fe(LinkStatus.UNLINKED), fe(LinkStatus.LINKED)]
    assert aggregate_link_status(files) == LinkStatus.PARTIAL
    files = [fe(LinkStatus.CROSS_SEEDED), fe(LinkStatus.LINKED_ELSEWHERE)]
    assert aggregate_link_status(files) == LinkStatus.PARTIAL


def test_aggregate_all_unlinked():
    assert aggregate_link_status([fe(LinkStatus.UNLINKED)] * 2) == LinkStatus.UNLINKED


def test_aggregate_not_imported_mix_is_cross_seeded():
    files = [fe(LinkStatus.UNLINKED), fe(LinkStatus.CROSS_SEEDED)]
    assert aggregate_link_status(files) == LinkStatus.CROSS_SEEDED


def test_aggregate_all_linked():
    assert aggregate_link_status([fe(LinkStatus.LINKED)] * 3) == LinkStatus.LINKED


def test_aggregate_linked_mix_is_linked_elsewhere():
    files = [fe(LinkStatus.LINKED), fe(LinkStatus.LINKED_ELSEWHERE)]
    assert aggregate_link_status(files) == LinkStatus.LINKED_ELSEWHERE
