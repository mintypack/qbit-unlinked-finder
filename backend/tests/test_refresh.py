import asyncio
import shutil

from app.linker import LinkPatch
from app.models import LinkStatus
from app.refresh import RefreshManager
from conftest import NoQbit, make_torrent, settings_for


def test_initial_scan_publishes_index(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "A", {"f.mkv": b"a"})
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    asyncio.run(rm.run_scan())
    assert rm.scan_state == "ready"
    assert rm.index.counts["total"] == 1
    assert rm.last_scan_error is None
    assert rm.last_scan_duration is not None


def test_patch_survives_concurrent_scan(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "A", {"f.mkv": b"a"})
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    asyncio.run(rm.run_scan())

    async def race():
        task = asyncio.create_task(rm.run_scan())
        while not rm._scan_running:
            await asyncio.sleep(0)
        rm.apply_link_patch(LinkPatch(
            item_rel_path="A", file_targets={"f.mkv": str(tv / "f.mkv")}))
        await task

    asyncio.run(race())
    item = rm.index.by_rel_path["A"]
    assert item.link_status == LinkStatus.LINKED
    assert item.files[0].linked_targets == (str(tv / "f.mkv"),)


def test_patch_applies_to_current_index(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "A", {"f.mkv": b"a"})
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    asyncio.run(rm.run_scan())
    rm.apply_link_patch(LinkPatch(
        item_rel_path="A", file_targets={"f.mkv": str(tv / "f.mkv")}))
    assert rm.index.by_rel_path["A"].link_status == LinkStatus.LINKED
    assert rm.index.counts["linked"] == 1


def test_stale_mount_guard_refuses_empty_root(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "A", {"f.mkv": b"a"})
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    asyncio.run(rm.run_scan())
    shutil.rmtree(downloads / "A")
    asyncio.run(rm.run_scan())
    assert rm.index.counts["total"] == 1
    assert "stale mount" in (rm.last_scan_error or "")
    asyncio.run(rm.run_scan(force=True))
    assert rm.index.counts["total"] == 0
    assert rm.last_scan_error is None


def test_qbit_state_reflects_connection(tree):
    _, downloads, tv = tree
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    asyncio.run(rm.run_scan())
    assert rm.qbit_state == "disconnected"


def test_roots_meta_linkable(tree, monkeypatch):
    _, downloads, tv = tree
    rm = RefreshManager(settings_for(downloads, tv), NoQbit())
    metas = rm.roots_meta()
    assert metas[0]["linkable"] is True and metas[0]["reason"] is None
    monkeypatch.setattr("app.refresh._dev_of", lambda p: hash(str(p)) % 100000)
    metas = rm.roots_meta()
    assert metas[0]["linkable"] is False and "filesystem" in metas[0]["reason"]


def test_zero_interval_disables_periodic(tree):
    _, downloads, tv = tree
    settings = settings_for(downloads, tv)
    settings.scan.rescan_interval_seconds = 0
    rm = RefreshManager(settings, NoQbit())

    async def run():
        # Must return immediately instead of busy-looping
        await asyncio.wait_for(rm.periodic(), timeout=1)

    asyncio.run(run())
