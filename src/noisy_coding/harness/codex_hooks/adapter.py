"""Codex lifecycle hooks -> the harness contract.

Codex runs the same five hooks with the same stdin shape as Claude Code,
but its Stop hook is synchronous: while our listener polls, the turn is
not finished and anything the user types waits behind it. The user picks
the window length in codex.json (trade-off: long = wake by voice, short =
typed input never waits); when it lapses the tab shows as deaf. Identity is the Codex `session_id`;
there is no transcript path to key on.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from noisy_coding.harness.hook_contract import Delivery, Interpretation
from noisy_coding.harness.base import (
    Capabilities,
    Event,
    HarnessError,
    Moment,
)
from noisy_coding.harness.hook_common import (
    THINKING,
    activity_line,
    hook_delivery,
    is_identity_tool,
)

# Upper bound for the synchronous Stop listener. The USER picks the actual
# window in ~/.config/noisy-coding/codex.json (listen_seconds, 0-3600 per
# install_codex.py) and the hook passes it along; the daemon only ever
# shortens to this bound, never lengthens. It was 30 s once, which silently
# clamped a configured hour to half a minute and left the tab deaf while the
# user still expected it to hear them (2026-09-10).
DEFAULT_LISTEN_SECONDS = 3600.0
DEFAULT_LABEL = "Codex"
# Codex keeps thread names here (Codex Desktop and the TUI both write it):
# one JSON object per line, {"id", "thread_name", "updated_at"}, append-only,
# so the LAST line for an id is the current name. It is the Codex equivalent
# of Claude's /rename title in the transcript.
SESSION_INDEX = Path.home() / ".codex" / "session_index.jsonl"


def _read_session_index() -> str:
    try:
        return SESSION_INDEX.read_text(encoding="utf-8")
    except OSError:
        return ""


def thread_name_from_index(text: str, session_id: str) -> str:
    """The latest thread_name recorded for this thread id, or ''."""
    name = ""
    for line in text.splitlines():
        if session_id not in line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("id") == session_id and row.get("thread_name"):
            name = str(row["thread_name"])
    return name


class CodexHooks:
    name = "codex-hooks"
    label = "Codex"

    def __init__(
        self,
        listen_seconds: float = DEFAULT_LISTEN_SECONDS,
        agent_label: str = DEFAULT_LABEL,
        read_index: Callable[[], str] = _read_session_index,
    ) -> None:
        self.capabilities = Capabilities(
            wake="long_poll",
            max_idle_seconds=listen_seconds,
            liveness="heuristic",
            mid_turn_delivery=True,
            spawn=False,
        )
        self._agent_label = agent_label
        self._read_index = read_index

    def interpret(self, payload: dict) -> Interpretation:
        if not isinstance(payload, dict):
            raise HarnessError("hook input must be an object")
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            raise HarnessError("Codex hook payload names no session")
        key = session_id
        participant = str(payload.get("agent_id") or "").strip() or None
        event_name = str(payload.get("hook_event_name") or "")
        # The tab is named by the thread's own name: from the payload when a
        # client sends it, else from session_index.jsonl (Codex updates it on
        # /rename and on auto-titling).
        thread_name = (
            str(payload.get("thread_name") or "").strip()
            or thread_name_from_index(self._read_index(), session_id)
        )
        # The tab shows the thread's name and nothing else - no prefix, no
        # project, no id (Krzysztof, 2026-09-13). Until Codex has named the
        # thread the registry shows its neutral placeholder and keeps the
        # last known name after that.
        title = thread_name
        events: list[Event] = []
        may_drain = False
        listener = "none"
        speech_identity = None

        def add(kind, **fields):
            events.append(Event(kind, key, (), participant=participant, **fields))

        if event_name == "SessionStart":
            add("session_started", source=str(payload.get("source") or ""), title=title)
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
            listener = "poll"
        elif event_name == "SubagentStart":
            add("participant_started")
        elif event_name == "SubagentStop":
            add("participant_ended")
        else:
            add("activity", detail="")
        if event_name != "SessionStart":
            events.append(Event("title_changed", key, (), title=title))
        return Interpretation(
            conversation=key,
            events=tuple(events),
            may_drain=may_drain,
            speech_identity=speech_identity,
            listener=listener,
            short_id=session_id[:8],
            participant=participant,
        )

    def deliver(self, messages: list[str], moment: Moment) -> Delivery:
        return hook_delivery(messages, moment)
