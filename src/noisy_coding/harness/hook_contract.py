"""Retained hook protocol types, private to adapters and HTTP compatibility."""
from dataclasses import dataclass, field
from typing import Protocol
from noisy_coding.harness.base import Capabilities, Event, ListenerAction, Moment, Observation

@dataclass(frozen=True)
class Interpretation(Observation):
    # Participants (subagents) never take the conversation's queue: a
    # message spoken to the user's agent must reach the parent, not a child
    # that happened to run a tool first (#40).
    may_drain: bool = False
    # What the calling hook must inject into identity-sensitive tool calls
    # (speak/announce/...). None when this payload is not such a call.
    speech_identity: str | None = None
    listener: ListenerAction = "none"


@dataclass(frozen=True)
class Delivery:
    context: str
    system_message: str
    exit_code: int
    extra: dict = field(default_factory=dict)


class Harness(Protocol):
    name: str  # registry key ("claude-hooks", "codex-hooks", ...)
    label: str  # human wording ("Claude Code", "Codex")
    capabilities: Capabilities

    def interpret(self, payload: dict) -> Interpretation: ...

    def deliver(self, messages: list[str], moment: Moment) -> Delivery: ...
