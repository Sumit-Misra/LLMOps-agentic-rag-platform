"""
Pydantic request/response models for the API.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's question.")
    thread_id: str = Field(
        ...,
        description=(
            "Identifies the conversation. Reuse the same thread_id across "
            "requests to keep multi-turn memory; use a new one to start a "
            "fresh conversation."
        ),
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    revisions: int = Field(description="How many self-correction passes the answer took.")