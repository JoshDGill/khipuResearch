import pytest

from khipu import paths
from steward import fetch


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RAW", tmp_path)
    monkeypatch.setattr(paths, "MANIFEST", tmp_path / "MANIFEST.csv")
    return tmp_path


def test_manifest_roundtrip_and_verify(raw):
    f = raw / "okr" / "a.txt"
    f.parent.mkdir()
    f.write_text("hello")
    rows = {("okr", "a.txt"): fetch._record("okr", "a.txt", "u", "v1", "MIT", "ok", f)}
    fetch.save_manifest(rows)
    loaded = fetch.load_manifest()
    assert loaded == rows
    assert fetch.verify(loaded) == []
    f.write_text("tampered")
    assert any("CHECKSUM MISMATCH" in p for p in fetch.verify(loaded))


def test_failed_downloads_are_not_verified(raw):
    rows = {("kfg", "x.xlsx"): fetch._record("kfg", "x.xlsx", "u", "", "", "http_404", None)}
    assert fetch.verify(rows) == []


def test_kfg_index_parsing():
    html = '<a href="../catalog/KH0001.html">x</a><a href="catalog/KH0083B.html">'
    assert fetch.KFG_ID.findall(html) == ["KH0001", "KH0083B"]
