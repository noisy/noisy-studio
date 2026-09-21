"""A scriptable harness for tests.

`FakeSession` produces the payloads a real client would send, so one
driver feeds adapter tests, registry scenarios and HTTP integration
tests. `FakeHarness` interprets them; its capabilities are constructor
arguments, so a test can model a push harness, a deaf one, or one that
cannot spawn.
"""

from __future__ import annotations

import itertools

from noisy_studio.harness.hook_contract import Delivery, Interpretation
from noisy_studio.harness.base import (
    Capabilities,
    Event,
    HarnessError,
    Moment,
)

_ids = itertools.count(1)


class FakeSession:
    """Emits payloads for one conversation; ids rotate on demand."""

    def __init__(self, conversation: str | None = None, title: str = "") -> None:
        n = next(_ids)
        self.conversation = conversation or f"conv-{n}"
        self.session_id = f"sess-{n}-a"
        self.title = title
        self._rotations = 0

    def _payload(self, event: str, **fields) -> dict:
        return {
            "event": event,
            "conversation": self.conversation,
            "session_id": self.session_id,
            **fields,
        }

    def start(self, source: str = "startup") -> dict:
        return self._payload("session_started", source=source, title=self.title)

    def prompt(self) -> dict:
        return self._payload("turn_started")

    def tool(self, name: str = "Bash", participant: str | None = None) -> dict:
        return self._payload("tool", tool=name, participant=participant)

    def tool_done(self, participant: str | None = None) -> dict:
        return self._payload("tool_done", participant=participant)

    def speak(self) -> dict:
        return self._payload("tool", tool="speak")

    def stop(self) -> dict:
        return self._payload("turn_ended")

    def subagent_start(self, participant: str) -> dict:
        return self._payload("participant_started", participant=participant)

    def subagent_stop(self, participant: str) -> dict:
        return self._payload("participant_ended", participant=participant)

    def rename(self, title: str) -> dict:
        self.title = title
        return self._payload("title_changed", title=title)

    def rotate_id(self) -> str:
        """The agent system presents a new session id for the same conversation."""
        self._rotations += 1
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{chr(ord('a') + self._rotations)}"
        return self.session_id

    def end(self) -> dict:
        return self._payload("session_ended")


class FakeHarness:
    name = "fake"
    label = "Fake harness"

    def __init__(self, capabilities: Capabilities | None = None) -> None:
        self.capabilities = capabilities or Capabilities(
            wake="long_poll",
            max_idle_seconds=60.0,
            liveness="events",
            mid_turn_delivery=True,
            spawn=False,
        )

    def interpret(self, payload: dict) -> Interpretation:
        if not isinstance(payload, dict) or not payload.get("conversation"):
            raise HarnessError("fake payload names no conversation")
        key = str(payload["conversation"])
        aliases = (str(payload["session_id"]),) if payload.get("session_id") else ()
        participant = payload.get("participant") or None
        event = str(payload.get("event") or "")
        events: list[Event] = []
        may_drain = False
        listener = "none"
        speech_identity = None
        if event == "session_started":
            events.append(Event("session_started", key, aliases,
                                title=str(payload.get("title") or ""),
                                source=str(payload.get("source") or "")))
            listener = "start" if self.capabilities.wake == "long_poll" else "none"
        elif event == "tool":
            events.append(Event("activity", key, aliases, participant=participant,
                                detail=str(payload.get("tool") or "")))
            if payload.get("tool") == "speak":
                speech_identity = key
        elif event == "tool_done":
            events.append(Event("activity", key, aliases, participant=participant,
                                detail="THINKING…"))
            may_drain = participant is None
        elif event == "turn_ended":
            events.append(Event("turn_ended", key, aliases))
            listener = "start" if self.capabilities.wake == "long_poll" else "none"
        elif event in ("turn_started", "session_ended", "participant_started",
                       "participant_ended", "title_changed"):
            events.append(Event(event, key, aliases, participant=participant,
                                title=str(payload.get("title") or "")))
        else:
            raise HarnessError(f"fake payload has unknown event {event!r}")
        return Interpretation(
            conversation=key,
            events=tuple(events),
            may_drain=may_drain,
            speech_identity=speech_identity,
            listener=listener,
            short_id=key[-8:],
            participant=participant,
        )

    def deliver(self, messages: list[str], moment: Moment) -> Delivery:
        text = " ".join(messages)
        return Delivery(
            context=f"[FAKE {moment}] {text}",
            system_message=text,
            exit_code=2 if moment == "wake" and self.capabilities.wake == "long_poll" else 0,
        )
