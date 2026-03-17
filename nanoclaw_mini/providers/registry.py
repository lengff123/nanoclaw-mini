"""Provider registry for the Codex OAuth-only build."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    """Metadata describing one supported provider."""

    name: str
    keywords: tuple[str, ...]
    display_name: str = ""
    is_oauth: bool = False

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openai_codex",
        keywords=("openai-codex", "openai_codex"),
        display_name="OpenAI Codex",
        is_oauth=True,
    ),
)


def find_by_model(model: str) -> ProviderSpec | None:
    """Match a supported provider by explicit prefix or keyword."""
    model_lower = model.lower()
    model_prefix = model_lower.split("/", 1)[0] if "/" in model_lower else ""
    normalized_prefix = model_prefix.replace("-", "_")

    for spec in PROVIDERS:
        if model_prefix and normalized_prefix == spec.name:
            return spec

    for spec in PROVIDERS:
        if any(keyword in model_lower for keyword in spec.keywords):
            return spec

    return find_by_name("openai_codex")


def find_by_name(name: str | None) -> ProviderSpec | None:
    """Find a provider spec by config field name."""
    if not name:
        return None
    normalized = name.replace("-", "_")
    for spec in PROVIDERS:
        if spec.name == normalized:
            return spec
    return None
