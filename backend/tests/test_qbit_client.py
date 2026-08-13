import pytest

from app.path_mapper import PathMapper
from app.qbit_client import QbitClient, QbitError


class FakeTorrent(dict):
    __getattr__ = dict.__getitem__


class FakeClient:
    def __init__(self):
        self.torrents = [FakeTorrent(hash="h1", name="Ubuntu", category="linux",
                                     content_path="/downloads/Ubuntu",
                                     save_path="/downloads")]
        self.files = {"h1": [FakeTorrent(name="Ubuntu/u.iso")]}
        self.maindata_rids = []
        self.fail = False

    def torrents_info(self):
        if self.fail:
            raise ConnectionError("down")
        return self.torrents

    def torrents_files(self, torrent_hash):
        return self.files[torrent_hash]

    def sync_maindata(self, rid):
        if self.fail:
            raise ConnectionError("down")
        self.maindata_rids.append(rid)
        return {"rid": rid + 1, "torrents": {"h1": {}} if rid == 0 else {}}


def make(fake):
    mapper = PathMapper([("/downloads", "/data/torrents")])
    conf = type("C", (), {"url": "", "username": "", "password": ""})()
    return QbitClient(conf, mapper, client=fake)


def test_fetch_all_maps_paths():
    qc = make(FakeClient())
    torrents = qc.fetch_all()
    assert torrents[0].content_path == "/data/torrents/Ubuntu"
    assert torrents[0].files == ("/data/torrents/Ubuntu/u.iso",)
    assert torrents[0].category == "linux"
    assert qc.connected and qc.ever_connected


def test_uncategorized_becomes_empty_string():
    fake = FakeClient()
    fake.torrents[0]["category"] = ""
    qc = make(fake)
    assert qc.fetch_all()[0].category == ""


def test_poll_tracks_rid_and_reports_changes():
    qc = make(FakeClient())
    assert qc.poll() is True
    assert qc.poll() is False


def test_error_resets_rid_and_connected():
    fake = FakeClient()
    qc = make(fake)
    qc.poll()
    fake.fail = True
    with pytest.raises(QbitError):
        qc.poll()
    assert qc.connected is False
    fake.fail = False
    qc.poll()
    assert fake.maindata_rids == [0, 0]
