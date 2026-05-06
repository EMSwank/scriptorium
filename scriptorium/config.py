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
        "model": "gemma4:e4b",
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
