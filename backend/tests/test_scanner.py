import os

from app.models import LinkStatus, ManagedStatus
from app.qbit_client import TorrentInfo
from app.scanner import QbitView, scan
from conftest import dest, make_torrent, scan_conf


def view(downloads, *torrents):
    return QbitView.build(list(torrents), str(downloads))


def test_flat_layout_one_item_per_torrent(tree):
    _, downloads, tv = tree
    t = make_torrent(downloads, "Show.S01", {"e1.mkv": b"a", "e2.mkv": b"b"})
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads, t))
    assert [i.rel_path for i in result.items] == ["Show.S01"]
    item = result.items[0]
    assert item.is_dir and item.file_count == 2 and item.total_size == 2
    assert item.managed_status == ManagedStatus.MANAGED


def test_category_subfolder_descends_to_torrents(tree):
    _, downloads, tv = tree
    (downloads / "tv-shows").mkdir()
    t1 = make_torrent(downloads / "tv-shows", "Show.S01", {"e1.mkv": b"a"},
                      category="tv-shows")
    t2 = make_torrent(downloads / "tv-shows", "Show.S02", {"e1.mkv": b"b"},
                      category="tv-shows")
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads, t1, t2))
    assert sorted(i.rel_path for i in result.items) == [
        "tv-shows/Show.S01", "tv-shows/Show.S02"]
    assert all(i.category == "tv-shows" for i in result.items)


def test_unmanaged_folder_stays_single_item(tree):
    _, downloads, tv = tree
    stray = downloads / "random-stuff" / "nested"
    stray.mkdir(parents=True)
    (stray / "f.bin").write_bytes(b"x")
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads))
    assert [i.rel_path for i in result.items] == ["random-stuff"]
    assert result.items[0].managed_status == ManagedStatus.UNMANAGED


def test_loose_managed_file_is_item(tree):
    _, downloads, tv = tree
    f = downloads / "old.mkv"
    f.write_bytes(b"x")
    t = TorrentInfo(name="old", category="", content_path=str(f), files=(str(f),))
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads, t))
    item = result.items[0]
    assert not item.is_dir and item.managed_status == ManagedStatus.MANAGED


def test_qbit_never_reached_gives_unknown(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "Show.S01", {"e1.mkv": b"a"})
    result = scan(scan_conf(downloads), [dest(tv)], None)
    assert result.items[0].managed_status == ManagedStatus.UNKNOWN


def test_artifacts_and_incomplete_dir_excluded(tree):
    _, downloads, tv = tree
    t = make_torrent(downloads, "Show.S01",
                     {"e1.mkv": b"a", "e2.mkv.!qB": b"x", "e3.parts": b"x"})
    inc = downloads / ".incomplete"
    inc.mkdir()
    (inc / "half.mkv").write_bytes(b"x")
    result = scan(scan_conf(downloads, incomplete=inc), [dest(tv)], view(downloads, t))
    assert [i.rel_path for i in result.items] == ["Show.S01"]
    assert result.items[0].file_count == 1


def test_folder_of_only_artifacts_is_empty(tree):
    _, downloads, tv = tree
    t = make_torrent(downloads, "Fresh", {"a.mkv.!qB": b"x"})
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads, t))
    assert result.items[0].link_status == LinkStatus.EMPTY


def test_symlinks_not_followed_and_loop_terminates(tree):
    _, downloads, tv = tree
    t = make_torrent(downloads, "Show.S01", {"e1.mkv": b"a"})
    base = downloads / "Show.S01"
    os.symlink(base, base / "loop")
    os.symlink("/etc/hostname", base / "leak.mkv")
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads, t))
    assert result.items[0].file_count == 1


def test_non_portable_name_flagged_and_sanitized(tree):
    _, downloads, tv = tree
    bad = downloads / os.fsdecode(b"bad-\xff-name")
    bad.mkdir()
    (bad / "f.bin").write_bytes(b"x")
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads))
    item = result.items[0]
    assert item.non_portable is True
    item.name.encode("utf-8")
    item.rel_path.encode("utf-8")


def test_root_file_counts_reported(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "Show.S01", {"e1.mkv": b"a"})
    (tv / "kept.mkv").write_bytes(b"y")
    result = scan(scan_conf(downloads), [dest(tv)], view(downloads))
    assert result.root_file_counts[str(downloads)] == 1
    assert result.root_file_counts[str(tv)] == 1
