# LLM Provider Abstraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded Anthropic client with a config-driven abstraction supporting Anthropic, OpenAI, Gemini, and Ollama via environment variables.

**Architecture:** A frozen `LLMConfig` dataclass carries all provider state. `build_config()` reads env vars and validates credentials at startup (fast-fail before the watcher starts). `generate_note()` dispatches to an Anthropic path (with prompt caching) or an OpenAI-compatible path (OpenAI, Gemini, Ollama). The watcher stores `config`; all callers see no change.

**Tech Stack:** Python 3.11+, `anthropic>=0.49`, `openai>=1.0`, `uv`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scriptorium/config.py` | Create | `LLMConfig` dataclass + `build_config()` |
| `scriptorium/claude.py` | Rename → `scriptorium/llm.py` | Note generation, two provider code paths |
| `scriptorium/watcher.py` | Modify | Accept `LLMConfig` instead of `api_key: str` |
| `main.py` | Modify | Build `LLMConfig` via `build_config(os.environ)` at startup |
| `pyproject.toml` | Modify | Add `openai>=1.0` dependency |
| `tests/test_config.py` | Create | Tests for `build_config()` |
| `tests/test_claude.py` | Rename → `tests/test_llm.py` | Tests for `generate_note()` with new signature |
| `tests/test_watcher.py` | Modify | Fixture: `LLMConfig(...)` instead of patching `anthropic.Anthropic` |
| `README.md` | Modify | Document LLM provider env vars |

---

### Task 1: Config Module

**Files:**
- Create: `scriptorium/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/eliotswank/dev/scriptorium && .venv/bin/pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scriptorium.config'`

- [ ] **Step 3: Implement `scriptorium/config.py`**

Create `scriptorium/config.py`:

```python
import sys
from dataclasses import dataclass

_PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "base_url": None,
        "key_env": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": None,
        "key_env": "OPENAI_API_KEY",
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "model": "gemma4:e2b",
        "base_url": "http://localhost:11434/v1",
        "key_env": None,
    },
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None


def build_config(env: dict) -> LLMConfig:
    provider = env.get("LLM_PROVIDER", "anthropic")
    if provider not in _PROVIDERS:
        sys.exit(
            f"Error: Unknown LLM_PROVIDER '{provider}'. "
            f"Valid: {', '.join(_PROVIDERS)}"
        )
    defaults = _PROVIDERS[provider]
    model = env.get("LLM_MODEL", defaults["model"])
    base_url = env.get("LLM_BASE_URL", defaults["base_url"])
    key_env = defaults["key_env"]
    if key_env:
        api_key = env.get(key_env)
        if not api_key:
            sys.exit(
                f"Error: {key_env} not set (required for provider={provider})"
            )
    else:
        api_key = None
    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scriptorium/config.py tests/test_config.py
git commit -m "feat(config): add LLMConfig dataclass and build_config()"
```

---

### Task 2: Multi-Provider LLM Module + Watcher Update

This task renames `claude.py` → `llm.py`, rewrites `generate_note` to support two code paths, updates `watcher.py` to use `LLMConfig`, and refreshes both test files. All changes are tightly coupled and ship in one commit.

**Files:**
- Rename: `scriptorium/claude.py` → `scriptorium/llm.py`
- Rename: `tests/test_claude.py` → `tests/test_llm.py`
- Modify: `scriptorium/watcher.py`
- Modify: `tests/test_watcher.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add openai dependency**

Edit `pyproject.toml`. Change the `dependencies` array to:

```toml
dependencies = [
    "anthropic>=0.49.0",
    "openai>=1.0",
    "watchdog>=4.0.0",
    "pdfplumber>=0.11.0",
]
```

Install: `.venv/bin/pip install -e .`
Expected: `openai` installs, no errors.

- [ ] **Step 2: Rename source and test files**

```bash
git mv scriptorium/claude.py scriptorium/llm.py
git mv tests/test_claude.py tests/test_llm.py
```

- [ ] **Step 3: Write new tests in `tests/test_llm.py`**

Overwrite the entire contents of `tests/test_llm.py` with:

```python
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


# ── OpenAI-compatible path ────────────────────────────────────────────────────

