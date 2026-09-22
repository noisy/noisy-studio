"""Transport-independent agent conversation and incoming-speech contract.

The core retains its utterance queue. Providers report what they observed;
queued and uncertain receipts never mean the user message was consumed.
Connection data belongs to the provider and is never exposed in UI snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from noisy_studio.harness.base import Event

DeliveryState = Literal['queued', 'sent', 'accepted', 'confirmed', 'rejected', 'unavailable', 'uncertain', 'unknown', 'cancelled']


@dataclass(frozen=True)
class Speech:
    utterance_id: int
    conversation: str
    text: str
    created_at: float
    provenance: str = 'user speech transcribed by Noisy Studio'


@dataclass(frozen=True)
class Receipt:
    utterance_id: int
    conversation: str
    state: DeliveryState
    detail: str = ''
    message_id: str | None = None
    turn_id: str | None = None


@dataclass(frozen=True)
class Availability:
    ready: bool
    reason: str = ''
    interaction_required: bool = False


@dataclass(frozen=True)
class WakeResult:
    state: Literal['requested', 'pending', 'unavailable', 'uncertain']
    detail: str = ''


@dataclass(frozen=True)
class ProviderCapabilities:
    idle_wake: bool
    active_turn_delivery: bool
    lifecycle_observation: bool
    confirmation: Literal['none', 'transport', 'application']
    liveness: Literal['events', 'heuristic'] = 'events'


@dataclass(frozen=True)
class Registration:
    conversation: str
    native_session_id: str
    connection: object = field(default=None, repr=False)
    participant: str | None = None


class Provider(Protocol):
    name: str
    label: str
    capabilities: ProviderCapabilities

    def attach(self, registration: Registration) -> Availability: ...
    def submit(self, speech: Speech) -> Receipt: ...
    def observe(self, events: tuple[Event, ...]) -> None: ...
    def availability(self, conversation: str) -> Availability: ...
    def wake(self, conversation: str) -> WakeResult: ...


ALIASES = {'claude-hooks': 'claude', 'codex-hooks': 'codex', 'grok-hooks': 'grok'}


def provider_name(name: str) -> str:
    return ALIASES.get(name, name)
