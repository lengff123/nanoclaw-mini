"""Agent core module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["AgentLoop", "ContextBuilder", "MemoryStore"]

if TYPE_CHECKING:
    from nanoclaw_mini.agent.context import ContextBuilder
    from nanoclaw_mini.agent.loop import AgentLoop
    from nanoclaw_mini.agent.memory import MemoryStore


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
    raise AttributeError(name)
