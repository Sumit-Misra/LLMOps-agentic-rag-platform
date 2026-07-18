"""
One-time/occasional script: create or update the versioned system
prompt in Langfuse.

Run whenever you want to publish a new version of the agent's system
prompt:
    python3 scripts/push_prompt.py

Langfuse keeps every version you ever push; labeling this one
"production" is what makes get_prompt(..., label="production") in
nodes.py pick it up automatically, with zero code changes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.observability.langfuse_client import get_langfuse_client

PROMPT_NAME = "devops-rag-system-prompt"

PROMPT_TEXT = """You are a DevOps and cloud-infrastructure knowledge assistant.
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


def main() -> None:
    client = get_langfuse_client()
    prompt = client.create_prompt(
        name=PROMPT_NAME,
        prompt=PROMPT_TEXT,
        labels=["production"],
        type="text",
        commit_message="Initial version",
    )
    client.flush()
    print(f"Pushed prompt '{PROMPT_NAME}' version {prompt.version}, labeled 'production'")


if __name__ == "__main__":
    main()