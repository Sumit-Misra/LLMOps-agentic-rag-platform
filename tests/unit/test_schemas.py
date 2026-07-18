"""
Unit test: API request/response schemas validate as expected.
"""

import pytest
from pydantic import ValidationError

from src.api.schemas import ChatRequest, ChatResponse


def test_chat_request_requires_message_and_thread_id():
    req = ChatRequest(message="hello", thread_id="t1")
    assert req.message == "hello"
    assert req.thread_id == "t1"


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="", thread_id="t1")


def test_chat_response_shape():
    resp = ChatResponse(answer="hi", sources=["a.md"], revisions=1)
    assert resp.answer == "hi"
    assert resp.sources == ["a.md"]
    assert resp.revisions == 1