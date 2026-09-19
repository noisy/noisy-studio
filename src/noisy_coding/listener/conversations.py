"""The conversation registry: what the user sees as tabs, kept honest.

One entry per conversation, keyed by the harness-chosen key, with every
other id the harness ever presented for it as an alias - so a rotated
session id, a resumed session or a subagent's tool call all land on the
same tab instead of conjuring a new one. Liveness is derived from
lifecycle events and the listener lease, not from guessing at heartbeats;
the heuristic survives only for harnesses that declare it.

The registry knows nothing about HTTP, speech or the dashboard. The daemon
feeds it `Interpretation`s from a harness adapter and asks it questions.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from noisy_coding.harness.base import Capabilities, Interpretation
from noisy_coding.listener.identity import canonical_identity

__all__ = ["Conversation", "ConversationRegistry", "Listener", "Status"]

Status = Literal["live", "idle", "deaf", "ended", "unknown"]

# For harnesses with heuristic liveness only: activity newer than this
# means the agent is mid-turn even though no turn event told us so.
HEURISTIC_LIVE_SECONDS = 180.0


@dataclass
class Listener:
    id: str
    started_at: float
    expires_at: float | None  # None = push harness, never expires


@dataclass
class Conversation:
    key: str
    harness: str
    created_at: float
    position: int
    title: str = ""
    short_id: str = ""
    aliases: list[str] = field(default_factory=list)
    last_event_at: float = 0.0
    last_event_kind: str = ""
    last_activity: str = ""
    turn_open: bool = False
    ended: bool = False
    hidden: bool = False
    participants: dict[str, float] = field(default_factory=dict)
    listener: Listener | None = None
    deaf_reason: str = ""

    # What a tab is called before its session has any name of its own. A
    # tab never shows an id or a path (Krzysztof, 2026-09-13): the newest
    # real name wins, and until one exists this neutral text stands in.
    UNNAMED = "New conversation"

    def label(self) -> str:
        return self.title or self.UNNAMED


class ConversationRegistry:
    def __init__(
        self,
        clock: Callable[[], float] = time.time,
        path: Path | None = None,
    ) -> None:
        self._clock = clock
        self._path = path
        self._by_key: dict[str, Conversation] = {}
        self._alias: dict[str, str] = {}
        self._capabilities: dict[str, Capabilities] = {}
        if path is not None:
            self._load()

    # -- identity -----------------------------------------------------

    def resolve(self, presented: str) -> str | None:
        """The conversation key an id refers to, or None if unknown."""
        if not presented:
            return None
        if presented in self._by_key:
            return presented
        return self._alias.get(presented)

    def get(self, key: str) -> Conversation | None:
        return self._by_key.get(key)

    def keys(self) -> list[str]:
        return [c.key for c in sorted(self._by_key.values(), key=lambda c: c.position)]

    def visible_keys(self) -> list[str]:
        return [k for k in self.keys() if not self._by_key[k].hidden]

    # -- events -------------------------------------------------------

    def apply(
        self, harness: str, result: Interpretation, capabilities: Capabilities
    ) -> Conversation:
        now = self._clock()
        self._capabilities[harness] = capabilities
        conversation = self._by_key.get(result.conversation)
        if conversation is None:
            conversation = Conversation(
                key=result.conversation,
                harness=harness,
                created_at=now,
                position=self._next_position(),
                short_id=result.short_id,
            )
            self._by_key[conversation.key] = conversation
        if result.short_id and not conversation.short_id:
            conversation.short_id = result.short_id
        for event in result.events:
            for alias in event.aliases:
                if alias and alias != conversation.key:
                    self._alias[alias] = conversation.key
                    if alias not in conversation.aliases:
                        conversation.aliases.append(alias)
            conversation.last_event_at = now
            conversation.last_event_kind = event.kind
            if event.kind == "session_started":
                conversation.ended = False
                conversation.hidden = False
                if event.title:
                    conversation.title = event.title
            elif event.kind == "session_ended":
                conversation.ended = True
                conversation.turn_open = False
                conversation.listener = None
            elif event.kind == "turn_started":
                conversation.turn_open = True
                conversation.ended = False
                conversation.hidden = False  # the user is talking there again
            elif event.kind == "turn_ended":
                conversation.turn_open = False
            elif event.kind == "activity":
                conversation.last_activity = event.detail
                if event.participant:
                    conversation.participants[event.participant] = now
            elif event.kind == "title_changed":
                if event.title:
                    conversation.title = event.title
            elif event.kind == "participant_started" and event.participant:
                conversation.participants[event.participant] = now
            elif event.kind == "participant_ended" and event.participant:
                conversation.participants.pop(event.participant, None)
        self._save()
        return conversation

    def adopt(
        self, key: str, title: str = "", harness: str = "legacy", unhide: bool = True
    ) -> Conversation:
        """Register a conversation that arrived outside the harness contract
        (the legacy /register endpoint used by old hook scripts), so it is
        persisted like any other and survives a daemon restart. A real title
        updates the name; a fallback label (the key or its prefix) does not."""
        conversation = self._by_key.get(key)
        if conversation is None:
            conversation = Conversation(
                key=key, harness=harness, created_at=self._clock(),
                position=self._next_position(), short_id=key[:8],
            )
            self._by_key[conversation.key] = conversation
        if title and title != key and title != key[:8]:
            conversation.title = title
        if unhide:
            conversation.hidden = False
        conversation.last_event_at = self._clock()
        self._save()
        return conversation

    # -- listener lease -----------------------------------------------

    def listener_started(
        self, key: str, listener_id: str | None = None, window: float | None = None
    ) -> str:
        """A new listener takes over; whoever listened before is stale.

        `window` overrides the harness default lease (a hook may shorten it)."""
        conversation = self._require(key)
        capabilities = self._capabilities.get(conversation.harness)
        if window is None:
            window = capabilities.max_idle_seconds if capabilities else None
        now = self._clock()
        listener_id = listener_id or uuid.uuid4().hex
        conversation.listener = Listener(
            id=listener_id,
            started_at=now,
            expires_at=(now + window) if window is not None else None,
        )
        conversation.deaf_reason = ""
        self._save()
        return listener_id

    def listener_alive(self, key: str, listener_id: str) -> bool:
        """Is this listener the current, unexpired one? Stale ones stand down."""
        conversation = self._by_key.get(key)
        if conversation is None or conversation.listener is None:
            return False
        listener = conversation.listener
        if listener.id != listener_id:
            return False
        return listener.expires_at is None or self._clock() < listener.expires_at

    def listener_stopped(self, key: str, listener_id: str, reason: str = "") -> None:
        conversation = self._by_key.get(key)
        if conversation is None or conversation.listener is None:
            return
        if conversation.listener.id == listener_id:
            conversation.listener = None
            conversation.deaf_reason = reason
            self._save()

    # -- status -------------------------------------------------------

    def status(self, key: str) -> Status:
        conversation = self._by_key.get(key)
        if conversation is None:
            return "unknown"
        if conversation.ended:
            return "ended"
        now = self._clock()
        if conversation.turn_open:
            return "live"
        capabilities = self._capabilities.get(conversation.harness)
        if capabilities and capabilities.liveness == "heuristic":
            if conversation.last_activity and now - conversation.last_event_at <= HEURISTIC_LIVE_SECONDS:
                return "live"
        if capabilities and capabilities.wake == "push":
            return "idle"
        listener = conversation.listener
        if listener and (listener.expires_at is None or now < listener.expires_at):
            return "idle"
        return "deaf"

    def deaf_reason(self, key: str) -> str:
        conversation = self._by_key.get(key)
        if conversation is None:
            return ""
        if self.status(key) != "deaf":
            return ""
        return conversation.deaf_reason or "no listener"

    # -- order and visibility ----------------------------------------

    def reorder(self, keys: list[str]) -> None:
        """User-chosen order for the given keys; others keep relative order after them."""
        known = [k for k in keys if k in self._by_key]
        rest = [k for k in self.keys() if k not in known]
        for position, key in enumerate(known + rest):
            self._by_key[key].position = position
        self._save()

    def hide(self, key: str) -> bool:
        conversation = self._by_key.get(key)
        if conversation is None:
            return False
        conversation.hidden = True
        self._save()
        return True

    def unhide(self, key: str) -> bool:
        conversation = self._by_key.get(key)
        if conversation is None:
            return False
        conversation.hidden = False
        conversation.position = self._next_position()
        self._save()
        return True

    # -- snapshot -----------------------------------------------------

    def snapshot(self) -> dict:
        """Dashboard shape: everything a tab needs, keyed by conversation."""
        out = {}
        for key in self.keys():
            c = self._by_key[key]
            out[key] = {
                "label": c.label(),
                "title": c.title,
                "short_id": c.short_id,
                "harness": c.harness,
                "status": self.status(key),
                "deaf_reason": self.deaf_reason(key),
                "position": c.position,
                "hidden": c.hidden,
                "aliases": list(c.aliases),
                "participants": sorted(c.participants),
                "last_activity": c.last_activity,
                "last_event_at": c.last_event_at,
                "listening_until": c.listener.expires_at if c.listener else None,
            }
        return out

    # -- internals ----------------------------------------------------

    def _require(self, key: str) -> Conversation:
        conversation = self._by_key.get(key)
        if conversation is None:
            raise KeyError(f"unknown conversation {key!r}")
        return conversation

    def _next_position(self) -> int:
        return max((c.position for c in self._by_key.values()), default=-1) + 1

    def _save(self) -> None:
        if self._path is None:
            return
        data = {
            "conversations": [
                {**asdict(c), "listener": None} for c in self._by_key.values()
            ],
            "capabilities": {name: asdict(caps) for name, caps in self._capabilities.items()},
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data))
            tmp.replace(self._path)
        except OSError:
            pass

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())  # type: ignore[union-attr]
        except (OSError, ValueError):
            return
        for row in data.get("conversations", []):
            row = dict(row)
            row.pop("listener", None)
            try:
                conversation = Conversation(**row)
            except TypeError:
                continue
            # A listener from a previous daemon life is gone with it: the
            # tab starts deaf until its session's next hook says otherwise.
            conversation.deaf_reason = "daemon restarted"
            conversation.turn_open = False
            # Fold a path-keyed tab onto its session id (#107). Saved before
            # the adapter was fixed, such a tab has no title of its own, so
            # its key IS its label - which put an absolute path on screen
            # during a stream. The path stays as an alias so hooks that
            # still send it keep finding the same tab.
            identity = canonical_identity(conversation.key)
            if identity != conversation.key:
                if conversation.key not in conversation.aliases:
                    conversation.aliases.append(conversation.key)
                conversation.key = identity
            existing = self._by_key.get(conversation.key)
            if existing is not None:
                # Same session under both spellings: keep the one already
                # restored and inherit the twin's aliases rather than
                # letting one silently replace the other.
                for alias in conversation.aliases:
                    if alias not in existing.aliases:
                        existing.aliases.append(alias)
                    self._alias[alias] = existing.key
                continue
            self._by_key[conversation.key] = conversation
            for alias in conversation.aliases:
                self._alias[alias] = conversation.key
        for name, caps in data.get("capabilities", {}).items():
            try:
                self._capabilities[name] = Capabilities(**caps)
            except TypeError:
                continue
