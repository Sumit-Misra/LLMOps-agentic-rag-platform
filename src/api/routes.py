"""
API routes for the agent (chat endpoint, multi-turn sessions via thread_id).
"""

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from src.api.schemas import ChatRequest, ChatResponse
from src.observability.langfuse_client import get_callback_handler

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    graph = request.app.state.graph

    config = {
        "configurable": {"thread_id": payload.thread_id},
        "callbacks": [get_callback_handler()],
        # Groups every trace from this conversation together in the
        # Langfuse dashboard under one session, so a multi-turn
        # conversation reads as one coherent thread, not scattered
        # unrelated traces.
        "metadata": {"langfuse_session_id": payload.thread_id},
    }
    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=payload.message)],
                "revision_count": 0,
                "max_revisions": 2,
            },
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent failed: {exc}") from exc

    return ChatResponse(
        answer=result["messages"][-1].content,
        sources=result.get("retrieved_sources", []),
        revisions=result.get("revision_count", 0),
    )