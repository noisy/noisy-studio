"""The MCP server carries no identity of its own.

Since the overhaul, speech identity is supplied per call by the trusted
host hook (PreToolUse rewrites `agent_id`); the server never derives it
from cwd or the environment, on any harness. A call without `agent_id`
means the hook did not run: fail closed, never guess a tab.
"""

import json

import httpx
import pytest
import respx

from noisy_studio import server


@pytest.mark.asyncio
@respx.mock
async def test_acknowledgement_uses_injected_session_and_preserves_message_ids(monkeypatch):
    monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", "12345")
    message_ids = ['a' * 64, 'b' * 64]
    route = respx.post("http://127.0.0.1:12345/delivery/acknowledge").mock(
        return_value=httpx.Response(200, json={"confirmed": message_ids, "unmatched": []}))

    await server.acknowledge_delivery(message_ids, agent_id="session-1")

    assert json.loads(route.calls[0].request.content) == {"agent": "session-1", "message_ids": message_ids}


@pytest.mark.asyncio
@respx.mock
async def test_speak_routes_by_the_injected_identity_only(monkeypatch):
    monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", "12345")
    # Even a stale environment identity must not leak into routing.
    monkeypatch.setenv("NOISY_STUDIO_AGENT_NAME", "forged")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "also-forged")
    route = respx.post("http://127.0.0.1:12345/speak").mock(
        return_value=httpx.Response(200, json={"voice": "test"}))

    await server.speak("A", agent_id="codex-a")
    await server.announce("B", agent_id="codex-b")
    await server.speak("A again", agent_id="codex-a")

    assert [json.loads(call.request.content) for call in route.calls] == [
        {"text": "A", "interrupt": False, "wait": True, "agent": "codex-a"},
        {"text": "B", "wait": False, "agent": "codex-b"},
        {"text": "A again", "interrupt": False, "wait": True, "agent": "codex-a"},
    ]


@pytest.mark.asyncio
@respx.mock
async def test_speak_without_injected_identity_fails_closed(monkeypatch):
    monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", "12345")
    monkeypatch.setenv("NOISY_STUDIO_AGENT_NAME", "forged")  # must be ignored
    speak = respx.post("http://127.0.0.1:12345/speak").mock(
        return_value=httpx.Response(200, json={"voice": "x"}))
    event = respx.post("http://127.0.0.1:12345/event").mock(
        return_value=httpx.Response(200, json={"ok": True}))

    result = await server.speak("never route this by cwd")

    assert "identity is missing" in result
    assert not speak.calls  # nothing was spoken
    assert json.loads(event.calls[0].request.content)["kind"] == "voice_identity_error"


@pytest.mark.asyncio
@respx.mock
async def test_change_voice_uses_the_injected_identity(monkeypatch):
    monkeypatch.setenv("NOISY_STUDIO_AGENT_NAME", "forged")
    monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", "12345")
    route = respx.post("http://127.0.0.1:12345/voice").mock(
        return_value=httpx.Response(200, json={"voice": "test"}))

    await server.change_voice("test", agent_id="codex-session")

    assert json.loads(route.calls[0].request.content) == {"voice_id": "test", "agent": "codex-session"}


@pytest.mark.asyncio
@respx.mock
async def test_change_voice_without_identity_fails_closed(monkeypatch):
    monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", "12345")
    respx.post("http://127.0.0.1:12345/event").mock(return_value=httpx.Response(200, json={"ok": True}))
    voice = respx.post("http://127.0.0.1:12345/voice").mock(
        return_value=httpx.Response(200, json={"voice": "x"}))

    result = await server.change_voice("test")

    assert "identity is missing" in result
    assert not voice.calls


def test_the_server_derives_no_identity_of_its_own():
    # The cwd-map / env-name guessing helpers are gone for good.
    assert not hasattr(server, "_agent_name")
    assert not hasattr(server, "_cwd_agent")
    assert not hasattr(server, "_register_agent")
    assert not hasattr(server, "_SESSIONS_MAP")
