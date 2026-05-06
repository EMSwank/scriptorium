# Scriptorium

Drop a PDF into a folder. A structured wiki note is waiting in Obsidian when you come back.

Scriptorium is a macOS background service that watches your vault for new files, extracts the text, calls an LLM (Claude, OpenAI, Gemini, or a local model via Ollama), and writes a formatted note with a summary, key concepts, and wikilinks. The source file moves to `raw/processed/` when done.

## Prerequisites

- macOS 13+
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- An API key for your chosen LLM provider (Anthropic by default — [get one here](https://console.anthropic.com/))
- Obsidian with iCloud sync enabled

## Obsidian setup

Two minutes to configure. You won't touch this again.

1. **Create or open a vault stored in iCloud Drive.** In Obsidian → Open another vault → Create new vault, set the location to somewhere inside `iCloud Drive/`. Obsidian will store it at:
   ```
   ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<vault-name>/
   ```

2. **Confirm the path matches.** Scriptorium watches:
   ```
   ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/raw/
   ```
   Your vault must be named `wiki`. To use a different name, update `WIKI_DIR` and `RAW_DIR` in `main.py` before running.

3. **Create the `raw/` folder** inside your vault (Obsidian won't create it automatically):
   ```bash
   mkdir -p ~/Library/Mobile\ Documents/iCloud\~md\~obsidian/Documents/wiki/raw
   ```

4. **Exclude `raw/` from Obsidian's file explorer** so processed and failed source files don't clutter your vault view: Obsidian → Settings → Files & Links → Excluded files → add `raw`.

## Folder layout

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/
├── raw/            ← drop files here
│   ├── processed/  ← moved here after successful processing
│   └── failed/     ← moved here on error (+ .error.log alongside)
└── *.md            ← generated notes appear here
```

## Installation

```bash
git clone https://github.com/EMSwank/scriptorium.git
cd scriptorium
uv venv
uv pip install -e .
```

## Running manually

Good for testing. For daily use, skip to [Running as a macOS service](#running-as-a-macos-service-launchd).

```bash
ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python main.py
```

Logs are written to `~/Library/Logs/scriptorium.log`. Enable debug logging with `SCRIPTORIUM_DEBUG=1`.

## Troubleshooting

**File lands in `raw/failed/` immediately after dropping**

iCloud may fire a creation event before a large file finishes syncing. If the source device is still uploading, Scriptorium reads partial bytes and routes the file to `failed/`. Re-drop the file once iCloud finishes syncing — it will process correctly.

## Running as a macOS service (launchd)

Set it up once. After that, Scriptorium starts on login and runs invisibly.

1. Copy the plist template and fill in your credentials (run from the cloned `scriptorium/` directory):

   ```bash
   cp com.scriptorium.watcher.plist ~/Library/LaunchAgents/
   # Replace all four YOUR_USERNAME placeholders with your actual username:
   sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.scriptorium.watcher.plist
   ```

   Then open `~/Library/LaunchAgents/com.scriptorium.watcher.plist` and replace `YOUR_API_KEY_HERE` with your Anthropic API key. For non-Anthropic providers, set the relevant key variable instead (e.g., `OPENAI_API_KEY`) and add `LLM_PROVIDER` with the provider name.

2. Load the service:

   ```bash
   launchctl load ~/Library/LaunchAgents/com.scriptorium.watcher.plist
   ```

3. Verify it is running:

   ```bash
   launchctl list | grep scriptorium
   tail -f ~/Library/Logs/scriptorium.log
   ```

4. Stop the service:

   ```bash
   launchctl unload ~/Library/LaunchAgents/com.scriptorium.watcher.plist
   ```

## Supported file types

| Extension | Extractor |
|-----------|-----------|
| `.pdf`    | pdfplumber |
| `.txt`    | UTF-8 read |
| `.md`     | UTF-8 read |

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

## Generated note format

Every processed file produces this:

```markdown
# Title

**Date:** YYYY-MM-DD
**Source:** original-filename.pdf

## Summary
2-4 sentence summary.

## Key Concepts
- [[Wikilink]]

## Open Questions
- Question raised by the document.
```

Wikilinks match existing note titles in your vault where possible. New concepts get new wikilink titles.

## Development

```bash
uv pip install -e ".[dev]"
.venv/bin/pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
