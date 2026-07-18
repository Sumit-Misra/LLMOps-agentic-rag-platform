"""
Evaluation harness: runs the agent against the golden Q&A set and scores
every answer with Ragas (faithfulness, answer relevancy, context
precision, context recall). Prints per-question and average scores,
writes full results to eval/eval_results.json, and exits non-zero if
the average faithfulness score drops below FAITHFULNESS_THRESHOLD --
this exit code is what Step 14 (CI gate) checks.

Run manually with:
    python3 eval/run_eval.py
"""

import asyncio
import json
import sys
import types
from pathlib import Path

# Ragas 0.4.3 unconditionally imports langchain_community.chat_models.vertexai
# at module load time. That module was removed from current
# langchain-community (split into a separate langchain-google-vertexai
# package). We never use VertexAI -- only OpenAI -- so we stub the missing
# module rather than pull in the entire unused google-cloud-aiplatform
# dependency tree just to satisfy this import.
_fake_vertexai = types.ModuleType("langchain_community.chat_models.vertexai")


class _ChatVertexAIStub:
    pass


_fake_vertexai.ChatVertexAI = _ChatVertexAIStub
sys.modules.setdefault("langchain_community.chat_models.vertexai", _fake_vertexai)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from ragas.embeddings.base import embedding_factory  # noqa: E402
from ragas.llms import llm_factory  # noqa: E402
from ragas.metrics.collections import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.agent.checkpointer import get_checkpointer  # noqa: E402
from src.agent.graph import build_graph  # noqa: E402
from src.config import settings  # noqa: E402

GOLDEN_QA_PATH = Path(__file__).resolve().parent / "golden_qa.jsonl"
RESULTS_PATH = Path(__file__).resolve().parent / "eval_results.json"

# Regression gate -- CI fails the build if this drops. Faithfulness
# (is the answer actually grounded in retrieved context, not
# hallucinated) is the metric that matters most for a RAG system, so
# it's the one wired into the CI gate; the others are tracked/reported
# but not currently gating.
FAITHFULNESS_THRESHOLD = 0.7


async def run_agent(graph, question: str, thread_id: str) -> tuple[str, list[str]]:
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=question)],
            "revision_count": 0,
            "max_revisions": 2,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    answer = result["messages"][-1].content
    # format_chunks_for_context joined chunks with this separator --
    # split back apart into individual context strings for Ragas.
    contexts = result["retrieved_context"].split("\n\n---\n\n")
    return answer, contexts


async def main() -> None:
    golden_set = [
        json.loads(line) for line in GOLDEN_QA_PATH.read_text().splitlines() if line.strip()
    ]
    print(f"Loaded {len(golden_set)} golden Q&A pairs")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    eval_llm = llm_factory(settings.openai_chat_model, client=client)
    eval_embeddings = embedding_factory(model=settings.openai_embedding_model, client=client)

    faithfulness = Faithfulness(llm=eval_llm)
    answer_relevancy = AnswerRelevancy(llm=eval_llm, embeddings=eval_embeddings)
    context_precision = ContextPrecision(llm=eval_llm)
    context_recall = ContextRecall(llm=eval_llm)

    results = []
    async with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)

        for i, item in enumerate(golden_set):
            question = item["question"]
            reference = item["reference_answer"]
            thread_id = f"eval-{i}"

            answer, contexts = await run_agent(graph, question, thread_id)

            f_score = await faithfulness.ascore(
                user_input=question, response=answer, retrieved_contexts=contexts
            )
            ar_score = await answer_relevancy.ascore(user_input=question, response=answer)
            cp_score = await context_precision.ascore(
                user_input=question, reference=reference, retrieved_contexts=contexts
            )
            cr_score = await context_recall.ascore(
                user_input=question, retrieved_contexts=contexts, reference=reference
            )

            row = {
                "question": question,
                "answer": answer,
                "faithfulness": f_score.value,
                "answer_relevancy": ar_score.value,
                "context_precision": cp_score.value,
                "context_recall": cr_score.value,
            }
            results.append(row)
            print(
                f"[{i + 1}/{len(golden_set)}] "
                f"faithfulness={row['faithfulness']:.2f} "
                f"answer_relevancy={row['answer_relevancy']:.2f} "
                f"context_precision={row['context_precision']:.2f} "
                f"context_recall={row['context_recall']:.2f}  -- {question[:60]}"
            )

    metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    avg = {k: sum(r[k] for r in results) / len(results) for k in metric_keys}

    print()
    print("=== Averages ===")
    for k, v in avg.items():
        print(f"  {k}: {v:.3f}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {RESULTS_PATH}")

    if avg["faithfulness"] < FAITHFULNESS_THRESHOLD:
        print(
            f"\nFAIL: average faithfulness {avg['faithfulness']:.3f} "
            f"is below threshold {FAITHFULNESS_THRESHOLD}"
        )
        sys.exit(1)

    print("\nPASS")


if __name__ == "__main__":
    asyncio.run(main())