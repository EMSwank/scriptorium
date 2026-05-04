import datetime
import logging
from pathlib import Path

import anthropic

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
                if line.startswith("#"):
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
    client: anthropic.Anthropic,
) -> str:
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
        model="claude-sonnet-4-6",
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
