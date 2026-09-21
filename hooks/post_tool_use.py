#!/usr/bin/env python3
"""PostToolUse hook: deliver queued voice transcripts to the model mid-work.

Fails open (silent exit) whenever the listener daemon is not running.
"""

from __future__ import annotations

import _environment as environment
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _agent_identity import identity  # noqa: E402

PORT = environment.get("NOISY_CODING_LISTENER_PORT", "8765")


def _activity_line(hook_input: dict) -> str:
    """One human line describing the tool call, e.g. 'Edit · App.vue'."""
    tool = str(hook_input.get("tool_name", "")).strip()
    if not tool:
        return ""
    params = hook_input.get("tool_input") or {}
    speech_prefix = next(
        (p for p in ("mcp__noisy-studio__", "mcp__noisy-coding__") if tool.startswith(p)),
        "",
    )
    if speech_prefix:
        # Claude's own speech: name the act, not the plumbing. This line is
        # what explains a transcript stuck AWAITING — the speak call blocks
        # through synthesis AND playback, and it fires BEFORE the daemon
        # even creates the voice card.
        action = tool[len(speech_prefix):]
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


def _post_activity(agent: str, text: str) -> None:
    """Best-effort live-activity update for the dashboard."""
    body = json.dumps({"agent": agent, "text": text}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/activity", data=body, method="POST"
    )
    try:
        urllib.request.urlopen(request, timeout=0.3).close()
    except Exception:
        pass


def main() -> None:
    raw = sys.stdin.read()
    try:
        hook_input = json.loads(raw) if raw.strip() else {}
    except ValueError:
        hook_input = {}
    agent, _label = identity(hook_input)
    # The tool just FINISHED — between tools the model is reasoning (or
    # waiting on the API; indistinguishable from outside). The pre-tool
    # hook overwrites this with the concrete tool line when work resumes.
    _post_activity(agent, "THINKING…")
    drain_url = f"http://127.0.0.1:{PORT}/drain?agent={agent}"
    try:
        with urllib.request.urlopen(drain_url, timeout=0.5) as response:
            payload = json.load(response)
            transcripts = payload["transcripts"]
            # Narration nudge (#16): the daemon's reminder that this agent
            # has been working silently past its talkative budget.
            nudge = payload.get("nudge")
    except Exception:
        return
    if not transcripts and not nudge:
        return

    context_parts = []
    output: dict = {}
    if transcripts:
        spoken = " ".join(t["text"] for t in transcripts)
        output["systemMessage"] = f"🎙️ Voice: „{spoken}”"
        context_parts.append(
            f"[VOICE] The user just said (spoken, while you work): {spoken}\n"
            "If this asks you to stop or change course, do so now; "
            "otherwise incorporate it and continue."
        )
    if nudge:
        context_parts.append(nudge)
    output["hookSpecificOutput"] = {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n\n".join(context_parts),
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
