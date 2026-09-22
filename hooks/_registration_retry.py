"""Bounded recovery inside Claude's asynchronous SessionStart hook."""
from __future__ import annotations

import os
import stat
import time
import uuid

import _client

RETRY_INTERVAL_SECONDS = 2.0
# SessionStart's async hook timeout is 14430 seconds; leave room to exit.
MAX_STARTUP_WAIT_SECONDS = 14400.0


def _socket_identity(path):
    try:
        info = os.lstat(path)
        if stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid():
            return info.st_dev, info.st_ino
    except (OSError, TypeError, ValueError):
        pass
    return None


def wait_for_daemon(body, listen_seconds=None):
    payload = body['payload']
    connection = payload.get('noisy_studio_connection')
    if (body['harness'] not in ('claude', 'claude-hooks')
            or payload.get('hook_event_name') != 'SessionStart'
            or payload.get('agent_id') or not isinstance(connection, dict)
            or connection.get('hook_protocol') != 2):
        return None
    try:
        uuid.UUID(payload.get('session_id', ''))
    except (ValueError, TypeError, AttributeError):
        return None
    path = connection.get('socket')
    identity = _socket_identity(path)
    if identity is None:
        return None
    window = MAX_STARTUP_WAIT_SECONDS if listen_seconds is None else min(
        MAX_STARTUP_WAIT_SECONDS, max(0, listen_seconds))
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        time.sleep(min(RETRY_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))
        if time.monotonic() >= deadline or _socket_identity(path) != identity:
            return None
        # Only replay registration, never a user prompt or a tool invocation.
        remaining = max(0, deadline - time.monotonic())
        reply = _client.post('/harness/event', {**body, 'listen_seconds': remaining})
        if reply is not None:
            # An explicit refusal is final; normal handling reports it.
            return reply
    return None
