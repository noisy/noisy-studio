#!/usr/bin/env python3
"""One flow for every hook event, for every hook-based harness.

    payload -> POST /harness/event -> do what the daemon says:
      speech_identity -> inject agent_id into the tool call (updatedInput)
      may_drain       -> deliver queued voice as context (PostToolUse)
      listener=start  -> background poll until voice or timeout (asyncRewake)
      listener=poll   -> foreground poll for a short window (synchronous Stop)

The daemon interprets the payload (which harness, which conversation, is
this a subagent, is there a title) and renders the delivery text; the hook
knows nothing about any of that. Stdlib only; python 3.9+.
"""

from __future__ import annotations

import json
import os
import sys
import time
from urllib.parse import quote

import _client

POLL_INTERVAL_SECONDS = 0.5
# After speech arrives, keep listening this long for a continuation before
# waking the model, so a longer musing isn't answered mid-thought.
GRACE_SECONDS = float(os.environ.get("NOISY_CODING_REWAKE_GRACE_SECONDS", "2.0"))
GRACE_CAP_SECONDS = 20.0
MAX_PREVIEW_CHARS = 220


def read_payload() -> dict:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def run(harness: str, payload: dict, listen_seconds: float | None = None) -> int:
    """Handle one hook invocation; returns the process exit code."""
    body = {"harness": harness, "payload": payload}
    if listen_seconds is not None:
        body["listen_seconds"] = listen_seconds
    reply = _client.post("/harness/event", body)
    event_name = str(payload.get("hook_event_name") or "")
    tool_name = str(payload.get("tool_name") or "")
    identity_call = event_name == "PreToolUse" and "noisy" in tool_name and (
        tool_name.endswith(("__speak", "__announce", "__change_voice", "__set_speaker_style", "__acknowledge_delivery"))
    )
    if reply is None or reply.get("status") == 404:
        return 0  # no daemon, or one too old to know this contract: never block
    if "error" in reply:
        # The daemon refused (no session identity, unknown harness). Speech
        # without identity would land on the wrong tab: block it and say why.
        message = f"noisy-coding: {reply['error']}"
        output: dict = {"systemMessage": message}
        if identity_call:
            output["hookSpecificOutput"] = {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            }
        print(json.dumps(output))
        return 0

    if event_name == "PreToolUse":
        return _pre_tool_use(payload, reply)
    if reply.get("registration_context") and event_name in ("SessionStart", "UserPromptSubmit"):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": event_name, "additionalContext": reply["registration_context"],
        }}))
    if reply.get("may_drain"):
        return _deliver_mid_turn(reply)
    if reply.get("nudge"):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse", "additionalContext": reply["nudge"],
        }}))
    listener = reply.get("listener")
    if listener in ("start", "poll") and reply.get("listener_id"):
        return _listen(reply)
    return 0


def _pre_tool_use(payload: dict, reply: dict) -> int:
    identity = reply.get("speech_identity")
    if not identity:
        return 0
    arguments = payload.get("tool_input")
    if not isinstance(arguments, dict):
        arguments = {}
    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            # Always overwrite model-supplied identity, including a forged one.
            "updatedInput": {**arguments, "agent_id": identity},
        }
    }
    text = str(arguments.get("text") or "").strip()
    if text:
        if len(text) > MAX_PREVIEW_CHARS:
            text = text[: MAX_PREVIEW_CHARS - 1] + "…"
        voice = str(arguments.get("voice_id") or "") or "voice"
        output["systemMessage"] = f"🔊 {voice}: „{text}”"
    print(json.dumps(output))
    return 0


def _drain(conversation: str, listener_id: str | None) -> dict | None:
    path = f"/drain?conversation={quote(conversation, safe='')}"
    if listener_id:
        path += f"&listener={listener_id}"
    return _client.get(path)


def _deliver_mid_turn(reply: dict) -> int:
    drained = _drain(reply["conversation"], None)
    if not drained:
        return 0
    delivery = drained.get("delivery")
    nudge = drained.get("nudge")
    if not delivery and not nudge:
        return 0
    parts = []
    output: dict = {}
    if delivery:
        output["systemMessage"] = delivery["system_message"]
        parts.append(delivery["context"])
    if nudge:
        parts.append(nudge)
    output["hookSpecificOutput"] = {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n\n".join(parts),
    }
    print(json.dumps(output))
    return 0


def _listen(reply: dict) -> int:
    conversation = reply["conversation"]
    listener_id = reply["listener_id"]
    window = float(reply.get("listen_seconds") or 0)
    if window <= 0:
        return 0
    deadline = time.time() + window
    while time.time() < deadline:
        drained = _drain(conversation, listener_id)
        if drained is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        if drained.get("stand_down"):
            return 0  # a newer listener took over - this one's job is done
        if drained.get("transcripts"):
            texts = [t["text"] for t in drained["transcripts"]]
            texts.extend(_collect_continuation(conversation, listener_id))
            return _wake(conversation, reply.get("harness", ""), texts, drained)
        time.sleep(POLL_INTERVAL_SECONDS)
    _client.post(
        "/harness/listener",
        {"conversation": conversation, "listener_id": listener_id, "reason": "timeout"},
        timeout=0.5,
    )
    return 0


def _collect_continuation(conversation: str, listener_id: str) -> list[str]:
    """Keep draining while the user is still talking (pauses < GRACE_SECONDS)."""
    parts: list[str] = []
    quiet_since = time.time()
    started = time.time()
    while (
        time.time() - quiet_since < GRACE_SECONDS
        and time.time() - started < GRACE_CAP_SECONDS
    ):
        time.sleep(POLL_INTERVAL_SECONDS)
        drained = _drain(conversation, listener_id)
        if drained and drained.get("transcripts"):
            parts.extend(t["text"] for t in drained["transcripts"])
            quiet_since = time.time()
        else:
            status = _client.get("/status", timeout=0.3) or {}
            if status.get("recording"):
                quiet_since = time.time()  # mid-sentence: VAD is still capturing
    return parts


def _wake(conversation: str, harness: str, texts: list[str], first_drain: dict) -> int:
    delivery = first_drain.get("delivery") or {}
    if len(texts) > len(first_drain.get("transcripts") or []):
        # More arrived during the grace window: ask the daemon to render the
        # whole utterance, so the model gets one message, not the first half.
        rendered = _client.post(
            "/harness/render",
            {"conversation": conversation, "messages": texts, "moment": "wake"},
            timeout=0.5,
        )
        if rendered and "context" in rendered:
            delivery = rendered
    if not delivery:
        spoken = " ".join(texts)
        delivery = {
            "context": f"[VOICE] The user said (spoken): {spoken}",
            "system_message": f"🎙️ Voice: „{spoken}”",
            "exit_code": 2,
        }
    # Waking the model resumes the turn - relight the activity line.
    _client.post("/activity", {"agent": conversation, "text": "THINKING…"}, timeout=0.3)
    print(json.dumps({"systemMessage": delivery["system_message"]}))
    print(delivery["context"], file=sys.stderr)
    return int(delivery.get("exit_code", 2))