@pytest.mark.parametrize("provider,model,api_key,base_url", [
    ("openai", "gpt-4o-mini", "sk-test", None),
    ("gemini", "gemini-2.0-flash", "gemini-key", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ("ollama", "gemma4:e2b", None, "http://localhost:11434/v1"),
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
    ("ollama", "gemma4:e2b", None, "http://localhost:11434/v1"),
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_llm.py -v`
Expected: FAIL — import errors or wrong `generate_note` signature. This is expected; implementation comes next.

- [ ] **Step 5: Rewrite `scriptorium/llm.py`**

Overwrite the entire contents of `scriptorium/llm.py` with:

```python
import datetime
import logging
from pathlib import Path

import anthropic
import openai

from scriptorium.config import LLMConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a knowledge management assistant. Convert the provided document into a \
structured Obsidian markdown note.

Output ONLY the markdown content — no preamble, no explanation.

Use this exact format:

# {{Title}}

**Date:** {{YYYY-MM-DD}}
**Source:** {{original filename}}

## Summary
(2-4 sentence summary of the document)

## Key Concepts
- [[Wikilink1]]
- [[Wikilink2]]

## Open Questions
- (questions raised by the document)

Use [[double bracket]] wikilinks for key concepts. Match existing note titles \
from the context provided where relevant. Create new wikilink titles for novel \
concepts not already in the knowledge base.\
"""

_MAX_PARA_CHARS = 300


def load_wiki_context(wiki_dir: Path) -> str:
    notes = []
    for md_file in sorted(wiki_dir.glob("*.md")):
        lines = md_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        title = md_file.stem
        para_lines: list[str] = []
        past_title = False
        for line in lines:
            if not past_title:
                if line.startswith("# "):
                    title = line.lstrip("#").strip()
                    past_title = True
                continue
            if not line.strip() and para_lines:
                break
            if line.strip():
                para_lines.append(line.strip())
        para = " ".join(para_lines)[:_MAX_PARA_CHARS]
        entry = f"- [[{title}]]: {para}" if para else f"- [[{title}]]"
        notes.append(entry)

    if not notes:
        return ""
    return "Existing notes in this knowledge base:\n" + "\n".join(notes)


def generate_note(
    text: str,
    source_filename: str,
    wiki_context: str,
    config: LLMConfig,
) -> str:
    if config.provider == "anthropic":
        return _generate_anthropic(text, source_filename, wiki_context, config)
    return _generate_openai_compat(text, source_filename, wiki_context, config)


def _generate_anthropic(
    text: str,
    source_filename: str,
    wiki_context: str,
    config: LLMConfig,
) -> str:
    client = anthropic.Anthropic(api_key=config.api_key)
    today = datetime.date.today().isoformat()
    user_content: list[dict] = []
    if wiki_context:
        user_content.append(
            {
                "type": "text",
                "text": wiki_context,
                "cache_control": {"type": "ephemeral"},
            }
        )
    user_content.append(
        {
            "type": "text",
            "text": f"Today's date: {today}\nFilename: {source_filename}\n\n---\n\n{text}",
        }
    )
    response = client.messages.create(
        model=config.model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    logger.debug("API usage: %s", response.usage)
    return response.content[0].text


def _generate_openai_compat(
    text: str,
    source_filename: str,
    wiki_context: str,
    config: LLMConfig,
) -> str:
    # OpenAI SDK requires a non-empty api_key; "ollama" is a harmless placeholder
    client = openai.OpenAI(
        api_key=config.api_key or "ollama",
        base_url=config.base_url,
    )
    today = datetime.date.today().isoformat()
    user_parts: list[str] = []
    if wiki_context:
        user_parts.append(wiki_context)
    user_parts.append(
        f"Today's date: {today}\nFilename: {source_filename}\n\n---\n\n{text}"
    )
    response = client.chat.completions.create(
        model=config.model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    logger.debug("API usage: %s", response.usage)
    return response.choices[0].message.content
```

- [ ] **Step 6: Rewrite `scriptorium/watcher.py`**

Overwrite the entire contents of `scriptorium/watcher.py` with:

```python
import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from scriptorium.config import LLMConfig
from scriptorium.extractor import extract_text
from scriptorium.llm import generate_note, load_wiki_context
from scriptorium.writer import move_to_failed, write_note

logger = logging.getLogger(__name__)

# Mirrors extractor._SUPPORTED — intentionally decoupled so watcher and extractor can evolve independently
_SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


class ScriptoriumHandler(FileSystemEventHandler):
    def __init__(self, wiki_dir: Path, raw_dir: Path, config: LLMConfig) -> None:
        super().__init__()
        self.wiki_dir = wiki_dir
        self.raw_dir = raw_dir
        self.config = config

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name.startswith("."):
            return
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            return
        logger.info("New file: %s", path.name)
        self._process(path)

    def _process(self, path: Path) -> None:
        try:
            text = extract_text(path)
            wiki_context = load_wiki_context(self.wiki_dir)
            content = generate_note(text, path.name, wiki_context, self.config)
            write_note(content, path, self.wiki_dir, self.raw_dir)
        except Exception as e:
            logger.exception("Error processing %s", path.name)
            try:
                move_to_failed(path, self.raw_dir, e)
            except Exception:
                logger.exception("Failed to route %s to failed/", path.name)
```

- [ ] **Step 7: Rewrite `tests/test_watcher.py`**

Overwrite the entire contents of `tests/test_watcher.py` with:

```python
from pathlib import Path
from unittest.mock import patch

import pytest
from watchdog.events import DirCreatedEvent, FileCreatedEvent, FileModifiedEvent

from scriptorium.config import LLMConfig
from scriptorium.watcher import ScriptoriumHandler


@pytest.fixture
def handler(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    config = LLMConfig(
        provider="anthropic", model="claude-sonnet-4-6", api_key="test-key", base_url=None
    )
    return ScriptoriumHandler(wiki_dir=wiki_dir, raw_dir=raw_dir, config=config)


def test_ignores_directories(handler):
    event = DirCreatedEvent("/raw/subdir")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_ignores_dotfiles(handler):
    event = FileCreatedEvent("/raw/.DS_Store")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_ignores_unsupported_extension(handler):
    event = FileCreatedEvent("/raw/doc.docx")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_processes_txt(handler):
    event = FileCreatedEvent("/raw/doc.txt")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/doc.txt"))


def test_processes_pdf(handler):
    event = FileCreatedEvent("/raw/report.pdf")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/report.pdf"))


def test_processes_md(handler):
    event = FileCreatedEvent("/raw/notes.md")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/notes.md"))


def test_processes_uppercase_extension(handler):
    event = FileCreatedEvent("/raw/report.PDF")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/report.PDF"))


def test_on_modified_ignored(handler):
    with patch.object(handler, "_process") as mock_process:
        handler.on_modified(FileModifiedEvent("/raw/doc.txt"))
        mock_process.assert_not_called()


def test_process_calls_pipeline(handler, tmp_path):
    source = tmp_path / "raw" / "doc.txt"
    source.write_text("content", encoding="utf-8")

    with (
        patch("scriptorium.watcher.extract_text", return_value="extracted") as mock_extract,
        patch("scriptorium.watcher.load_wiki_context", return_value="context") as mock_ctx,
        patch("scriptorium.watcher.generate_note", return_value="# Note") as mock_gen,
        patch("scriptorium.watcher.write_note") as mock_write,
    ):
        handler._process(source)

    mock_extract.assert_called_once_with(source)
    mock_ctx.assert_called_once_with(handler.wiki_dir)
    mock_gen.assert_called_once_with("extracted", "doc.txt", "context", handler.config)
    mock_write.assert_called_once_with("# Note", source, handler.wiki_dir, handler.raw_dir)


def test_process_routes_errors_to_failed(handler, tmp_path):
    source = tmp_path / "raw" / "bad.txt"
    source.write_text("content", encoding="utf-8")
    err = ValueError("boom")

    with (
        patch("scriptorium.watcher.extract_text", side_effect=err),
        patch("scriptorium.watcher.move_to_failed") as mock_failed,
    ):
        handler._process(source)

    mock_failed.assert_called_once_with(source, handler.raw_dir, err)


def test_process_move_to_failed_secondary_exception_does_not_propagate(handler, tmp_path):
    source = tmp_path / "raw" / "bad.txt"
    source.write_text("content", encoding="utf-8")

    with (
        patch("scriptorium.watcher.extract_text", side_effect=ValueError("pipeline fail")),
        patch("scriptorium.watcher.move_to_failed", side_effect=OSError("disk full")),
    ):
        # Must not raise — secondary exception in move_to_failed is swallowed and logged
        handler._process(source)
```

- [ ] **Step 8: Run all tests**

Run: `.venv/bin/pytest -v`
Expected: All tests PASS across test_config, test_llm, test_watcher, test_extractor, test_writer.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml scriptorium/llm.py scriptorium/watcher.py tests/test_llm.py tests/test_watcher.py
git commit -m "feat(llm): add multi-provider support (openai, gemini, ollama)"
```

---

### Task 3: Update Entry Point

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Rewrite `main.py`**

Overwrite the entire contents of `main.py` with:

```python
import logging
import os
import time
from pathlib import Path

from watchdog.observers import Observer

from scriptorium.config import build_config
from scriptorium.watcher import ScriptoriumHandler

RAW_DIR = Path(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/raw"
).expanduser()
WIKI_DIR = Path(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki"
).expanduser()


def setup_logging() -> None:
    log_dir = Path("~/Library/Logs").expanduser()
    log_dir.mkdir(exist_ok=True)
    level = logging.DEBUG if os.environ.get("SCRIPTORIUM_DEBUG") else logging.INFO
    logging.basicConfig(
        filename=log_dir / "scriptorium.log",
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main() -> None:
    config = build_config(os.environ)

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting Scriptorium provider=%s model=%s",
        config.provider,
        config.model,
    )

    (RAW_DIR / "processed").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "failed").mkdir(parents=True, exist_ok=True)

    handler = ScriptoriumHandler(wiki_dir=WIKI_DIR, raw_dir=RAW_DIR, config=config)
    observer = Observer()
    observer.schedule(handler, str(RAW_DIR), recursive=False)
    observer.start()
    logger.info("Watching: %s", RAW_DIR)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Smoke-test startup validation**

Run: `python main.py`
Expected: exits immediately with message containing `ANTHROPIC_API_KEY not set`

Run: `LLM_PROVIDER=xyz python main.py`
Expected: exits with message containing `Unknown LLM_PROVIDER 'xyz'`

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): build LLMConfig at startup, log active provider"
```

---

### Task 4: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add LLM Provider Configuration section**

In `README.md`, insert the following new section between `## Supported file types` and `## Generated note format`:

```markdown
## LLM Provider Configuration

By default Scriptorium uses Anthropic Claude. Set `LLM_PROVIDER` to switch providers.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | `anthropic`, `openai`, `gemini`, or `ollama` |
| `LLM_MODEL` | Provider default | Override the model name |
| `LLM_BASE_URL` | Provider default | Override the API base URL |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | — | Required when `LLM_PROVIDER=gemini` |

### Provider defaults

| Provider | Default model | Notes |
|----------|--------------|-------|
| `anthropic` | `claude-sonnet-4-6` | Prompt caching enabled |
| `openai` | `gpt-4o-mini` | OpenAI-compatible |
| `gemini` | `gemini-2.0-flash` | Uses Gemini's OpenAI-compatible endpoint |
| `ollama` | `gemma4:e2b` | Local inference; no API key required |

### Examples

**OpenAI:**
```bash
LLM_PROVIDER=openai OPENAI_API_KEY=sk-... .venv/bin/python main.py
```

**Gemini:**
```bash
LLM_PROVIDER=gemini GEMINI_API_KEY=AIza... .venv/bin/python main.py
```

**Ollama (local):**
```bash
# Pull the model first: ollama pull gemma4:e2b
LLM_PROVIDER=ollama .venv/bin/python main.py
```

**Custom model:**
```bash
LLM_PROVIDER=anthropic LLM_MODEL=claude-opus-4-7 ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python main.py
```
```

- [ ] **Step 2: Update the launchd plist instructions**

In the `## Running as a macOS service (launchd)` section, find the paragraph that says "Then open `~/Library/LaunchAgents/com.scriptorium.watcher.plist` and replace `YOUR_API_KEY_HERE` with your Anthropic API key." and append this sentence:

```
For non-Anthropic providers, set the relevant key variable instead (e.g., `OPENAI_API_KEY`) and add `LLM_PROVIDER` with the provider name.
```

- [ ] **Step 3: Run tests one final time**

Run: `.venv/bin/pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document LLM provider configuration"
```
