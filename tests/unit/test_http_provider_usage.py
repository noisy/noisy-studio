import http.client
import json

from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState


def test_usage_http_boundary_accepts_registered_session_and_exposes_normalized_windows():
    state = ListenerState()
    state.conversations.adopt('c1', harness='claude-hooks')
    server = start_http_api(state, 0)
    client = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=3)
    try:
        client.request('POST', '/provider-usage', body=json.dumps({'provider': 'claude', 'conversation': 'c1', 'scope': 'a' * 64, 'data': {'five_hour': {'used_percentage': 71, 'resets_at': 9999999999}}}))
        response = client.getresponse()
        accepted = (response.status, json.loads(response.read()))
        client.request('GET', '/status')
        snapshot = json.loads(client.getresponse().read())
        assert {'accepted': accepted, 'windows': snapshot['provider_usage'][0]['windows']} == {
            'accepted': (200, {'accepted': True}),
            'windows': [{'label': 'Session', 'used_percent': 71, 'resets_at': 9999999999, 'stale': False}],
        }
    finally:
        client.close()
        server.shutdown()
        server.server_close()
