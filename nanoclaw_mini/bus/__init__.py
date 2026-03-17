"""Message bus module for decoupled channel-agent communication."""

from nanoclaw_mini.bus.events import InboundMessage, OutboundMessage
from nanoclaw_mini.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
