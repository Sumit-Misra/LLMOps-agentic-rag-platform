"""
Unit test: settings load correctly with sensible defaults. No live DB
or API key required -- pydantic-settings just parses whatever env vars
or .env values are present.
"""

from src.config import Settings


def test_settings_have_expected_defaults():
    settings = Settings(_env_file=None)  # ignore any local .env for this test
    assert settings.openai_chat_model == "gpt-4.1-mini"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.openai_embedding_dim == 1536
    assert settings.app_env == "development"


def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-test-override")
    settings = Settings(_env_file=None)
    assert settings.openai_chat_model == "gpt-test-override"