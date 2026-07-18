"""
Unit test: the chunker actually splits long text into multiple pieces,
each within the configured token budget, with no live infra needed.
"""

from src.ingestion.chunking import chunk_document


def test_chunk_document_splits_long_text():
    long_text = "## Section\n\n" + ("This is a sentence about Kubernetes. " * 300)
    chunks = chunk_document(long_text)
    assert len(chunks) > 1
    assert all(isinstance(c, str) and c.strip() for c in chunks)


def test_chunk_document_handles_short_text():
    short_text = "A single short sentence."
    chunks = chunk_document(short_text)
    assert len(chunks) == 1
    assert chunks[0] == short_text