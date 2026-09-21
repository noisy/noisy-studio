#!/usr/bin/env python3
"""Stdlib HTTP client shared by the hook scripts.

Hooks are thin: they read the payload the agent system hands them, send it
to the daemon, and do exactly what the daemon says. Every call fails open -
a daemon that is down or does not understand us must never block a tool
call or a turn.
"""

from __future__ import annotations

import _environment as environment
import json
import os
import urllib.error
import urllib.request

PORT = environment.get("NOISY_CODING_LISTENER_PORT", "8765")
BASE_URL = f"http://127.0.0.1:{PORT}"


def post(path: str, body: dict, timeout: float = 1.0) -> dict | None:
    """POST JSON; the decoded reply, or None when the daemon is unreachable.

    A 4xx reply is returned as {"error": ..., "status": code} so callers can
    tell "the daemon refused" from "there is no daemon".
    """
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error)
        except ValueError:
            detail = {}
        return {"error": str(detail.get("error") or error.reason), "status": error.code}
    except Exception:
        return None


def get(path: str, timeout: float = 0.5) -> dict | None:
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None


def event(kind: str, detail: str) -> None:
    """Best-effort line in the daemon's event log."""
    post("/event", {"kind": kind, "detail": detail}, timeout=0.3)
