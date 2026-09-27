#!/usr/bin/env python3
"""Forward official statusline quota fields, optionally preserving an existing command.

Configure explicitly as a statusline command; this script never edits Claude config.
Pass the existing command after -- as arguments, not an interpreted shell string.
"""
import json
import subprocess
import sys

import _client
from _provider_usage import connection_scope


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and isinstance(payload.get('rate_limits'), dict) and payload.get('session_id'):
            _client.post('/provider-usage', {'provider': 'claude', 'conversation': payload['session_id'],
                         'scope': connection_scope('claude'), 'data': payload['rate_limits']}, timeout=0.3)
    except (ValueError, OSError):
        pass
    args = sys.argv[1:]
    if args and args[0] == '--':
        args = args[1:]
    if args:
        # Existing output passes straight through; no credentials/config inspection.
        try:
            subprocess.run(args, input=raw, text=True, check=False)
        except OSError:
            pass


if __name__ == '__main__':
    main()
