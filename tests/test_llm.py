from unittest.mock import MagicMock, patch

import pytest

from scriptorium.config import LLMConfig
from scriptorium.llm import SYSTEM_PROMPT, generate_note, load_wiki_context


# ── load_wiki_context (unchanged behavior) ────────────────────────────────────

def test_load_wiki_context_empty_dir(tmp_path):
    assert load_wiki_context(tmp_path) == ""


def test_load_wiki_context_reads_title_and_first_paragraph(tmp_path):
    (tmp_path / "alpha.md").write_text(
        "# Alpha Note\n\nThis is the first paragraph.\n\nSecond paragraph.",
        encoding="utf-8",
    )
    result = load_wiki_context(tmp_path)
    assert "[[Alpha Note]]" in result
    assert "first paragraph" in result
    assert "Second paragraph" not in result
    assert "[[Alpha Note]]: This is the first paragraph." in result


def test_load_wiki_context_multiple_notes(tmp_path):
    (tmp_path / "alpha.md").write_text("# Alpha\n\nAlpha content.", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# Beta\n\nBeta content.", encoding="utf-8")
    result = load_wiki_context(tmp_path)
    assert "[[Alpha]]" in result
    assert "[[Beta]]" in result


def test_load_wiki_context_ignores_subdirectory_md_files(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "hidden.md").write_text("# Hidden\n\nContent.", encoding="utf-8")
    result = load_wiki_context(tmp_path)
    assert "Hidden" not in result


# ── Anthropic path ────────────────────────────────────────────────────────────

def _anthropic_config(**kwargs):
    defaults = dict(
        provider="anthropic", model="claude-sonnet-4-6", api_key="test-key", base_url=None
    )
    defaults.update(kwargs)
    return LLMConfig(**defaults)


def test_generate_note_anthropic_returns_api_text():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Generated\n\nContent")],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        result = generate_note("doc text", "doc.txt", "", config)
    assert result == "# Generated\n\nContent"


def test_generate_note_anthropic_calls_correct_model():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Note")], usage=MagicMock()
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        generate_note("text", "doc.txt", "", config)
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 4096


def test_generate_note_anthropic_system_prompt_has_cache_control():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Note")], usage=MagicMock()
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        generate_note("text", "doc.txt", "", config)
    kwargs = mock_client.messages.create.call_args.kwargs
    system_blocks = kwargs["system"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert system_blocks[0]["text"] == SYSTEM_PROMPT


def test_generate_note_anthropic_wiki_context_is_cached():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Note")], usage=MagicMock()
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        generate_note("text", "doc.txt", "Existing notes: [[Alpha]]", config)
    kwargs = mock_client.messages.create.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert user_content[0]["text"] == "Existing notes: [[Alpha]]"
    assert user_content[0]["cache_control"] == {"type": "ephemeral"}


def test_generate_note_anthropic_no_wiki_context_omits_context_block():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Note")], usage=MagicMock()
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        generate_note("text", "doc.txt", "", config)
    kwargs = mock_client.messages.create.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert len(user_content) == 1
    assert "cache_control" not in user_content[0]


def test_generate_note_anthropic_raises_on_empty_content():
    config = _anthropic_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(RuntimeError, match="no content blocks"):
            generate_note("text", "doc.txt", "", config)


# ── OpenAI-compatible path ────────────────────────────────────────────────────

@pytest.mark.parametrize("provider,model,api_key,base_url", [
    ("openai", "gpt-4o-mini", "sk-test", None),
    ("gemini", "gemini-2.0-flash", "gemini-key", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ("ollama", "gemma4:e4b", None, "http://localhost:11434/v1"),
])
def test_generate_note_openai_compat_returns_text(provider, model, api_key, base_url):
    config = LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Generated"))],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.openai.OpenAI", return_value=mock_client):
        result = generate_note("doc text", "doc.txt", "", config)
    assert result == "# Generated"


@pytest.mark.parametrize("provider,model,api_key,base_url", [
    ("openai", "gpt-4o-mini", "sk-test", None),
    ("gemini", "gemini-2.0-flash", "gemini-key", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ("ollama", "gemma4:e4b", None, "http://localhost:11434/v1"),
])
def test_generate_note_openai_compat_client_args(provider, model, api_key, base_url):
    config = LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Note"))],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.openai.OpenAI", return_value=mock_client) as mock_openai:
        generate_note("text", "doc.txt", "", config)
    mock_openai.assert_called_once_with(
        api_key=api_key or "ollama",
        base_url=base_url,
    )


def test_generate_note_openai_compat_no_cache_control():
    config = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test", base_url=None)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Note"))],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.openai.OpenAI", return_value=mock_client):
        generate_note("text", "doc.txt", "wiki context", config)
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    for msg in kwargs["messages"]:
        assert "cache_control" not in msg


def test_generate_note_openai_compat_raises_on_none_content():
    config = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test", base_url=None)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=None))],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.openai.OpenAI", return_value=mock_client):
        with pytest.raises(RuntimeError, match="returned no text content"):
            generate_note("text", "doc.txt", "", config)


def test_generate_note_openai_compat_wiki_context_in_user_message():
    config = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test", base_url=None)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Note"))],
        usage=MagicMock(),
    )
    with patch("scriptorium.llm.openai.OpenAI", return_value=mock_client):
        generate_note("text", "doc.txt", "Existing notes: [[Alpha]]", config)
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_message = kwargs["messages"][1]["content"]
    assert "Existing notes: [[Alpha]]" in user_message
