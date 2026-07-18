"""
Agent state schema.

This is the shared object that flows through every node in the graph.
LangGraph merges each node's returned dict into this state between
steps -- `messages` uses `add_messages` so new messages append instead
of overwriting the conversation history (this is what gives us
multi-turn memory once combined with the Postgres checkpointer).

Note: `draft_answer` is deliberately separate from `messages`. Only the
final, critique-approved answer gets appended to the permanent
conversation history (by finalize_node) -- intermediate drafts that
failed critique stay internal scratch state and are never shown to the
user or persisted as a message.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

    # Populated by the retrieve node each turn
    retrieved_context: str
    retrieved_sources: list[str]

    # Scratch state for the generate<->critique loop -- not part of the
    # permanent conversation history until finalize_node commits it
    draft_answer: str
    critique: str
    needs_revision: bool

    # Loop control -- caps the retrieve->generate->critique cycle so a
    # stubborn critique can't loop forever
    revision_count: int
    max_revisions: int