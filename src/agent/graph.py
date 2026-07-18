"""
Builds the agent's LangGraph:
    retrieve -> generate -> critique -> (loop back to generate, or finalize)

This is the "cyclic graph workflow that enables self-correction" piece
-- the graph literally has a cycle in it (critique -> generate), not
just a linear pipeline. finalize is a separate terminal node so only a
critique-approved answer ever gets committed to permanent conversation
history.
"""

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import (
    critique_node,
    finalize_node,
    generate_node,
    retrieve_node,
    should_revise,
)
from src.agent.state import AgentState


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("critique", critique_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "critique")
    builder.add_conditional_edges(
        "critique",
        should_revise,
        {"generate": "generate", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)