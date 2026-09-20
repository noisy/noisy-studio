"""HTTP compatibility boundary for lifecycle-hook clients.

Hook formatting, identity injection instructions and polling decisions belong
here; the shared HTTP server only dispatches requests and persists app settings.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from noisy_coding import harness
from noisy_coding.harness.provider import Registration, Speech

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
        connection = payload.get("noisy_studio_connection") if payload.get("hook_event_name") in ("SessionStart", "UserPromptSubmit") else None
        provider.attach(Registration(key, str(payload.get("session_id") or key), connection=connection, participant=result.participant))
        registry._readiness[conversation.harness] = provider.availability
        if not provider.allows_hook_pickup:
            conversation.listener = None
        provider.observe(result.events)
        if connection is not None and result.participant is None and not provider.allows_hook_pickup:
            for item in state.snapshot_transcripts():
                if item["addressee"] == key and item.get("delivery_state", "queued") in ("queued", "unavailable"):
                    state.submit_speech(Speech(item["utterance_id"], key, item["text"], item["timestamp"]))
    if conversation.hidden:
        # The user closed this tab. Routine hooks from a still-running
        # session must not resurrect it; only a new session or a new user
        # turn does (registry.apply un-hides on those). Identity and drain
        # rules still apply - closing a tab does not change who speaks.
        return {
            "conversation": key,
            "may_drain": result.may_drain and (provider is None or provider.allows_hook_pickup),
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
        "may_drain": result.may_drain and (provider is None or provider.allows_hook_pickup),
        "speech_identity": result.speech_identity,
        "listener": result.listener if provider is None or provider.allows_hook_pickup else "none",
        "participant": result.participant,
        "label": conversation.label(),
    }
    if (payload.get('hook_event_name') == 'UserPromptSubmit' and result.participant is None
            and provider is not None and provider.accept_wake(key, payload.get('prompt'))):
        picked_up = drain(state, key, None)
        response['wake_delivery'] = picked_up.get('delivery')
        response['suppress_empty_wake'] = not bool(picked_up.get('delivery'))
    if (payload.get("hook_event_name") == "PostToolUse" and result.participant is None
            and provider is not None and not provider.allows_hook_pickup):
        response["nudge"] = state.pop_due_nudge(key)
    if (payload.get("hook_event_name") in ("SessionStart", "UserPromptSubmit")
            and result.participant is None and provider is not None and provider.registration_context):
        response["registration_context"] = provider.registration_context
    if response["listener"] in ("start", "poll"):
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
    if agent is None and any(not state.conversations.providers.for_conversation(key).allows_hook_pickup
                             for key in state.conversations.keys()
                             if state.conversations.providers.for_conversation(key) is not None):
        return {"transcripts": [], "nudge": None, "stand_down": True}
    if provider is not None and not provider.allows_hook_pickup:
        return {"transcripts": [], "nudge": None, "stand_down": True}
    if listener_id and not state.conversations.listener_alive(agent or "", listener_id):
        return {"transcripts": [], "nudge": None, "stand_down": True}
    conversation = state.conversations.get(agent or "")
    hidden = bool(conversation and conversation.hidden)
    if provider is not None:
        pending = [Speech(t['utterance_id'], t['addressee'], t['text'], t['timestamp'])
                   for t in state.snapshot_transcripts()
                   if t['addressee'] == agent and t.get('delivery_state', 'queued') in ('queued', 'unavailable')]
        try:
            provider.prepare_hook_pickup(pending)
        except Exception:
            return {"transcripts": [], "nudge": None, "stand_down": True}
    transcripts = [asdict(t) for t in state.drain(agent, touch=not hidden)]
    if provider is not None and transcripts:
        for item in transcripts:
            state.update_utterance(item['utterance_id'], delivery_state='confirmed',
                                   delivery_detail='Handed to the receiving hook.')
        try:
            provider.complete_hook_pickup([Speech(t['utterance_id'], t['addressee'], t['text'], t['timestamp']) for t in transcripts])
        except Exception:
            # The pre-pickup claim is already durable; never replay on failure.
            state.add_event('delivery_storage_error', 'Hook pickup completed; its final receipt could not be saved')
    nudge = state.pop_due_nudge(agent) if agent else None
    moment = "wake" if listener_id else "mid_turn"
    return {
        "transcripts": transcripts,
        "nudge": nudge,
        "stand_down": False,
        "delivery": _render_delivery(state, agent or "", transcripts, moment),
    }
