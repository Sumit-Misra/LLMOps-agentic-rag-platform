"""
High-level retrieval: given a user's raw question, embed it and fetch
the most relevant chunks from the vector store.
"""

import asyncio

from src.db.models import DocumentChunk
from src.ingestion.embed import embed_texts
from src.retrieval.vector_store import similarity_search


async def retrieve(
    query: str, k: int = 5, source_type: str | None = None
) -> list[tuple[DocumentChunk, float]]:
    """Flat top-k search across whichever source_type is requested (or
    all sources if None). Simple, but a numerically small source can
    get crowded out of the ranking by a much larger one -- see
    retrieve_balanced() below for the fix used by the agent.
    """
    embedding = (await asyncio.to_thread(embed_texts, [query]))[0]
    return await similarity_search(embedding, k=k, source_type=source_type)


async def retrieve_balanced(
    query: str, k_per_source: int = 3
) -> list[tuple[DocumentChunk, float]]:
    """Retrieve top results independently from each source type, then
    merge and re-sort by distance.

    This exists because a flat top-k across both sources lets the
    numerically dominant one (cloud_docs: 207 chunks) crowd out the
    smaller, often more diagnostically relevant one (postmortem: 10
    chunks) -- confirmed empirically: a query like "why would pods
    crash loop after a deployment" returned zero postmortem chunks in
    a flat top-3, even though postmortem-001 is a direct match for
    that exact scenario. Searching each source independently guarantees
    both get a fair chance to be represented.
    """
    embedding = (await asyncio.to_thread(embed_texts, [query]))[0]
    cloud = await similarity_search(embedding, k=k_per_source, source_type="cloud_docs")
    postmortems = await similarity_search(embedding, k=k_per_source, source_type="postmortem")
    combined = cloud + postmortems
    combined.sort(key=lambda pair: pair[1])  # ascending distance = most similar first
    return combined


def format_chunks_for_context(results: list[tuple[DocumentChunk, float]]) -> str:
    """Render retrieved (chunk, distance) pairs into a single text block
    suitable for an LLM prompt, with source attribution per chunk."""
    parts = []
    for chunk, _distance in results:
        label = chunk.source_url or chunk.source_name
        parts.append(f"[Source: {label}]\n{chunk.content}")
    return "\n\n---\n\n".join(parts)