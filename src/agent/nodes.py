"""
Graph nodes: retrieve -> generate -> critique -> (loop back to generate,
or finalize).

Each node is a plain async function: (AgentState) -> dict. LangGraph
merges the returned dict into the shared state between steps.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.agent.state import AgentState
from src.config import settings
from src.observability.langfuse_client import get_langfuse_client
from src.retrieval.retriever import format_chunks_for_context, retrieve_balanced

_llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key, temperature=0)

PROMPT_NAME = "devops-rag-system-prompt"

# Local fallback -- used only if Langfuse is unreachable or the prompt
# hasn't been pushed yet (see scripts/push_prompt.py). The real,
# versioned copy lives in Langfuse; this keeps the agent working even
# if that API call fails, rather than hard-erroring.
_FALLBACK_SYSTEM_PROMPT = """You are a DevOps and cloud-infrastructure knowledge assistant.
Answer ONLY using the provided context below. The context comes from two
kinds of sources: official Kubernetes documentation, and internal incident
postmortems.

Rules:
- If the context doesn't contain enough information to answer confidently,
  say so plainly instead of guessing.
- When you use a fact from the context, cite it using the [Source: ...]
  label it came with.
- Prefer postmortem sources when the question is about *why something
  would fail or break*; prefer documentation sources for *how something
  works* questions.
- Be concise and technically precise -- this is for an engineering
  audience.

Context:
{{context}}
"""


async def retrieve_node(state: AgentState) -> dict:
    last_user_message = state["messages"][-1].content
    results = await retrieve_balanced(last_user_message, k_per_source=3)
    context = format_chunks_for_context(results)
    sources = sorted({chunk.source_url or chunk.source_name for chunk, _ in results})
    return {"retrieved_context": context, "retrieved_sources": sources}


async def generate_node(state: AgentState) -> dict:
    """Produces (or revises) a draft answer. Writes to draft_answer, NOT
    messages -- the draft only becomes a permanent message once
    finalize_node commits it, so a rejected first attempt never shows
    up in the conversation the user sees."""
    try:
        prompt_client = get_langfuse_client().get_prompt(
            PROMPT_NAME, label="production", fallback=_FALLBACK_SYSTEM_PROMPT
        )
        system_text = prompt_client.compile(context=state["retrieved_context"])
    except Exception:
        # Covers both "Langfuse has no credentials configured yet" (raises
        # immediately, before the SDK's own `fallback` param even applies)
        # and any transient network/API failure -- the agent should keep
        # working either way, just without prompt versioning for that call.
        system_text = _FALLBACK_SYSTEM_PROMPT.replace(
            "{{context}}", state["retrieved_context"]
        )
    system = SystemMessage(content=system_text)
    messages = [system, *state["messages"]]

    if state.get("critique"):
        messages.append(
            HumanMessage(
                content=(
                    f"Your previous draft was: {state['draft_answer']}\n\n"
                    f"Revision feedback: {state['critique']}\n\n"
                    "Please provide a corrected answer."
                )
            )
        )

    response = await _llm.ainvoke(messages)
    return {"draft_answer": response.content}


class CritiqueResult(BaseModel):
    needs_revision: bool = Field(
        description="True if the answer contains claims not supported by the "
        "context, or fails to actually answer the question."
    )
    feedback: str = Field(
        description="If needs_revision is True, concise actionable feedback on "
        "what to fix. If False, a brief one-line confirmation."
    )


async def critique_node(state: AgentState) -> dict:
    critique_llm = _llm.with_structured_output(CritiqueResult)

    prompt = (
        "Evaluate this draft answer against the provided context.\n\n"
        f"Context:\n{state['retrieved_context']}\n\n"
        f"Question: {state['messages'][-1].content}\n\n"
        f"Draft answer: {state['draft_answer']}\n\n"
        "Does the draft answer contain claims NOT supported by the context "
        "(hallucination), or fail to actually address the question?"
    )

    result: CritiqueResult = await critique_llm.ainvoke(prompt)

    return {
        "critique": result.feedback,
        "needs_revision": result.needs_revision,
        "revision_count": state.get("revision_count", 0) + 1,
    }


async def finalize_node(state: AgentState) -> dict:
    """Commits the critique-approved draft as the real, permanent
    conversation message."""
    return {"messages": [AIMessage(content=state["draft_answer"])]}


def should_revise(state: AgentState) -> str:
    """Conditional edge: loop back to generate if the critique flagged a
    problem and we haven't hit the revision cap; otherwise finalize."""
    if state.get("needs_revision") and state.get("revision_count", 0) < state.get(
        "max_revisions", 2
    ):
        return "generate"
    return "finalize"