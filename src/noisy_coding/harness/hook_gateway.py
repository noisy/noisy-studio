"""HTTP compatibility boundary for lifecycle-hook clients.

Hook formatting, identity injection instructions and polling decisions belong
here; the shared HTTP server only dispatches requests and persists app settings.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from noisy_coding import harness
from noisy_coding.harness.provider import Registration

if TYPE_CHECKING:
    from noisy_coding.listener.state import ListenerState

_ADAPTERS: dict[str, harness.Harness] = {}


def _adapter(name: str) -> harness.Harness:
    if name not in _ADAPTERS:
        _ADAPTERS[name] = harness.get(name)
    return _ADAPTERS[name]


def _apply_harness_event(
    state: ListenerState, name: str, payload: dict, listen_seconds: float | None = None
) -> dict:
    """Run one hook payload through its harness adapter and the registry.

    The registry is the source of truth for tabs; the legacy agent table in
    ListenerState is kept in step (same key) so speech routing, activity and
    the dashboard keep working while they migrate to /status.conversations.
    """
    adapter = _adapter(name)
    result = adapter.interpret(payload)
    registry = state.conversations
    conversation = registry.apply(name, result, adapter.capabilities)
    key = conversation.key
    provider = registry.providers.get(name)
    if provider is not None:
        provider.attach(Registration(key, str(payload.get("session_id") or key), participant=result.participant))
        provider.observe(result.events)
    if conversation.hidden:
        # The user closed this tab. Routine hooks from a still-running
        # session must not resurrect it; only a new session or a new user
        # turn does (registry.apply un-hides on those). Identity and drain
        # rules still apply - closing a tab does not change who speaks.
        return {
            "conversation": key,
            "may_drain": result.may_drain,
            "speech_identity": result.speech_identity,
            "listener": "none",
            "participant": result.participant,
            "label": conversation.label(),
        }
    already = key in state.agents
    state.register_agent(key, conversation.label())
    if not already:
        state.add_event("agent", f"'{conversation.label()}' registered ({adapter.label})")
    for event in result.events:
        if event.kind == "activity" and event.participant is None:
            state.set_activity(key, event.detail)
        elif event.kind == "turn_ended":
            state.set_activity(key, "")
        elif event.kind == "title_changed" and event.title:
            state.register_agent(key, event.title)
    response = {
        "conversation": key,
        "may_drain": result.may_drain,
        "speech_identity": result.speech_identity,
        "listener": result.listener,
        "participant": result.participant,
        "label": conversation.label(),
    }
    if result.listener in ("start", "poll"):
        window = adapter.capabilities.max_idle_seconds
        if listen_seconds is not None and window:
            # The hook may shorten (never lengthen) the harness window - a
            # Codex user picks how long the synchronous Stop holds the turn.
            window = max(0.0, min(float(listen_seconds), window))
        if window is not None and window <= 0:
            response["listener"] = "none"  # idle listening disabled by the hook
        else:
            response["listener_id"] = registry.listener_started(key, window=window)
            response["listen_seconds"] = window
            response["harness"] = name
    return response


def _render_for(state: ListenerState, key: str, messages: list[str], moment: str) -> dict | None:
    conversation = state.conversations.get(key)
    if conversation is None:
        return None
    try:
        adapter = _adapter(conversation.harness)
    except KeyError:
        return None
    delivery = adapter.deliver(messages, moment)  # type: ignore[arg-type]
    return {
        "context": delivery.context,
        "system_message": delivery.system_message,
        "exit_code": delivery.exit_code,
    }


def _render_delivery(state: ListenerState, key: str, transcripts: list[dict], moment: str) -> dict | None:
    if not transcripts:
        return None
    return _render_for(state, key, [t["text"] for t in transcripts], moment)


def drain(state: ListenerState, agent: str | None, listener_id: str | None) -> dict:
    provider = state.conversations.providers.for_conversation(agent or "")
    if provider is not None and not provider.allows_hook_pickup:
        return {"transcripts": [], "nudge": None, "stand_down": True}
    if listener_id and not state.conversations.listener_alive(agent or "", listener_id):
        return {"transcripts": [], "nudge": None, "stand_down": True}
    conversation = state.conversations.get(agent or "")
    hidden = bool(conversation and conversation.hidden)
    transcripts = [asdict(t) for t in state.drain(agent, touch=not hidden)]
    nudge = state.pop_due_nudge(agent) if agent else None
    moment = "wake" if listener_id else "mid_turn"
    return {
        "transcripts": transcripts,
        "nudge": nudge,
        "stand_down": False,
        "delivery": _render_delivery(state, agent or "", transcripts, moment),
    }
