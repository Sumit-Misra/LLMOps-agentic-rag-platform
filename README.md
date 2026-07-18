# Agentic Payments-Ops Compliance & Incident Diagnostic Assistant

A stateful, self-correcting agentic RAG platform for payments-operations
questions. It answers two kinds of questions over one unified retrieval
layer:

- **Compliance / reference** — "What does ISO 20022 require for a pacs.008
  message?" grounded in public Fedwire / ISO 20022 / SWIFT documentation and
  the CFPB Consumer Complaint Database.
- **Diagnostic** — "Why would a payment release fail at the settlement
  step?" grounded in a self-authored set of realistic, scrubbed incident
  postmortems.

The agent is built as a cyclic [LangGraph](https://github.com/langchain-ai/langgraph)
workflow with a retrieve → generate → self-critique → correct loop,
Postgres-backed checkpointing for multi-turn memory, full
[Langfuse](https://langfuse.com) observability, and an automated Ragas eval
suite gated into CI.

> No employer-specific or proprietary information is used anywhere in this
> project. All postmortems are original, fictional, and only inspired by
> publicly-known, general patterns in payments-settlement incidents.

## Architecture

```
                     ┌─────────────────────────┐
                     │   FastAPI (src/api)     │
                     │   chat / session routes │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │  LangGraph agent (src/agent) │
                     │  retrieve → generate →   │
                     │  critique → correct loop │
                     │  (Postgres checkpointer) │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │ Retrieval layer (src/retrieval) │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │ Postgres + pgvector      │
                     │ payments docs | CFPB     │
                     │ complaints | postmortems │
                     └──────────────────────────┘

   Langfuse (src/observability) traces every node in the graph.
   eval/run_eval.py scores the agent against a golden Q&A set with Ragas,
   gated into GitHub Actions CI.
```

## Tech stack

Python · LangGraph · FastAPI · PostgreSQL + pgvector · OpenAI (`gpt-4o-mini`
+ `text-embedding-3-small`) · Docker Compose · Langfuse · Ragas · GitHub
Actions

## Build status

- [x] **Step 1 — Repo scaffolding.** Structure, config, Docker Compose
      skeleton (db + api), tooling, CI lint/test job. *(this step)*
- [ ] **Step 2 — Data ingestion.** Pull Fedwire/ISO 20022/SWIFT docs + CFPB
      complaints, write the 15-20 postmortems, chunking.
- [ ] **Step 3 — Vector store & retrieval layer.** pgvector schema,
      embeddings, unified retriever.
- [ ] **Step 4 — LangGraph agent.** State schema, nodes, self-correction
      loop, Postgres checkpointer.
- [ ] **Step 5 — API layer.** Chat/diagnostic endpoints, session handling.
- [ ] **Step 6 — Langfuse observability.** Tracing, token spend, prompt
      versioning, dashboards.
- [ ] **Step 7 — Eval harness.** Golden Q&A set, Ragas scoring.
- [ ] **Step 8 — CI eval gate.** Wire `eval/run_eval.py` into GitHub
      Actions so a regression fails the build.
- [ ] **Step 9 — End-to-end polish.**

## Local setup

```bash
# 1. Python env + dependencies
make install-dev          # creates .venv, installs requirements-dev.txt

# 2. Configure environment
cp .env.example .env
# fill in OPENAI_API_KEY

# 3. Database (via Docker)
docker compose up -d db

# 4. Run the API
make run                  # http://localhost:8000/health

# 5. Tests
make test
```

Or run everything in containers:

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

## Project structure

```
src/
  agent/          LangGraph state, nodes, graph, checkpointer      (Step 4)
  api/             FastAPI app, routes, schemas                     (Step 5)
  ingestion/      Loaders, chunking, embedding for all 3 sources   (Step 2)
  retrieval/      pgvector store + unified retriever                (Step 3)
  observability/  Langfuse client/instrumentation                  (Step 6)
  db/             SQLAlchemy models + Alembic migrations            (Step 3)
  config.py       Central pydantic-settings config
data/
  raw/            payments_docs/, cfpb_complaints/, postmortems/
  processed/      Chunked/cleaned docs ready for embedding
eval/
  golden_qa.jsonl Golden Q&A set for Ragas scoring                  (Step 7)
  run_eval.py     Eval runner, CI-gated                             (Step 8)
tests/            pytest unit + integration tests
```
