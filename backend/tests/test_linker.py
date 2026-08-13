import os

import pytest

from app.index import Index
from app.linker import HardlinkRequest, Linker, LinkError
from app.scanner import QbitView, scan
from conftest import dest, make_torrent, scan_conf, settings_for


@pytest.fixture
def env(tree):
    tmp, downloads, tv = tree
    t = make_torrent(downloads, "Show.S01", {"e1.mkv": b"a", "sub/e2.mkv": b"b"})
    view = QbitView.build([t], str(downloads))
    result = scan(scan_conf(downloads), [dest(tv)], view)
    settings = settings_for(downloads, tv)
    return settings, Index.build(result.items), downloads, tv


def req(tv, subpath="Show.S01", root=None, source="Show.S01"):
    return HardlinkRequest(source_rel_path=source,
                           dest_root=root if root else str(tv), subpath=subpath)


def test_preview_plans_all_files(env):
    settings, idx, downloads, tv = env
    plan = Linker(settings).preview(req(tv), idx)
    assert plan.will_link == 2 and plan.will_skip == 0 and not plan.collisions
    assert plan.dest_path == str(tv / "Show.S01")
    actions = {f.source_rel_path: f.action for f in plan.files}
    assert actions == {"e1.mkv": "LINK", "sub/e2.mkv": "LINK"}


def test_single_file_item_links_to_dest_path(tree):
    _, downloads, tv = tree
    f = downloads / "old.mkv"
    f.write_bytes(b"x")
    from app.qbit_client import TorrentInfo
    t = TorrentInfo(name="old", category="", content_path=str(f), files=(str(f),))
    result = scan(scan_conf(downloads), [dest(tv)],
                  QbitView.build([t], str(downloads)))
    idx = Index.build(result.items)
    settings = settings_for(downloads, tv)
    plan = Linker(settings).preview(
        HardlinkRequest(source_rel_path="old.mkv", dest_root=str(tv),
                        subpath="old.mkv"), idx)
    assert plan.will_link == 1
    assert plan.files[0].dest_path == str(tv / "old.mkv")


def test_source_outside_downloads_rejected(env):
    settings, idx, downloads, tv = env
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv, source="../evil"), idx)
    assert e.value.code == "SOURCE_OUTSIDE_DOWNLOADS"


def test_unknown_item_rejected(env):
    settings, idx, downloads, tv = env
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv, source="Nope"), idx)
    assert e.value.code == "SOURCE_OUTSIDE_DOWNLOADS"


def test_unconfigured_root_rejected(env):
    settings, idx, downloads, tv = env
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv, root="/somewhere/else"), idx)
    assert e.value.code == "ROOT_NOT_CONFIGURED"


def test_subpath_traversal_rejected(env):
    settings, idx, downloads, tv = env
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv, subpath="../../escape"), idx)
    assert e.value.code == "DEST_OUTSIDE_ROOT"


def test_symlinked_subdir_escape_rejected(env, tmp_path):
    settings, idx, downloads, tv = env
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, tv / "sneaky")
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv, subpath="sneaky/Show.S01"), idx)
    assert e.value.code == "DEST_OUTSIDE_ROOT"


def test_cross_filesystem_precheck(env, monkeypatch):
    settings, idx, downloads, tv = env
    monkeypatch.setattr(
        "app.linker._dev_of",
        lambda p: 999 if str(p).startswith(str(tv)) else 1)
    with pytest.raises(LinkError) as e:
        Linker(settings).preview(req(tv), idx)
    assert e.value.code == "CROSS_FILESYSTEM"


def test_collision_listed_in_preview_same_inode_skipped(env):
    settings, idx, downloads, tv = env
    destdir = tv / "Show.S01"
    (destdir / "sub").mkdir(parents=True)
    os.link(downloads / "Show.S01" / "e1.mkv", destdir / "e1.mkv")
    (destdir / "sub" / "e2.mkv").write_bytes(b"foreign")
    plan = Linker(settings).preview(req(tv), idx)
    actions = {f.source_rel_path: f.action for f in plan.files}
    assert actions == {"e1.mkv": "SKIP", "sub/e2.mkv": "COLLISION"}
    assert plan.will_link == 0 and plan.will_skip == 1
    assert plan.collisions == (str(destdir / "sub" / "e2.mkv"),)


def test_execute_links_folder_tree(env):
    settings, idx, downloads, tv = env
    r = Linker(settings).execute(req(tv), idx)
    assert r.linked == 2 and r.skipped == 0 and r.rolled_back is False
    src = os.stat(downloads / "Show.S01" / "sub" / "e2.mkv")
    dst = os.stat(tv / "Show.S01" / "sub" / "e2.mkv")
    assert (src.st_dev, src.st_ino) == (dst.st_dev, dst.st_ino)
    assert r.patch.item_rel_path == "Show.S01"
    assert r.patch.file_targets["e1.mkv"] == str(tv / "Show.S01" / "e1.mkv")


def test_execute_completes_partial_by_skipping(env):
    settings, idx, downloads, tv = env
    linker = Linker(settings)
    linker.execute(req(tv), idx)
    r = linker.execute(req(tv), idx)
    assert r.linked == 0 and r.skipped == 2


def test_execute_refuses_collision(env):
    settings, idx, downloads, tv = env
    (tv / "Show.S01").mkdir()
    (tv / "Show.S01" / "e1.mkv").write_bytes(b"foreign")
    with pytest.raises(LinkError) as e:
        Linker(settings).execute(req(tv), idx)
    assert e.value.code == "COLLISION"
    assert not (tv / "Show.S01" / "sub").exists()


def test_exdev_mid_plan_rolls_back(env, monkeypatch):
    settings, idx, downloads, tv = env
    real_link = os.link
    calls = []

    def flaky_link(src, dst, **kw):
        calls.append(dst)
        if len(calls) == 2:
            raise OSError(18, "Invalid cross-device link")
        return real_link(src, dst, **kw)

    monkeypatch.setattr(os, "link", flaky_link)
    with pytest.raises(LinkError) as e:
        Linker(settings).execute(req(tv), idx)
    assert e.value.code == "CROSS_FILESYSTEM"
    assert e.value.rolled_back is True
    assert not (tv / "Show.S01").exists()


def test_rollback_leaves_foreign_file(env, monkeypatch):
    settings, idx, downloads, tv = env
    real_link = os.link

    def evil_link(src, dst, **kw):
        real_link(src, dst, **kw)
        if str(dst).endswith("e1.mkv"):
            os.unlink(dst)
            with open(dst, "wb") as fh:
                fh.write(b"foreign")
            raise OSError(5, "boom")

    monkeypatch.setattr(os, "link", evil_link)
    with pytest.raises(LinkError) as e:
        Linker(settings).execute(req(tv), idx)
    assert e.value.code == "LINK_FAILED"
    # Created dir cannot be removed while the foreign file sits in it
    assert e.value.rolled_back is False
    foreign = tv / "Show.S01" / "e1.mkv"
    assert foreign.read_bytes() == b"foreign"


def test_concurrent_executes_serialize(env):
    import threading as th
    settings, idx, downloads, tv = env
    linker = Linker(settings)
    results = []

    def run():
        try:
            results.append(linker.execute(req(tv), idx))
        except LinkError as err:
            results.append(err)

    threads = [th.Thread(target=run) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    oks = [r for r in results if not isinstance(r, LinkError)]
    total_linked = sum(r.linked for r in oks)
    total_skipped = sum(r.skipped for r in oks)
    assert total_linked == 2 and total_linked + total_skipped == 4
