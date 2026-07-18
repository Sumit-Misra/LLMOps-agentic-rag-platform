"""
Vector store: low-level similarity search against document_chunks.

Uses an async SQLAlchemy engine deliberately -- this is the same
connection style the FastAPI app and LangGraph agent will use later, so
the retrieval layer plugs straight in without a sync/async mismatch.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.db.models import DocumentChunk

_engine = create_async_engine(settings.database_url)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def similarity_search(
    query_embedding: list[float],
    k: int = 5,
    source_type: str | None = None,
) -> list[tuple[DocumentChunk, float]]:
    """Return the k most semantically similar chunks to query_embedding,
    nearest first, alongside their cosine distance (0 = identical
    direction, 2 = opposite). Returning the distance (not just the
    chunk) is what lets callers merge results from multiple separate
    searches back into one correctly-ordered ranking -- see
    retrieve_balanced() in retriever.py.
    """
    async with _session_factory() as session:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = select(DocumentChunk, distance.label("distance")).order_by(distance).limit(k)
        if source_type is not None:
            stmt = stmt.where(DocumentChunk.source_type == source_type)
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]