"""Pieces shared by hook-based harnesses (Claude Code, Codex).

Both agent systems run the same five lifecycle hooks with the same stdin
shape and the same output contract (JSON on stdout to inject context,
exit 2 with stderr to wake). What differs is identity and capability, and
that lives in each adapter.
"""

from __future__ import annotations

import os
import re

from noisy_studio.harness.base import Delivery, Moment

# Canonical Studio tools, including dev and plugin-namespaced registrations.
IDENTITY_TOOLS = re.compile(
    r"^mcp__[^\s]*noisy[_-]studio[^\s]*__(speak|announce|change_voice|set_speaker_style|acknowledge_delivery)$"
)

THINKING = "THINKING…"

WAKE_INSTRUCTION = (
    "Treat this as his next message. Answer it now — aloud via the "
    "noisy-studio speak tool (briefly) and in text."
)
MID_TURN_INSTRUCTION = (
    "If it concerns what you are doing, take it into account; "
    "if it is clearly meant for someone else, say so instead of acting on it."
)


def is_identity_tool(tool_name: str) -> bool:
    return bool(IDENTITY_TOOLS.fullmatch(str(tool_name or "")))


def activity_line(payload: dict) -> str:
    """One human line describing a tool call, e.g. 'Edit · App.vue'."""
    tool = str(payload.get("tool_name", "")).strip()
    if not tool:
        return ""
    params = payload.get("tool_input") or {}
    if not isinstance(params, dict):
        params = {}
    if is_identity_tool(tool):
        action = tool.rsplit("__", 1)[-1]
        spoken = str(params.get("text") or "").strip()
        if action in ("speak", "announce") and spoken:
            return f"SPEAKING · „{spoken[:60]}”"
        return action.upper().replace("_", " ")
    path = params.get("file_path") or params.get("path") or params.get("notebook_path")
    if path:
        return f"{tool} · {os.path.basename(str(path))}"
    for key in ("command", "description", "pattern", "query", "prompt"):
        value = str(params.get(key) or "").strip()
        if value:
            return f"{tool} · {value[:70]}"
    return tool


def hook_delivery(messages: list[str], moment: Moment) -> Delivery:
    """The hook output contract shared by Claude Code and Codex."""
    spoken = " ".join(m.strip() for m in messages if m and m.strip())
    system_message = f"🎙️ Voice: „{spoken}”"
    if moment == "wake":
        return Delivery(
            context=f"[VOICE] The user said (spoken): {spoken}\n{WAKE_INSTRUCTION}",
            system_message=system_message,
            exit_code=2,
        )
    return Delivery(
        context=(
            f"[VOICE] The user just said (spoken, while you work): {spoken}\n"
            f"{MID_TURN_INSTRUCTION}"
        ),
        system_message=system_message,
        exit_code=0,
    )
