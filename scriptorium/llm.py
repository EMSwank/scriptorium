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
    if not response.content:
        raise RuntimeError("anthropic returned no content blocks")
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
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"{config.provider} returned no text content")
    return content
