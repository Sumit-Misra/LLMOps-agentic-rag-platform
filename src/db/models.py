"""
SQLAlchemy models.

Document chunks (+ their embeddings) live here -- this is the retrieval
layer's schema, built out fully in this step.

Multi-turn conversation memory / checkpointing (the LangGraph agent step)
does NOT get its own hand-written tables here. langgraph-checkpoint
-postgres manages its own tables automatically via its setup() call --
duplicating that schema by hand would just drift out of sync with the
library. This file only owns tables we query directly.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import settings


class Base(DeclarativeBase):
    pass


class DocumentChunk(Base):
    """One chunk of source text + its embedding.

    source_type distinguishes the two retrieval sources so we can filter
    or weight them differently at query time if needed (e.g. "give more
    weight to postmortems for diagnostic-sounding questions").
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # "cloud_docs" | "postmortem"
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g. "kubernetes-docs/pod-lifecycle.md" or "postmortem-003.md"
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.openai_embedding_dim), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # HNSW index for fast approximate cosine-similarity search.
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )