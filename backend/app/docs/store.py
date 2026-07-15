"""Local document store (SQLite FTS5).

No pgvector/Chroma needed — FTS5 ships with Python's sqlite3 and gives real
phrase/keyword retrieval offline. Chunks are indexed; search returns ranked
matches used to build the diagnosis prompt context.

This is the MVP retrieval layer (spec §14). Swapping to a vector DB later is a
drop-in change behind `search()`.
"""

import sqlite3
from pathlib import Path

from app.docs.chunk import chunk_text

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "docs.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.execute(
        """CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            content, section, source, tokenize='porter'
        )"""
    )
    return c


def ingest(text: str, source: str = "manual") -> int:
    """Chunk + index a document. Returns number of chunks stored."""
    chunks = chunk_text(text)
    conn = _conn()
    try:
        # clear previous chunks for this source to allow re-ingest
        conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
        for ch in chunks:
            conn.execute(
                "INSERT INTO chunks(content, section, source) VALUES (?, ?, ?)",
                (ch.text, ch.section, source),
            )
        conn.commit()
        return len(chunks)
    finally:
        conn.close()


def search(query: str, limit: int = 5) -> list[dict]:
    """FTS5 MATCH search. Query terms are AND-joined for precision."""
    terms = [t for t in query.replace("/", " ").replace(":", " ").split() if len(t) > 2]
    if not terms:
        return []
    match = " AND ".join(f'"{t}"' for t in terms)
    conn = _conn()
    try:
        rows = conn.execute(
            """SELECT content, section, source, rank
               FROM chunks
               WHERE chunks MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (match, limit),
        ).fetchall()
        return [
            {"content": r[0], "section": r[1], "source": r[2], "rank": r[3]}
            for r in rows
        ]
    finally:
        conn.close()
