# Scriptorium Design

**Date:** 2026-05-04
**Status:** Approved

## Overview

macOS background service that monitors an iCloud Obsidian folder for new files, extracts their text, sends it to the Claude API, and writes structured Obsidian markdown notes to a wiki folder. Processed source files are moved to a `processed/` subfolder.

---

## Section 1: Architecture

**Modular single-package layout:**

```
scriptorium/
├── pyproject.toml
├── requirements.txt
├── main.py                  ← entry point; wires components, starts watchdog observer
├── scriptorium/
│   ├── __init__.py
│   ├── watcher.py           ← FileSystemEventHandler subclass; filters events, delegates
│   ├── extractor.py         ← reads PDF/txt/md → plain text string
│   ├── claude.py            ← builds prompt, calls Claude API, returns structured text
│   └── writer.py            ← writes .md to wiki/, moves source file to processed/ or failed/
├── com.scriptorium.watcher.plist
├── docs/superpowers/specs/
└── README.md
```

Each module has one responsibility. `main.py` wires them together — it's the only file that knows the full pipeline. Modules communicate through plain Python function calls and return values (not shared state). This mirrors the separation-of-concerns pattern used in professional Python services: easy to test each layer independently, easy to swap out (e.g., replace `extractor.py` with a new format handler without touching `claude.py`).

**Python environment:** managed with `uv`. Canonical entry point: `.venv/bin/python main.py`.

---

## Section 2: Data Flow

```
raw/ (drop zone)
  │
  ▼ watchdog on_created event
watcher.py
  │  filter: ignore dotfiles, ignore non-.pdf/.txt/.md
  ▼
extractor.py  →  plain text string
  │
  ▼
claude.py  →  structured markdown string
  │
  ▼
writer.py
  ├── write .md to wiki/
  └── move source → raw/processed/   (or raw/failed/ on error)
```

**Paths:**
- Watch: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/raw/`
- Output: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/`
- Processed: `raw/processed/`
- Failed: `raw/failed/`

**Filename collision:** if output `.md` already exists, append a timestamp suffix (e.g., `note_20260504T143022.md`).

---

## Section 3: Claude API Integration

**Model:** `claude-sonnet-4-20250514`

**Prompt caching** (reduces latency + cost on repeated calls):
- `cache_control: {"type": "ephemeral"}` on system prompt block
- `cache_control` on wiki context block (titles + first paragraph of existing wiki notes)

**Output format** (Claude writes structured markdown directly):

```markdown
# {{Title}}

**Date:** {{YYYY-MM-DD}}
**Source:** {{original filename}}

## Summary
...

## Key Concepts
- [[Wikilink]]
- [[Wikilink]]

## Open Questions
- ...
```

**Wikilink strategy:** pass existing wiki note titles + first paragraph as context. Claude generates `[[Note Title]]` links that match real notes where relevant, and invents new titles for new concepts.

**API key:** read from `ANTHROPIC_API_KEY` environment variable. Missing key → crash at startup with clear error message.

---

## Section 4: Error Handling & Logging

| Scenario | Behavior |
|----------|----------|
| Dotfile or hidden file created | Silently ignore |
| File unreadable / corrupt PDF | Move to `raw/failed/`, write `<filename>.error.log` |
| Claude API error | Move to `raw/failed/`, write `<filename>.error.log` |
| `ANTHROPIC_API_KEY` missing | Crash at startup with clear error message |
| Output `.md` already exists | Append timestamp to output filename |

**Logging:**
- Python `logging` module
- Output: `~/Library/Logs/scriptorium.log`
- Default level: `INFO`
- Debug mode: set `SCRIPTORIUM_DEBUG=1` env var → `DEBUG` level

**`.error.log` format:**
```
Timestamp: 2026-05-04T14:30:22
File: document.pdf
Error: [exception type and message]
Traceback:
  [full traceback]
```

---

## Section 5: Deployment

**launchd plist:** `com.scriptorium.watcher.plist`
**Install path:** `~/Library/LaunchAgents/com.scriptorium.watcher.plist`

Key plist configuration:
```xml
<key>Label</key>        <string>com.scriptorium.watcher</string>
<key>ProgramArguments</key>
  <array>
    <string>/absolute/path/to/scriptorium/.venv/bin/python</string>
    <string>/absolute/path/to/scriptorium/main.py</string>
  </array>
<key>EnvironmentVariables</key>
  <dict>
    <key>ANTHROPIC_API_KEY</key><string>YOUR_KEY_HERE</string>
  </dict>
<key>RunAtLoad</key>     <true/>
<key>KeepAlive</key>     <true/>
<key>StandardOutPath</key><string>/Users/USERNAME/Library/Logs/scriptorium.log</string>
<key>StandardErrorPath</key><string>/Users/USERNAME/Library/Logs/scriptorium.log</string>
```

**Setup flow (documented in README):**
1. `uv venv && uv pip install -e .`
2. Edit plist — fill in absolute paths and API key
3. `cp com.scriptorium.watcher.plist ~/Library/LaunchAgents/`
4. `launchctl load ~/Library/LaunchAgents/com.scriptorium.watcher.plist`

`KeepAlive: true` → launchd auto-restarts on crash. `RunAtLoad: true` → starts on user login.
