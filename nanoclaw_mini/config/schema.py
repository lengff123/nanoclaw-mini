"""Configuration schema using Pydantic."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings


class Base(BaseModel):
    """Base model that accepts both camelCase and snake_case keys."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class InteractionConfig(Base):
    """Configuration for local CLI interaction output."""

    send_progress: bool = True
    send_tool_hints: bool = False


class AgentDefaults(Base):
    """Default agent configuration."""

    workspace: str = "~/.nanoclaw-mini/workspace"
    model: str = "openai-codex/gpt-5.1-codex"
    provider: str = "openai_codex"
    max_tokens: int = 8192
    context_window_tokens: int = 65_536
    temperature: float = 0.1
    max_tool_iterations: int = 40
    memory_window: int | None = Field(default=None, exclude=True)
    reasoning_effort: str | None = None

    @property
    def should_warn_deprecated_memory_window(self) -> bool:
        """Return True when old memoryWindow is present without contextWindowTokens."""
        return self.memory_window is not None and "context_window_tokens" not in self.model_fields_set


class AgentsConfig(Base):
    """Agent configuration."""

    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class CodexProviderConfig(Base):
    """Codex OAuth provider configuration placeholder."""


class ProvidersConfig(Base):
    """Configuration for supported LLM providers."""

    openai_codex: CodexProviderConfig = Field(default_factory=CodexProviderConfig)


class HeartbeatConfig(Base):
    """Heartbeat service configuration."""

    enabled: bool = True
    interval_s: int = 30 * 60


class GatewayConfig(Base):
    """Background gateway configuration."""

    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)


class ExecToolConfig(Base):
    """Shell exec tool configuration."""

    timeout: int = 60
    path_append: str = ""


class ToolsConfig(Base):
    """Tools configuration."""

    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False


class Config(BaseSettings):
    """Root configuration for nanoclaw-mini."""

    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    interaction: InteractionConfig = Field(default_factory=InteractionConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()

    def get_provider(self, model: str | None = None) -> CodexProviderConfig:
        """Get the sole supported provider config."""
        return self.providers.openai_codex

    def get_provider_name(self, model: str | None = None) -> str | None:
        """Get the registry name of the matched provider."""
        return "openai_codex"

    def get_api_base(self, model: str | None = None) -> str | None:
        """Get API base URL for the given model."""
        return None
