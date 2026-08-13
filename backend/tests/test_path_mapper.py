from app.path_mapper import PathMapper


def test_basic_rewrite():
    m = PathMapper([("/downloads", "/data/torrents")])
    assert m.map("/downloads/Ubuntu/u.iso") == "/data/torrents/Ubuntu/u.iso"


def test_exact_match_rewrites():
    m = PathMapper([("/downloads", "/data/torrents")])
    assert m.map("/downloads") == "/data/torrents"


def test_segment_boundary_no_partial_prefix():
    m = PathMapper([("/down", "/x")])
    assert m.map("/downloads/a") == "/downloads/a"


def test_first_match_wins_longer_prefix_listed_first():
    m = PathMapper([("/downloads/iso", "/data/iso"), ("/downloads", "/data/torrents")])
    assert m.map("/downloads/iso/u.iso") == "/data/iso/u.iso"
    assert m.map("/downloads/tv/e.mkv") == "/data/torrents/tv/e.mkv"


def test_trailing_slashes_normalized():
    m = PathMapper([("/downloads/", "/data/torrents/")])
    assert m.map("/downloads/a") == "/data/torrents/a"


def test_no_match_passthrough():
    m = PathMapper([("/downloads", "/data/torrents")])
    assert m.map("/other/a") == "/other/a"
