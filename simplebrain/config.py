from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, model_validator
import os


# LiteLLM provider prefix rules:
# - ollama models must be "ollama/<model>"
# - lmstudio models must be "lm_studio/<model>"
# - openai / anthropic models are used as-is (litellm recognises them natively)
_PROVIDER_PREFIXES: dict[str, str] = {
    "ollama": "ollama",
    "lmstudio": "lm_studio",
    "azure": "azure",
}

# Default API base URLs per provider (used when user doesn't set one)
_PROVIDER_DEFAULT_API_BASE: dict[str, str] = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434",
}

# Placeholder API keys for providers that don't require real auth
_PROVIDER_PLACEHOLDER_API_KEY: dict[str, str] = {
    "lmstudio": "lm-studio",
    "ollama": "ollama",
}

# Providers that require a real API key (used in setup warning)
_PROVIDERS_REQUIRING_KEY: frozenset[str] = frozenset({
    "openai", "anthropic", "cohere", "gemini", "groq",
})

# Env-var name that holds the API key for each provider
_PROVIDER_API_KEY_ENV: dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "cohere":    "COHERE_API_KEY",
    "gemini":    "GEMINI_API_KEY",
    "groq":      "GROQ_API_KEY",
}

# Complete list of supported providers — single source of truth
SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "openai",
    "anthropic",
    "ollama",
    "lmstudio",
    "groq",
    "gemini",
    "cohere",
)


def _normalize_litellm_model(provider: str, model: str) -> str:
    """Return the fully-qualified LiteLLM model string for *provider*/*model*.

    If *model* is already prefixed (e.g. the user typed ``lm_studio/gemma``)
    it is returned unchanged.  Otherwise the appropriate provider prefix is
    prepended so LiteLLM can route the call correctly.
    """
    prefix = _PROVIDER_PREFIXES.get(provider.lower())
    if prefix and not model.startswith(f"{prefix}/") and not model.startswith(f"{prefix}_chat/"):
        return f"{prefix}/{model}"
    return model


def build_litellm_kwargs(
    provider: str,
    model: str,
    api_base: str | None = None,
    api_key: str | None = None,
    api_version: str | None = None,
) -> dict:
    """Build a complete kwargs dict for ``litellm.completion()`` from raw inputs.

    This is used by the setup wizard (which works from an *answers* dict before
    a BrainConfig is written) and mirrors the ``BrainConfig.litellm_kwargs``
    property used everywhere else.
    """
    normalized = _normalize_litellm_model(provider, model)
    kwargs: dict = {"model": normalized}

    resolved_base = api_base or _PROVIDER_DEFAULT_API_BASE.get(provider.lower())
    if resolved_base:
        kwargs["api_base"] = resolved_base

    # Hard timeout so a stalled LM Studio or slow WiFi doesn't block the worker forever.
    # Override with LLM_TIMEOUT env var if needed (seconds).
    import os as _os
    kwargs["timeout"] = float(_os.getenv("LLM_TIMEOUT", "120"))

    resolved_key = api_key or _PROVIDER_PLACEHOLDER_API_KEY.get(provider.lower())
    if resolved_key:
        kwargs["api_key"] = resolved_key

    if api_version:
        kwargs["api_version"] = api_version

    return kwargs


class BrainConfig(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    brain_root: Path
    user: str
    device: str = "unknown"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_version: Optional[str] = None  # required for azure provider
    healer_schedule: str = "daily"        # daily | weekly | manual

    @model_validator(mode="after")
    def _normalise_model(self) -> "BrainConfig":
        """Ensure llm_model is a fully-qualified LiteLLM model string."""
        self.llm_model = _normalize_litellm_model(self.llm_provider, self.llm_model)
        return self

    @property
    def litellm_kwargs(self) -> dict:
        """Return kwargs to spread into every ``litellm.completion()`` call."""
        return build_litellm_kwargs(
            provider=self.llm_provider,
            model=self.llm_model,
            api_base=self.llm_api_base,
            api_key=self.llm_api_key,
            api_version=self.llm_api_version,
        )

    def model_post_init(self, __context):
        pass  # dirs are NOT created on construction — call init_dirs() explicitly

    def init_dirs(self) -> None:
        """Create all required brain directories. Call once after brain_root is finalised."""
        for folder in [
            self.raw_audio_dir, self.raw_transcripts_dir,
            self.queue_dir, self.queue_dir / "failed",
            self.index_dir,
            self.conflicts_dir / "pending",
            self.meta_dir,
            self.knowledge_dir / "_unfiled",
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def raw_audio_dir(self) -> Path:
        return self.brain_root / "_raw" / "audio"

    @property
    def raw_transcripts_dir(self) -> Path:
        return self.brain_root / "_raw" / "transcripts"

    @property
    def queue_dir(self) -> Path:
        return self.brain_root / "_queue"

    @property
    def knowledge_dir(self) -> Path:
        return self.brain_root / "knowledge"

    @property
    def index_dir(self) -> Path:
        return self.brain_root / "_index"

    @property
    def conflicts_dir(self) -> Path:
        return self.brain_root / "_conflicts"

    @property
    def meta_dir(self) -> Path:
        return self.brain_root / "_meta"

    @classmethod
    def from_env(cls) -> "BrainConfig":
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            brain_root=Path(os.getenv("BRAIN_ROOT", "~/simplebrain")).expanduser(),
            user=os.getenv("BRAIN_USER", "default"),
            device=os.getenv("BRAIN_DEVICE", "unknown"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_api_base=os.getenv("LLM_API_BASE") or None,
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_api_version=os.getenv("LLM_API_VERSION") or None,
            healer_schedule=os.getenv("BRAIN_HEALER_SCHEDULE", "daily"),
        )
