"""The agent-harness contract: how Noisy Studio attaches to an agent system.

A harness (Claude Code hooks, Codex hooks, later a channel or an SDK) is
an adapter that turns whatever the agent system sends us into a small
vocabulary the daemon understands, and turns the daemon's messages back
into whatever the agent system can consume. Three rules keep adapters
swappable and testable without a daemon:

- Adapters are pure: `interpret()` is a function of the payload (plus a
  transcript reader injected at construction), never of cwd or process
  environment. Identity is derived from what the agent system says about
  the session, so two sessions in one directory can never collide.
- The conversation key is chosen by the adapter and stable for the life of
  the conversation; any other id the harness presents for it is an alias.
- Capabilities are explicit. A harness that cannot wake an idle agent says
  so, and the daemon shows the user that state instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

__all__ = [
    "Capabilities",
    "Delivery",
    "Event",
    "EventKind",
    "Harness",
    "HarnessError",
    "Interpretation",
    "ListenerAction",
    "Liveness",
    "Moment",
    "Wake",
]

Wake = Literal["push", "long_poll", "none"]
Liveness = Literal["events", "heuristic"]
Moment = Literal["mid_turn", "wake"]
ListenerAction = Literal["none", "start", "poll"]
EventKind = Literal[
    "session_started",
    "session_ended",
    "turn_started",
    "turn_ended",
    "activity",
    "title_changed",
    "participant_started",
    "participant_ended",
]


class HarnessError(ValueError):
    """The payload cannot be interpreted; identity-sensitive callers fail closed."""


@dataclass(frozen=True)
class Capabilities:
    wake: Wake
    # long_poll only: a listener older than this has expired and the agent
    # is deaf until the user types. None for push/none.
    max_idle_seconds: float | None
    liveness: Liveness
    mid_turn_delivery: bool
    spawn: bool


@dataclass(frozen=True)
class Event:
    kind: EventKind
    conversation: str
    aliases: tuple[str, ...] = ()
    title: str = ""
    source: str = ""
    participant: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Observation:
    """Normalized conversation events; no host reply or polling instructions."""
    conversation: str
    events: tuple[Event, ...] = ()
    short_id: str = ""
    participant: str | None = None


# Compatibility imports for older adapters. New core code uses Observation and
# the transport-independent Provider/Speech/Receipt contract in provider.py.
from noisy_studio.harness.hook_contract import Delivery, Harness, Interpretation  # noqa: E402
