# Scriptorium

A macOS background service that watches your Obsidian vault for new files and converts them into structured wiki notes using the Claude API.

Drop a PDF, text file, or markdown document into the `raw/` folder. Scriptorium extracts the text, generates a structured note with a summary, key concepts, and wikilinks, and saves it to your wiki. The source file moves to `raw/processed/`.

## Prerequisites

- macOS 13+
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- An [Anthropic API key](https://console.anthropic.com/)
- Obsidian with iCloud sync enabled

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
git clone https://github.com/YOUR_USERNAME/scriptorium.git
cd scriptorium
uv venv
uv pip install -e .
```

## Running manually

```bash
ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python main.py
```

Logs are written to `~/Library/Logs/scriptorium.log`. Enable debug logging with `SCRIPTORIUM_DEBUG=1`.

## Troubleshooting

**File lands in `raw/failed/` immediately after dropping**

iCloud may fire a creation event before a large file finishes syncing. If the source device is still uploading, Scriptorium reads partial bytes and routes the file to `failed/`. Re-drop the file once iCloud finishes syncing — it will process correctly.

## Running as a macOS service (launchd)

1. Copy the plist template and fill in your credentials (run from the cloned `scriptorium/` directory):

   ```bash
   cp com.scriptorium.watcher.plist ~/Library/LaunchAgents/
   # Replace all four YOUR_USERNAME placeholders with your actual username:
   sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.scriptorium.watcher.plist
   ```

   Then open `~/Library/LaunchAgents/com.scriptorium.watcher.plist` and replace `YOUR_API_KEY_HERE` with your Anthropic API key.

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

## Generated note format

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
