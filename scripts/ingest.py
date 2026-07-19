"""
End-to-end ingestion: load raw docs -> chunk -> embed -> load into
document_chunks.

Run manually whenever the raw corpus in data/raw/ changes:
    python3 scripts/ingest.py

This wipes and reloads the whole table each run -- the simplest correct
behavior for a project this size. A production system would diff
instead of blowing the table away every time, but that's not needed
here.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import DocumentChunk
from src.ingestion.chunking import chunk_document
from src.ingestion.embed import embed_texts
from src.ingestion.loaders import load_all_documents


def main() -> None:
    start = time.time()
    engine = create_engine(settings.database_url_sync)

    docs = load_all_documents()
    print(f"Loaded {len(docs)} source documents")

    rows: list[tuple[str, str, str | None, int, str]] = []
    for doc in docs:
        chunks = chunk_document(doc.content)
        for idx, chunk in enumerate(chunks):
            rows.append((doc.source_type, doc.source_name, doc.source_url, idx, chunk))
    print(f"Produced {len(rows)} chunks total")

    texts = [r[4] for r in rows]
    print("Requesting embeddings from OpenAI (this calls the real API)...")
    embeddings = embed_texts(texts)
    print(f"Got {len(embeddings)} embeddings")

    with Session(engine) as session:
        session.execute(delete(DocumentChunk))
        for (source_type, source_name, source_url, idx, content), embedding in zip(
            rows, embeddings, strict=True
        ):
            session.add(
                DocumentChunk(
                    source_type=source_type,
                    source_name=source_name,
                    source_url=source_url,
                    chunk_index=idx,
                    content=content,
                    embedding=embedding,
                )
            )
        session.commit()

    elapsed = time.time() - start
    print(f"Inserted {len(rows)} chunks into document_chunks in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
