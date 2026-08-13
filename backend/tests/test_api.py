import asyncio

import pytest
from fastapi.testclient import TestClient

from app.linker import Linker
from app.main import create_app
from app.refresh import RefreshManager
from conftest import NoQbit, make_torrent, settings_for


@pytest.fixture
def client(tree):
    _, downloads, tv = tree
    make_torrent(downloads, "Show.S01", {"e1.mkv": b"a"})
    settings = settings_for(downloads, tv)
    rm = RefreshManager(settings, NoQbit())
    asyncio.run(rm.run_scan())
    app = create_app(settings, rm, Linker(settings))
    return TestClient(app), downloads, tv


def test_meta_shape(client):
    c, downloads, tv = client
    body = c.get("/api/meta").json()
    assert body["scan_state"] == "ready"
    assert body["qbit_state"] == "disconnected"
    assert body["downloads_root"] == str(downloads)
    assert body["destination_roots"][0]["linkable"] is True
    assert body["destination_roots"][0]["categories"] == []
    assert set(body["counts"]) == {"total", "unlinked", "cross_seeded", "partial",
                                   "linked", "linked_elsewhere", "empty",
                                   "unmanaged"}


def test_entries_and_no_inode_leak(client):
    c, *_ = client
    items = c.get("/api/entries", params={"q": "show"}).json()["items"]
    assert items[0]["rel_path"] == "Show.S01"
    assert "dev" not in items[0] and "inode" not in items[0]
    assert "files" not in items[0]


def test_files_endpoint_with_awkward_rel_path(client):
    c, *_ = client
    files = c.get("/api/files", params={"rel_path": "Show.S01"}).json()["files"]
    assert files[0]["rel_path"] == "e1.mkv"
    assert "dev" not in files[0] and "inode" not in files[0]
    assert c.get("/api/files", params={"rel_path": "nope"}).status_code == 404
    assert c.get("/api/files",
                 params={"rel_path": "with/slash%and#hash"}).status_code == 404


def test_hardlink_preview_then_execute(client):
    c, downloads, tv = client
    body = {"source_rel_path": "Show.S01", "dest_root": str(tv),
            "subpath": "Show.S01"}
    preview = c.post("/api/hardlink/preview", json=body).json()
    assert preview["will_link"] == 1 and preview["files"][0]["action"] == "LINK"
    result = c.post("/api/hardlink", json=body).json()
    assert result["linked"] == 1 and result["rolled_back"] is False
    items = c.get("/api/entries").json()["items"]
    assert items[0]["link_status"] == "LINKED"


def test_hardlink_error_shape(client):
    c, downloads, tv = client
    body = {"source_rel_path": "../evil", "dest_root": str(tv), "subpath": "x"}
    resp = c.post("/api/hardlink/preview", json=body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "SOURCE_OUTSIDE_DOWNLOADS"


def test_rescan_returns_202_and_state(client):
    c, *_ = client
    resp = c.post("/api/rescan", json={})
    assert resp.status_code == 202
    assert resp.json()["scan_state"] in ("scanning", "ready")


def test_host_check_rejects_unknown_host(client):
    c, *_ = client
    resp = c.get("/api/meta", headers={"host": "evil.example"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN_HOST"


def test_origin_check_on_mutating_requests(client):
    c, *_ = client
    resp = c.post("/api/rescan", json={},
                  headers={"origin": "http://evil.example"})
    assert resp.status_code == 403
    resp = c.post("/api/rescan", json={},
                  headers={"origin": "http://testserver"})
    assert resp.status_code == 202
