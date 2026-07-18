"""
FastAPI application entrypoint.

Builds the agent graph once at startup -- with one long-lived Postgres
checkpointer connection -- and reuses it across every request, rather
than reconnecting per-request.

Run locally with:
    uvicorn src.api.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.agent.checkpointer import get_checkpointer
from src.agent.graph import build_graph
from src.api.routes import router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with get_checkpointer() as checkpointer:
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(
    title="LLMOps Agentic RAG Platform — DevOps Knowledge & Incident Diagnostic Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app_env": settings.app_env,
    }