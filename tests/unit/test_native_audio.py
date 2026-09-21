import base64
import io
import json
import wave
from unittest.mock import Mock

import pytest

from noisy_studio.listener import daemon, http_api
from noisy_studio.listener.microphone_sample import MicrophoneSample
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.state_stream import StateStream


def test_old_audio_settings_are_migrated_on_disk_once(tmp_path, monkeypatch):
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(http_api, 'SETTINGS_FILE', path)
    state = ListenerState()
    state.set_language('en')
    daemon.migrate_audio_settings(state, {'input_device': 'browser', 'output_device': 'browser'})
    saved = json.loads(path.read_text())
    assert (saved['input_device'], saved['language'], 'output_device' in saved) == ('', 'en', False)
    persist = Mock()
    monkeypatch.setattr(daemon, 'save_settings', persist)
    daemon.migrate_audio_settings(state, saved)
    persist.assert_not_called()


def test_state_websocket_refuses_obsolete_audio_connections():
    socket = Mock()
    socket.request.path = '/'
    stream = StateStream(lambda: {})
    stream._handle(socket)
    socket.close.assert_called_once_with(code=1008, reason='Only dashboard state updates are supported')
    socket.send.assert_not_called()


def test_state_websocket_still_delivers_dashboard_snapshots():
    socket = Mock()
    socket.request.path = '/state'
    socket.recv.side_effect = ConnectionError('closed')
    snapshot = {'type': 'snapshot', 'status': {'recording': False}, 'utterances': []}
    StateStream(lambda: snapshot)._handle(socket)
    assert json.loads(socket.send.call_args.args[0]) == snapshot


def test_native_sample_is_bounded_and_exports_mono_wav():
    now = [0.0]
    sample = MicrophoneSample(sample_rate=16000, clock=lambda: now[0])
    identifier = sample.start()
    sample.feed(b'\x01\x00' * 160)
    now[0] = 16
    sample.feed(b'\x02\x00' * 160)
    with wave.open(io.BytesIO(base64.b64decode(sample.finish(identifier)))) as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getnframes()) == (1, 16000, 160)


def test_late_cancel_cannot_discard_a_new_native_sample():
    sample = MicrophoneSample()
    previous = sample.start()
    sample.finish(previous, cancel=True)
    current = sample.start()
    sample.feed(b'\x01\x00' * 16)
    with pytest.raises(ValueError, match='no longer active'):
        sample.finish(previous, cancel=True)
    assert sample.finish(current)


def test_native_sample_endpoint_requires_pausing_and_returns_only_sample_audio():
    import http.client
    state = ListenerState()
    server = http_api.start_http_api(state, 0)
    def post(body):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=3)
        connection.request('POST', '/speech-settings/sample', json.dumps(body), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result
    try:
        assert post({'action': 'start'})[0] == 400
        state.set_user_muted(True)
        status, started = post({'action': 'start'})
        assert status == 200
        state.microphone_sample.feed(b'\x01\x00' * 160)
        status, finished = post({'action': 'finish', 'id': started['id']})
        assert status == 200 and finished['audio']
        assert state.snapshot_transcripts() == []
    finally:
        server.shutdown()
        server.server_close()
