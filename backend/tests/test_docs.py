"""Tests for doc chunking + FTS5 retrieval (Day 8-9)."""

from app.docs.chunk import chunk_text
from app.docs.store import ingest, search


def test_chunk_split_on_headings():
    text = "# Auth\n\ntoken stuff\n\n## Orders\n\nsku stuff here"
    chunks = chunk_text(text)
    sections = [c.section for c in chunks]
    assert "Auth" in sections
    assert "Orders" in sections


def test_chunk_size_cap():
    big = "# Big\n" + ("word " * 5000)
    chunks = chunk_text(big, max_chars=800)
    assert all(len(c.text) <= 900 for c in chunks)
    assert len(chunks) > 1


def test_ingest_and_search(tmp_path, monkeypatch):
    # point the store DB at a temp file
    import app.docs.store as store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "docs.db")
    n = ingest("# Orders\n\nPOST with sku. Missing sku returns 400.", source="t")
    assert n >= 1
    res = search("missing sku 400")
    assert len(res) >= 1
    assert "Orders" in res[0]["section"]


def test_search_no_results_for_noise(tmp_path, monkeypatch):
    import app.docs.store as store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "docs.db")
    ingest("# Auth\n\nbearer token", source="t")
    assert search("zzzqqq nomatch term") == []
