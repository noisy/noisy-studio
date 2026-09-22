"""Grok lifecycle hooks -> the harness contract.

Grok has no agent inbox socket and no background wake. Its Stop hook is
synchronous, like Codex: while the listener polls, the turn stays open and
a waiting transcript is delivered as soon as it is queued. Two platform
limits stay inside this adapter instead of leaking into the daemon:

- after eight stop-hook continuations in one turn, Grok force-ends the
  turn and ignores the hook until the next typed message;
- an allowing UserPromptSubmit hook cannot attach context, so speech that
  arrives while no Stop listener is running waits for the next tool call.

Identity is the Grok session id. The payload is camelCase (`sessionId`,
`toolName`, `toolInput`) and also carries Claude's `hook_event_name`.
MCP tools are named `<server>__<tool>`, without Claude's `mcp__` prefix.
A subagent event carries `subagentType` and must not drain or listen:
Grok does not give the hook the parent's session id, so a child cannot
be reattached safely and must not open its own listening tab.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from noisy_studio.harness.base import Capabilities, Event, HarnessError, Moment
from noisy_studio.harness.hook_common import THINKING, activity_line, hook_delivery, is_identity_tool
from noisy_studio.harness.hook_contract import Delivery, Interpretation

# Upper bound for the synchronous Stop listener. The user picks the actual
# window (0 disables it); the daemon only shortens to this, never lengthens.
# Grok's own default Stop timeout is 600s and the hook timeout must be set
# above the chosen window. 3600 matches the Codex installer ceiling.
DEFAULT_LISTEN_SECONDS = 3600.0

_GROK_EVENTS = {
    "session_start": "SessionStart",
    "session_end": "SessionEnd",
    "user_prompt_submit": "UserPromptSubmit",
    "pre_tool_use": "PreToolUse",
    "post_tool_use": "PostToolUse",
    "stop": "Stop",
    "subagent_start": "SubagentStart",
    "subagent_stop": "SubagentStop",
}

_LISTEN_REASONS = {"", "end_turn"}
_SESSION_END_REASONS = {"channel_closed", "shutdown"}


def event_name(payload: dict) -> str:
    """Claude's PascalCase event name, which Grok sends beside its own."""
    explicit = str(payload.get("hook_event_name") or "").strip()
    if explicit:
        return explicit
    return _GROK_EVENTS.get(str(payload.get("hookEventName") or "").strip(), "")


def session_id_of(payload: dict) -> str:
    return str(payload.get("session_id") or payload.get("sessionId") or "").strip()


def tool_fields(payload: dict) -> tuple[str, dict]:
    name = str(payload.get("tool_name") or payload.get("toolName") or "").strip()
    arguments = payload.get("tool_input")
    if not isinstance(arguments, dict):
        arguments = payload.get("toolInput")
    if not isinstance(arguments, dict):
        arguments = {}
    return name, arguments


def participant_of(payload: dict) -> str | None:
    """A child agent inside this session, or None for the session itself.

    `agent_id` is accepted when a host sends one. Grok's own signal is
    `subagentType`, which is a role name rather than a stable id.
    """
    explicit = str(payload.get("agent_id") or payload.get("agentId") or "").strip()
    if explicit:
        return explicit
    kind = str(payload.get("subagentType") or payload.get("subagent_type") or "").strip()
    return kind or None


def title_from_summary(text: str) -> str:
    """The session's current name from Grok's summary.json, or ''."""
    try:
        row = json.loads(text) if text.strip() else {}
    except ValueError:
        return ""
    if not isinstance(row, dict):
        return ""
    for key in ("custom_title", "generated_title"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _read_summary(session_id: str, cwd: str) -> str:
    if not session_id or not cwd:
        return ""
    root = Path(os.environ.get("GROK_HOME") or Path.home() / ".grok")
    path = root / "sessions" / quote(cwd, safe="") / session_id / "summary.json"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


class GrokHooks:
    name = "grok-hooks"
    label = "Grok"

    def __init__(
        self,
        listen_seconds: float = DEFAULT_LISTEN_SECONDS,
        read_summary: Callable[[str, str], str] = _read_summary,
    ) -> None:
        self.capabilities = Capabilities(
            wake="long_poll",
            max_idle_seconds=listen_seconds,
            liveness="heuristic",
            mid_turn_delivery=True,
            spawn=True,
        )
        self._read_summary = read_summary

    def interpret(self, payload: dict) -> Interpretation:
        if not isinstance(payload, dict):
            raise HarnessError("hook input must be an object")
        session_id = session_id_of(payload)
        if not session_id:
            raise HarnessError("Grok hook payload names no session")
        name = event_name(payload)
        participant = participant_of(payload)
        tool_name, tool_input = tool_fields(payload)
        title = self._title(payload, session_id)
        events: list[Event] = []
        may_drain = False
        listener = "none"
        speech_identity = None

        def add(kind, **fields):
            events.append(Event(kind, session_id, (), participant=participant, **fields))

        if name == "SessionStart":
            add("session_started", source=str(payload.get("source") or ""), title=title)
        elif name == "SessionEnd":
            add("session_ended")
        elif name == "UserPromptSubmit":
            add("turn_started")
            add("activity", detail=THINKING)
        elif name == "PreToolUse":
            line = activity_line({"tool_name": tool_name, "tool_input": tool_input})
            if line:
                add("activity", detail=line)
            if is_identity_tool(tool_name):
                speech_identity = session_id
        elif name == "PostToolUse":
            add("activity", detail=THINKING)
            may_drain = participant is None
        elif name == "Stop":
            reason = str(payload.get("reason") or "")
            if participant:
                add("participant_ended")
            elif reason in _SESSION_END_REASONS:
                add("session_ended")
            elif reason in _LISTEN_REASONS:
                add("turn_ended")
                listener = "poll"
            else:
                add("activity", detail="")
        elif name == "SubagentStart":
            add("participant_started")
        elif name == "SubagentStop":
            add("participant_ended")
        else:
            add("activity", detail="")
        if name != "SessionStart":
            events.append(Event("title_changed", session_id, (), title=title))
        return Interpretation(
            conversation=session_id,
            events=tuple(events),
            may_drain=may_drain,
            speech_identity=speech_identity,
            listener=listener,
            short_id=session_id[:8],
            participant=participant,
        )

    def deliver(self, messages: list[str], moment: Moment) -> Delivery:
        return hook_delivery(messages, moment)

    def _title(self, payload: dict, session_id: str) -> str:
        explicit = str(payload.get("sessionTitle") or payload.get("session_title") or "").strip()
        if explicit:
            return explicit
        cwd = str(payload.get("cwd") or payload.get("workspaceRoot") or "")
        return title_from_summary(self._read_summary(session_id, cwd))
