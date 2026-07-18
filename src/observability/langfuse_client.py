"""
Langfuse client + LangGraph/LangChain instrumentation.

Langfuse's Python SDK (v3+) is OpenTelemetry-based: CallbackHandler
attaches to any LangChain/LangGraph .ainvoke() call via the `callbacks`
config key, and every LLM call, and every node inside the graph, gets
traced automatically -- no manual span code needed inside the agent
nodes themselves.
"""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from src.config import settings

_client: Langfuse | None = None
_handler: CallbackHandler | None = None


def get_langfuse_client() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _client


def get_callback_handler() -> CallbackHandler:
    """Returns a singleton CallbackHandler. Pass this in the `callbacks`
    list of any graph.ainvoke(..., config=...) call to trace it."""
    global _handler
    if _handler is None:
        get_langfuse_client()  # ensure the client is initialized first
        _handler = CallbackHandler()
    return _handler