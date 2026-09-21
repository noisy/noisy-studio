"""Claude Code lifecycle hooks -> the harness contract.

Facts this adapter relies on (verified 2026-09-10 on Claude Code 2.1.267,
see docs/agent-integration-analysis.md §10):

- every hook payload carries `session_id`, `transcript_path`, `cwd`,
  `hook_event_name`; SessionStart adds `source` and maybe `session_title`;
- a subagent's hooks carry the PARENT's `session_id` and `transcript_path`
  plus its own `agent_id`/`agent_type` - so a subagent is a participant of
  the parent's conversation, and must never drain its queue;
- `session_id` is the canonical conversation key; the transcript path is
  an alias, never a display name;
- SessionStart and Stop both accept `asyncRewake`, so a listener can start
  at second zero and after every turn.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from noisy_studio.harness.hook_contract import Delivery, Interpretation
from noisy_studio.harness.base import (
    Capabilities,
    Event,
    HarnessError,
    Moment,
)
from noisy_studio.harness.hook_common import (
    THINKING,
    activity_line,
    hook_delivery,
    is_identity_tool,
)

# How long the Stop-hook listener waits for voice before it expires. The
# registered hook timeout must exceed this (install adds slack).
DEFAULT_LISTEN_SECONDS = 14400.0  # 4h; U1 showed no platform cap, deaf state covers the rest


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def title_from_transcript(text: str) -> str:
    """The session's current name from its transcript, or ''.

    A /rename title (customTitle) always wins. Without one, Claude Code's
    own auto-generated summary title (the name shown in /resume) is the
    name. Latest row of each kind wins.
    """
    custom = ""
    summary = ""
    for line in text.splitlines():
        if '"customTitle"' in line or '"session-title"' in line:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            custom = str(row.get("customTitle") or row.get("title") or custom)
        elif '"type": "summary"' in line or '"type":"summary"' in line:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "summary" and row.get("summary"):
                summary = str(row["summary"])
    return custom or summary


class ClaudeHooks:
    name = "claude-hooks"
    label = "Claude Code"

    def __init__(
        self,
        listen_seconds: float = DEFAULT_LISTEN_SECONDS,
        read_text: Callable[[str], str] = _read_file,
    ) -> None:
        self.capabilities = Capabilities(
            wake="long_poll",
            max_idle_seconds=listen_seconds,
            liveness="heuristic",
            mid_turn_delivery=True,
            spawn=True,
        )
        self._read_text = read_text

    def interpret(self, payload: dict) -> Interpretation:
        if not isinstance(payload, dict):
            raise HarnessError("hook input must be an object")
        session_id = str(payload.get("session_id") or "").strip()
        transcript = str(payload.get("transcript_path") or "").strip()
        if not session_id and not transcript:
            raise HarnessError("Claude hook payload names no session")
        # THE SESSION ID IS CANONICAL (#107). It used to be the other way
        # round, and a session then existed under two names at once - the
        # hooks register by session_id, this adapter registered by path -
        # so the voice ledger, the character buckets and the tab list each
        # held two entries for one human. The path is derived and leaks a
        # directory layout into user-visible labels, so it is an alias.
        key = session_id or transcript
        aliases = (transcript,) if transcript and transcript != key else ()
        participant = str(payload.get("agent_id") or "").strip() or None
        event_name = str(payload.get("hook_event_name") or "")
        title = self._title(payload, transcript)
        events: list[Event] = []
        may_drain = False
        listener = "none"
        speech_identity = None

        def add(kind, **fields):
            events.append(Event(kind, key, aliases, participant=participant, **fields))

        if event_name == "SessionStart":
            add("session_started", source=str(payload.get("source") or ""), title=title)
            listener = "start"
        elif event_name == "SessionEnd":
            add("session_ended")
        elif event_name == "UserPromptSubmit":
            add("turn_started")
            add("activity", detail=THINKING)
        elif event_name == "PreToolUse":
            line = activity_line(payload)
            if line:
                add("activity", detail=line)
            if is_identity_tool(payload.get("tool_name", "")):
                speech_identity = key
        elif event_name == "PostToolUse":
            add("activity", detail=THINKING)
            may_drain = participant is None
        elif event_name == "Stop":
            add("turn_ended")
            listener = "start"
        elif event_name == "SubagentStart":
            add("participant_started")
        elif event_name == "SubagentStop":
            add("participant_ended")
        else:
            add("activity", detail="")
        if title and event_name != "SessionStart":
            events.append(Event("title_changed", key, aliases, title=title))
        return Interpretation(
            conversation=key,
            events=tuple(events),
            may_drain=may_drain,
            speech_identity=speech_identity,
            listener=listener,
            short_id=session_id[:8] if session_id else key[-8:],
            participant=participant,
        )

    def deliver(self, messages: list[str], moment: Moment) -> Delivery:
        return hook_delivery(messages, moment)

    def _title(self, payload: dict, transcript: str) -> str:
        explicit = str(payload.get("session_title") or "").strip()
        if explicit:
            return explicit
        if transcript:
            return title_from_transcript(self._read_text(transcript))
        return ""
