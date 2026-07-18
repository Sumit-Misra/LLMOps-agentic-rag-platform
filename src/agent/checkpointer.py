"""
Postgres-backed checkpointer for LangGraph -- this is what gives the
agent multi-turn conversation memory across requests: state for a given
thread_id is persisted to Postgres and reloaded on the next turn.

langgraph-checkpoint-postgres manages its own tables (created via
setup()) -- see the note at the top of src/db/models.py for why those
aren't hand-defined as SQLAlchemy models here.
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import settings

# AsyncPostgresSaver wants a plain psycopg3 DSN, not a SQLAlchemy-style
# URL with a +driver suffix.
_CHECKPOINT_DB_URI = settings.database_url_sync.replace("postgresql+psycopg2://", "postgresql://")


@asynccontextmanager
async def get_checkpointer():
    """Yields a ready-to-use AsyncPostgresSaver, with its tables ensured
    to exist. Usage:

        async with get_checkpointer() as checkpointer:
            graph = build_graph(checkpointer)
            ...
    """
    async with AsyncPostgresSaver.from_conn_string(_CHECKPOINT_DB_URI) as checkpointer:
        await checkpointer.setup()
        yield checkpointer