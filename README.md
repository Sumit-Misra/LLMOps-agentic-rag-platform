LLMOps Agentic RAG Platform

![CI](https://github.com/Sumit-Misra/llmops-agentic-rag-platform/actions/workflows/ci.yml/badge.svg)

A stateful, self-correcting AI agent for DevOps knowledge and incident
diagnostics — it doesn't just answer questions, it critiques its own
answers against retrieved evidence and revises before responding.

Ask it *"how does a readiness probe work"* and it grounds the answer in
official Kubernetes docs. Ask it *"why would pods crash loop after a
deploy"* and it reasons over real incident postmortems instead. One
retrieval layer, two very different kinds of questions.

Results

Scored automatically on every commit, gated into CI — not a one-off claim:

| Metric | Score |
|---|---|
| Faithfulness (grounded, not hallucinated) | **0.956** |
| Answer relevancy | **0.950** |
| Context precision | **0.951** |
| Context recall | **0.975** |

A merge to `main` that drops faithfulness below 0.7 fails the build
automatically — see [`eval/run_eval.py`](eval/run_eval.py) and
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Architecture

```
                     ┌──────────────────────────────┐
                     │   FastAPI (src/api)          │
                     │   /chat endpoint             │
                     └────────────┬─────────────────┘
                                  │
                     ┌────────────▼─────────────────┐
                     │  LangGraph agent (src/agent) │
                     │  retrieve → generate →       │
                     │  critique → finalize         │
                     │  (Postgres checkpointer)     │
                     └────────────┬─────────────────┘
                                  │
                     ┌────────────▼─────────────────┐
                     │ Balanced retrieval layer     │
                     │ (src/retrieval)              │
                     └────────────┬─────────────────┘
                                  │
                     ┌────────────▼─────────────────┐
                     │ Postgres + pgvector          │
                     │ K8s docs | postmortems       │
                     └──────────────────────────────┘

   Langfuse traces every node, tracks token spend, and serves a
   versioned system prompt. Ragas scores every answer against a
   20-question golden set, gated into GitHub Actions CI.
```

**Python · LangGraph · FastAPI · PostgreSQL + pgvector · OpenAI ·
Docker Compose · Langfuse · Ragas · GitHub Actions**

Quick start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env   # add OPENAI_API_KEY, optionally Langfuse keys

docker compose up -d db
alembic upgrade head
python3 scripts/ingest.py

uvicorn src.api.main:app --reload
# -> http://localhost:8000/docs
```

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "why would pods crash loop after a deployment", "thread_id": "demo"}' \
  | python3 -m json.tool
```

Run the eval suite: `python3 eval/run_eval.py`

Project layout

`src/agent/` LangGraph state, nodes, self-correction loop, Postgres
checkpointer · `src/api/` FastAPI app · `src/retrieval/` balanced
multi-source retriever · `src/observability/` Langfuse integration ·
`src/db/` models + migrations · `eval/` golden Q&A set + Ragas runner ·
`data/raw/` source corpus (Kubernetes docs + self-authored postmortems)
