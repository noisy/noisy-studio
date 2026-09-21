"""Private readiness/lease policy for retained hook delivery."""
from __future__ import annotations

from dataclasses import dataclass
import uuid

from noisy_studio.harness.provider import Availability


@dataclass
class Listener:
    id: str
    started_at: float
    expires_at: float | None


def start(conversation, capabilities, now: float, listener_id=None, window=None) -> str:
    if window is None:
        window = capabilities.max_idle_seconds if capabilities else None
    identifier = listener_id or uuid.uuid4().hex
    conversation.listener = Listener(identifier, now, now + window if window is not None else None)
    conversation.deaf_reason = ''
    return identifier


def alive(conversation, listener_id: str, now: float) -> bool:
    if conversation is None or conversation.listener is None:
        return False
    lease = conversation.listener
    return lease.id == listener_id and (lease.expires_at is None or now < lease.expires_at)


def availability(conversation, capabilities, now: float) -> Availability:
    if conversation is None or conversation.ended:
        return Availability(False, 'session ended' if conversation else 'not registered', True)
    if capabilities and capabilities.wake == 'push':
        return Availability(True)
    lease = conversation.listener
    if lease and (lease.expires_at is None or now < lease.expires_at):
        return Availability(True)
    return Availability(False, conversation.deaf_reason or 'no listener', True)
