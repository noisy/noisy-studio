"""One bounded inbox write. A successful write is never a delivery receipt."""
from dataclasses import dataclass
import json
import os
import socket
import stat
import uuid


@dataclass(frozen=True)
class Endpoint:
    session_id: str
    path: str


@dataclass(frozen=True)
class WriteResult:
    state: str
    detail: str


TIMEOUT_SECONDS = 3.0


def validate(endpoint: Endpoint) -> WriteResult | None:
    try:
        if str(uuid.UUID(endpoint.session_id)) != endpoint.session_id.lower():
            raise ValueError
    except (ValueError, AttributeError):
        return WriteResult('rejected', 'invalid full session identity')
    if not hasattr(socket, 'AF_UNIX') or not hasattr(os, 'getuid'):
        return WriteResult('unavailable', 'inbox delivery is not supported on this platform')
    try:
        metadata = os.lstat(endpoint.path)
        if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid():
            return WriteResult('rejected', 'inbox is not a socket owned by the current user')
    except OSError:
        return WriteResult('unavailable', 'inbox endpoint is unavailable; re-register the session')
    return None


def send(endpoint: Endpoint, text: str) -> WriteResult:
    invalid = validate(endpoint)
    if invalid:
        return invalid
    frame = {'type': 'user', 'session_id': endpoint.session_id,
             'message': {'role': 'user', 'content': text}}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(TIMEOUT_SECONDS)
        try:
            connection.connect(endpoint.path)
        except OSError:
            return WriteResult('unavailable', 'inbox connection failed; re-register the session')
        try:
            connection.sendall((json.dumps(frame, ensure_ascii=False) + '\n').encode('utf-8'))
        except OSError:
            return WriteResult('uncertain', 'inbox write interrupted; may have arrived; not retried')
    return WriteResult('sent', 'written to inbox; unconfirmed; host may hold or refuse it')
