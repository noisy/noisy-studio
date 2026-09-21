#!/usr/bin/env python3
"""Shared helper: derive this Claude session's agent identity for the hooks.

Per-session multi-agent: a session's identity is its session_id (stable,
unique, given to every hook on stdin). Its human label is the /rename title
found in the transcript. An explicit NOISY_CODING_AGENT_NAME still wins, so the
old per-config setup keeps working.

The MCP server can't see session_id, so the hook also writes a
cwd -> {agent, title} mapping to a file the server reads by its own cwd.
"""

from __future__ import annotations

import _environment as environment
import json
import os
import urllib.request
from pathlib import Path

MAP_FILE = Path.home() / ".config" / "noisy-coding" / "sessions.json"
PORT = environment.get("NOISY_CODING_LISTENER_PORT", "8765")


def _register(agent: str, label: str) -> None:
    """Tell the daemon this agent exists (idempotent), so it shows in the UI."""
    try:
        body = json.dumps({"name": agent, "label": label}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/register", data=body, method="POST"
        )
        urllib.request.urlopen(req, timeout=0.5).read()
    except OSError:
        pass


def _title_from_transcript(path: str) -> str:
    """Latest session-title (a.k.a. customTitle) in the transcript, or ''."""
    title = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if '"customTitle"' not in line and '"session-title"' not in line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                title = row.get("customTitle") or row.get("title") or title
    except OSError:
        pass
    return title


def identity(hook_input: dict) -> tuple[str, str]:
    """Return (agent_id, label) for this session.

    agent_id: NOISY_CODING_AGENT_NAME if set, else the session_id.
    label:    the session's /rename title if any, else a short agent_id.
    """
    env_name = environment.get("NOISY_CODING_AGENT_NAME", "").strip()
    session_id = str(hook_input.get("session_id", "") or "")
    agent_id = env_name or session_id or "default"

    label = (environment.get("NOISY_CODING_SESSION_TITLE", "").strip()
             if environment.get("NOISY_CODING_HARNESS") == "codex" else env_name)
    if not label:
        # An explicit integration title can be used when the transcript is unavailable.
        label = environment.get("NOISY_CODING_SESSION_TITLE", "").strip()
    if not label:
        label = _title_from_transcript(hook_input.get("transcript_path", ""))
    if not label:
        label = agent_id[:8] if session_id else agent_id

    # Let the MCP server (which has no session_id) find its agent by cwd.
    cwd = str(hook_input.get("cwd", "") or "")
    if cwd and environment.get("NOISY_CODING_HARNESS") != "codex":
        try:
            MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if MAP_FILE.exists():
                data = json.loads(MAP_FILE.read_text())
            data[cwd] = {"agent": agent_id, "label": label}
            MAP_FILE.write_text(json.dumps(data))
        except (OSError, ValueError):
            pass
    _register(agent_id, label)
    return agent_id, label
