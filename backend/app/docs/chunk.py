"""Document chunking.

Splits raw doc text into retrieval-sized chunks. Strategy:
- Split on markdown headings (#, ##, ###) so each chunk keeps its section context.
- Cap chunk size; if a section is huge, fall back to fixed-size window splits.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    section: str
    index: int


def chunk_text(text: str, max_chars: int = 800, overlap: int = 80) -> list[Chunk]:
    lines = text.splitlines()
    chunks: list[Chunk] = []
    current_section = "intro"
    buf: list[str] = []
    idx = 0

    def flush():
        nonlocal buf, idx
        joined = "\n".join(buf).strip()
        if joined:
            chunks.append(Chunk(text=joined, section=current_section, index=idx))
            idx += 1
        buf = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # heading => new section
            flush()
            current_section = stripped.lstrip("#").strip()
            continue
        buf.append(line)
        if len("\n".join(buf)) >= max_chars:
            flush()

    flush()

    # If any chunk is still too large, split it by fixed windows with overlap.
    final: list[Chunk] = []
    fidx = 0
    for c in chunks:
        if len(c.text) <= max_chars:
            final.append(Chunk(text=c.text, section=c.section, index=fidx))
            fidx += 1
            continue
        words = c.text.split()
        start = 0
        while start < len(words):
            piece = " ".join(words[start:start + max_chars // 6])
            final.append(Chunk(text=piece, section=c.section, index=fidx))
            fidx += 1
            start += max(1, (max_chars // 6) - overlap // 6)
    return final
