# LLM Provider Abstraction Design

**Date:** 2026-05-04
**Feature:** Config-driven multi-provider LLM backend

---

## 1. Architecture

Replace the hardcoded `anthropic` client with a thin provider abstraction configured entirely via environment variables. No interactive setup wizard. Anthropic remains the default when `LLM_PROVIDER` is unset (backward compatible).

A new `LLMConfig` frozen dataclass carries all provider state. `main.py` builds it at startup and validates required credentials immediately — missing keys exit before the watcher starts. `watcher.py` stores the config; the actual SDK client is created inside `llm.py` per call.

The module `scriptorium/claude.py` is renamed to `scriptorium/llm.py`. The public interface (`generate_note`, `load_wiki_context`) is unchanged.

---

## 2. Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `LLM_PROVIDER` | No | `anthropic` |
| `LLM_MODEL` | No | Provider default (see below) |
| `LLM_BASE_URL` | No | Provider default |
| `ANTHROPIC_API_KEY` | When provider=anthropic | — |
| `OPENAI_API_KEY` | When provider=openai | — |
| `GEMINI_API_KEY` | When provider=gemini | — |

### Provider defaults

| Provider | Default model | Default base_url |
|----------|--------------|-----------------|
| `anthropic` | `claude-sonnet-4-6` | (SDK default) |
| `openai` | `gpt-4o-mini` | (SDK default) |
| `gemini` | `gemini-2.0-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `ollama` | `gemma4:e2b` | `http://localhost:11434/v1` |

Ollama requires no API key. `LLM_BASE_URL` overrides the default for any provider.

---

## 3. Code Paths

### `scriptorium/config.py` (new)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class LLMConfig:
    provider: str       # "anthropic" | "openai" | "gemini" | "ollama"
    model: str
    api_key: str | None # None for Ollama
    base_url: str | None
```

`build_config(env: dict) -> LLMConfig` reads env vars and applies defaults. Raises `SystemExit` for missing required keys or unknown provider.

### `scriptorium/llm.py` (renamed from claude.py)

Two code paths inside `generate_note`:

**Anthropic path** (`provider == "anthropic"`):
- Uses `anthropic.Anthropic(api_key=config.api_key)`
- Passes `cache_control: {"type": "ephemeral"}` on the system prompt block and wiki context block
- `client.messages.create(model=..., max_tokens=4096, system=[...], messages=[...])`

**OpenAI-compatible path** (`provider in {"openai", "gemini", "ollama"}`):
- Uses `openai.OpenAI(api_key=config.api_key or "ollama", base_url=config.base_url)` — OpenAI SDK requires a non-empty `api_key`; `"ollama"` is a harmless placeholder when no key is needed
- System prompt passed as `{"role": "system", "content": SYSTEM_PROMPT}` message
- No `cache_control`
- `client.chat.completions.create(model=..., max_tokens=4096, messages=[...])`

Both paths return `str`. Caller in `watcher._process` is unchanged.

`generate_note` new signature: `generate_note(text: str, source_filename: str, wiki_context: str, config: LLMConfig) -> str`

`load_wiki_context` is unchanged — no API calls, pure file I/O.

### `scriptorium/watcher.py`

`ScriptoriumHandler.__init__` signature changes:

```python
# Before
def __init__(self, wiki_dir: Path, raw_dir: Path, api_key: str) -> None:
    self.client = anthropic.Anthropic(api_key=api_key)

# After
def __init__(self, wiki_dir: Path, raw_dir: Path, config: LLMConfig) -> None:
    self.config = config
```

`_process` passes `self.config` to `generate_note` instead of `self.client`.

### `main.py`

Builds `LLMConfig` via `build_config(os.environ)` before starting the watcher. Logs active provider and model at startup:

```
INFO Starting Scriptorium provider=anthropic model=claude-sonnet-4-6
```

---

## 4. Error Handling & Startup Validation

Validation runs at startup in `build_config`:

- Unknown `LLM_PROVIDER` → `sys.exit("Error: Unknown LLM_PROVIDER 'xyz'. Valid: anthropic, openai, gemini, ollama")`
- Missing required key → `sys.exit("Error: ANTHROPIC_API_KEY not set (required for provider=anthropic)")`
- Ollama: no key required, `LLM_BASE_URL` defaults to `http://localhost:11434/v1`

Runtime API errors surface as exceptions caught by `watcher._process`, which routes the file to `raw/failed/` with an `.error.log` — no change to existing error handling.

---

## 5. Testing Strategy

**`tests/test_llm.py`** (replaces `test_claude.py`):
- Anthropic path: mock `anthropic.Anthropic` client, assert `cache_control` blocks present in call args
- OpenAI-compatible path: mock `openai.OpenAI` client, assert `base_url` passed correctly, assert no `cache_control` in messages
- Parametrized over openai / gemini / ollama configs (differ only in config values)

**`tests/test_config.py`** (new):
- `build_config` returns correct defaults for each provider
- Missing required key raises `SystemExit` with helpful message
- Unknown provider raises `SystemExit`

**`tests/test_watcher.py`**:
- Fixture updated: pass `LLMConfig(...)` directly instead of patching `anthropic.Anthropic`

`tests/test_extractor.py` and `tests/test_writer.py` untouched.

---

## 6. Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
openai = ">=1.0"
```

`anthropic` dependency retained. No other new dependencies — `openai` SDK covers openai, gemini, and ollama endpoints.

---

## 7. README Updates

New section "LLM Provider Configuration" documents all env vars, provider defaults, and example configs for each provider (Anthropic, OpenAI, Gemini, Ollama). launchd plist example updated to show `LLM_PROVIDER` / `LLM_MODEL` env vars alongside `ANTHROPIC_API_KEY`.
