from unittest.mock import MagicMock

from scriptorium.claude import SYSTEM_PROMPT, generate_note, load_wiki_context


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


def test_generate_note_returns_api_text():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# Generated\n\nContent")]
    mock_client.messages.create.return_value = mock_response

    result = generate_note("doc text", "doc.txt", "", mock_client)

    assert result == "# Generated\n\nContent"


def test_generate_note_calls_correct_model():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# Note")]
    mock_client.messages.create.return_value = mock_response

    generate_note("text", "doc.txt", "", mock_client)

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 4096


def test_generate_note_system_prompt_has_cache_control():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# Note")]
    mock_client.messages.create.return_value = mock_response

    generate_note("text", "doc.txt", "", mock_client)

    kwargs = mock_client.messages.create.call_args.kwargs
    system_blocks = kwargs["system"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert system_blocks[0]["text"] == SYSTEM_PROMPT


def test_generate_note_wiki_context_is_first_cached_block():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# Note")]
    mock_client.messages.create.return_value = mock_response

    generate_note("text", "doc.txt", "Existing notes: [[Alpha]]", mock_client)

    kwargs = mock_client.messages.create.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert user_content[0]["text"] == "Existing notes: [[Alpha]]"
    assert user_content[0]["cache_control"] == {"type": "ephemeral"}


def test_generate_note_no_wiki_context_omits_context_block():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# Note")]
    mock_client.messages.create.return_value = mock_response

    generate_note("text", "doc.txt", "", mock_client)

    kwargs = mock_client.messages.create.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    # Only one block when no wiki context
    assert len(user_content) == 1
    assert "cache_control" not in user_content[0]
