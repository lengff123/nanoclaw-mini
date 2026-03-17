"""Agent core module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["AgentLoop", "ContextBuilder", "MemoryStore", "SkillsLoader"]

if TYPE_CHECKING:
    from nanoclaw_mini.agent.context import ContextBuilder
    from nanoclaw_mini.agent.loop import AgentLoop
    from nanoclaw_mini.agent.memory import MemoryStore
    from nanoclaw_mini.agent.skills import SkillsLoader


def __getattr__(name: str) -> Any:
    """Lazily import heavy agent modules on demand."""
    if name == "AgentLoop":
        from nanoclaw_mini.agent.loop import AgentLoop

        return AgentLoop
    if name == "ContextBuilder":
        from nanoclaw_mini.agent.context import ContextBuilder

        return ContextBuilder
    if name == "MemoryStore":
        from nanoclaw_mini.agent.memory import MemoryStore

        return MemoryStore
    if name == "SkillsLoader":
        from nanoclaw_mini.agent.skills import SkillsLoader

        return SkillsLoader
    raise AttributeError(name)
