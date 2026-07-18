"""
Embedding client -- wraps the OpenAI embeddings API.
"""

from openai import OpenAI

from src.config import settings

_client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts.

    OpenAI's embeddings endpoint accepts many inputs per call, but we
    batch conservatively at 100 to keep individual requests small and
    retries cheap if one batch fails.
    """
    all_embeddings: list[list[float]] = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = _client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in resp.data)
        print(f"  embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    return all_embeddings