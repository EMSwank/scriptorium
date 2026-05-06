import pytest

from scriptorium.config import LLMConfig, build_config


def test_defaults_to_anthropic():
    config = build_config({"ANTHROPIC_API_KEY": "test-key"})
    assert config.provider == "anthropic"
    assert config.model == "claude-sonnet-4-6"
    assert config.api_key == "test-key"
    assert config.base_url is None


def test_anthropic_custom_model():
    config = build_config({"ANTHROPIC_API_KEY": "key", "LLM_MODEL": "claude-opus-4-7"})
    assert config.model == "claude-opus-4-7"


def test_openai_defaults():
    config = build_config({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"})
    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.api_key == "sk-test"
    assert config.base_url is None


def test_gemini_defaults():
    config = build_config({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "gemini-key"})
    assert config.provider == "gemini"
    assert config.model == "gemini-2.0-flash"
    assert config.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_ollama_defaults():
    config = build_config({"LLM_PROVIDER": "ollama"})
    assert config.provider == "ollama"
    assert config.model == "gemma4:e2b"
    assert config.api_key is None
    assert config.base_url == "http://localhost:11434/v1"


def test_llm_base_url_overrides_default():
    config = build_config({"LLM_PROVIDER": "ollama", "LLM_BASE_URL": "http://custom:11434/v1"})
    assert config.base_url == "http://custom:11434/v1"


def test_missing_anthropic_key_exits():
    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
        build_config({})


def test_missing_openai_key_exits():
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        build_config({"LLM_PROVIDER": "openai"})


def test_missing_gemini_key_exits():
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        build_config({"LLM_PROVIDER": "gemini"})


def test_unknown_provider_exits():
    with pytest.raises(SystemExit, match="xyz"):
        build_config({"LLM_PROVIDER": "xyz"})
