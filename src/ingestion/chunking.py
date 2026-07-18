"""
Chunks raw document text into embedding-sized pieces.

Uses LangChain's RecursiveCharacterTextSplitter, but with chunk size
measured in *tokens* (via tiktoken) rather than raw characters -- what
actually matters for embedding quality and cost is the token count, and
markdown headers/prose vary a lot in characters-per-token.
"""

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

_encoding = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_encoding.encode(text))


def get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=75,
        length_function=_token_len,
        # Prefer splitting on markdown headers/paragraphs before
        # falling back to sentences/words -- keeps related content
        # (e.g. a whole "## Root Cause" section) together when it fits.
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )


def chunk_document(text: str) -> list[str]:
    splitter = get_splitter()
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]