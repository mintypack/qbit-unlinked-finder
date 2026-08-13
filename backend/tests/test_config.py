from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, load_settings, validate_environment

EXAMPLE = Path(__file__).resolve().parents[2] / "config.example.toml"


def base_kwargs(tmp_path):
    dl = tmp_path / "torrents"
    dl.mkdir(exist_ok=True)
    tv = tmp_path / "tv"
    tv.mkdir(exist_ok=True)
    return {
        "qbittorrent": {"url": "http://qb:8080", "username": "admin",
                        "path_mappings": [{"from": "/downloads", "to": str(dl)}]},
        "scan": {"downloads_root": str(dl)},
        "destination_roots": [{"path": str(tv), "label": "TV"}],
        "server": {"allowed_hosts": ["testserver"]},
    }


def test_example_config_parses_and_validates():
    s = load_settings(EXAMPLE)
    assert s.scan.rescan_interval_seconds == 86400
    assert s.destination_roots[0].categories == ["movies"]
    assert s.destination_roots[1].categories == ["tv-shows"]
    assert s.qbittorrent.path_mappings[0].from_ == "/config/qBittorrent/downloads"
    assert s.qbittorrent.path_mappings[0].to == "/data/downloads"
    assert "nas.local" in s.server.allowed_hosts


def test_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("QUF_SCAN__RESCAN_INTERVAL_SECONDS", "1800")
    monkeypatch.setenv("QUF_QBITTORRENT__PASSWORD", "hunter2")
    s = Settings(**base_kwargs(tmp_path))
    assert s.scan.rescan_interval_seconds == 1800
    assert s.qbittorrent.password == "hunter2"


def test_dest_root_inside_downloads_rejected(tmp_path):
    kw = base_kwargs(tmp_path)
    inner = tmp_path / "torrents" / "media"
    inner.mkdir()
    kw["destination_roots"] = [{"path": str(inner), "label": "bad"}]
    with pytest.raises(ValidationError):
        Settings(**kw)


def test_downloads_inside_dest_root_rejected(tmp_path):
    kw = base_kwargs(tmp_path)
    kw["destination_roots"] = [{"path": str(tmp_path), "label": "bad"}]
    with pytest.raises(ValidationError):
        Settings(**kw)


def test_two_dest_roots_nesting_rejected(tmp_path):
    kw = base_kwargs(tmp_path)
    sub = tmp_path / "tv" / "sub"
    sub.mkdir()
    kw["destination_roots"].append({"path": str(sub), "label": "sub"})
    with pytest.raises(ValidationError):
        Settings(**kw)


def test_duplicate_mapping_from_rejected(tmp_path):
    kw = base_kwargs(tmp_path)
    kw["qbittorrent"]["path_mappings"].append({"from": "/downloads", "to": "/x"})
    with pytest.raises(ValidationError):
        Settings(**kw)


def test_category_claimed_twice_rejected(tmp_path):
    kw = base_kwargs(tmp_path)
    movies = tmp_path / "movies"
    movies.mkdir()
    kw["destination_roots"][0]["categories"] = ["tv"]
    kw["destination_roots"].append(
        {"path": str(movies), "label": "M", "categories": ["tv"]})
    with pytest.raises(ValidationError):
        Settings(**kw)


def test_validate_environment_missing_root(tmp_path):
    kw = base_kwargs(tmp_path)
    s = Settings(**kw)
    (tmp_path / "tv").rmdir()
    with pytest.raises(ValueError, match="not a directory"):
        validate_environment(s)
