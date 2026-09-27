"""Read-only official quota collection. Never starts a model turn or reads credentials."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time


def connection_scope(provider):
    variable = 'CODEX_HOME' if provider == 'codex' else 'CLAUDE_CONFIG_DIR'
    default = '.codex' if provider == 'codex' else '.claude'
    profile = os.path.abspath(os.path.expanduser(os.environ.get(variable, str(Path.home() / default))))
    return hashlib.sha256(f'{provider}:{profile}'.encode()).hexdigest()


def read_codex_limits(command, timeout=20):
    """Use app-server's initialize handshake and read RPC, with no turn RPCs."""
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    pending = b''
    received = 0
    def send(message):
        process.stdin.write(json.dumps(message).encode() + b'\n')
        process.stdin.flush()
    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'noisy_studio_usage', 'version': '1.0.0'}}})
        while time.monotonic() < deadline:
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            block = os.read(process.stdout.fileno(), 65536)
            if not block:
                break
            received += len(block)
            if received > 1024 * 1024:
                break
            pending += block
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(message, dict):
                    continue
                if message.get('id') == 1:
                    if 'error' in message:
                        return None
                    send({'method': 'initialized'})
                    send({'id': 2, 'method': 'account/rateLimits/read', 'params': None})
                elif message.get('id') == 2:
                    result = message.get('result')
                    return result if isinstance(result, dict) else None
    finally:
        selector.close()
        process.stdin.close()
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdout.close()
    return None


def schedule_codex(conversation):
    executable = shutil.which('codex')
    if not executable:
        return
    scope = connection_scope('codex')
    # Scope includes daemon endpoint: one instance must not suppress another.
    import _client
    name = hashlib.sha256(f'{scope}:{_client.BASE_URL}'.encode()).hexdigest()
    stamp = Path(tempfile.gettempdir()) / f'noisy-usage-{name}.lock'
    try:
        if stamp.exists() and time.time() - stamp.stat().st_mtime > 60:
            stamp.unlink(missing_ok=True)
        descriptor = os.open(stamp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except OSError:
        return
    subprocess.Popen([sys.executable, __file__, executable, conversation, _client.BASE_URL], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def main():
    import _client
    if len(sys.argv) > 3:
        _client.BASE_URL = sys.argv[3]  # Exact resolved endpoint used by the registering hook.
    try:
        data = read_codex_limits([sys.argv[1], 'app-server'])
        if data is not None:
            _client.post('/provider-usage', {'provider': 'codex', 'conversation': sys.argv[2],
                         'scope': connection_scope('codex'), 'data': data})
    except (OSError, ValueError, BrokenPipeError):
        pass


if __name__ == '__main__':
    main()
