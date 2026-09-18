"""Local-only prepare/apply/preview smoke test against an isolated HTTP server."""
import base64
import http.client
import io
import json
import tempfile
import wave
from pathlib import Path

from noisy_coding import credentials, providers
from noisy_coding.listener.http_api import start_http_api
from noisy_coding.listener.state import ListenerState
from noisy_coding.providers import config, selection
from noisy_coding.providers.local import models_present


def main():
    if not models_present(tts=True, stt=True, options={'tts_engine': 'kokoro', 'stt_model':'base'}):
        raise SystemExit('Prepare Kokoro and Whisper base first; this test never downloads weights.')
    original_path = config.PROVIDERS_FILE
    original_key_reader = credentials.api_key
    credentials.api_key = lambda: ''  # Explicit keyless setup, confined to this process.
    with tempfile.TemporaryDirectory(prefix='speech-settings-test-') as directory:
        config.PROVIDERS_FILE = Path(directory) / 'providers.json'
        state = ListenerState()
        server = start_http_api(state, 0)
        connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=60)
        def post(path, payload):
            connection.request('POST', path, json.dumps(payload))
            response = connection.getresponse()
            body = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError(f'{path} returned {response.status}: {body.get("error")}')
            return body
        try:
            identities = sorted({c['voice'] for c in state.all_characters().values()} | set(state.voice_claims().values()) | {state.character()['voice']})
            candidate = selection.choice('kokoro:1')
            before = selection.active_choices()
            prepared = post('/speech-settings', {'operation': 'prepare', 'choice': 'kokoro:1'})
            assert prepared['active'] == before, 'Prepare changed the active engine'
            applied = post('/speech-settings', {'operation':'apply', 'choice':'kokoro:1', 'revision':selection.revision(), 'bindings':selection.assignments(candidate, identities)})
            assert applied['active'] == {'stt':'grok:stt', 'tts':'kokoro:1'}
            preview = post('/speech-settings/preview', {'choice':'kokoro:1', 'voice':'af_sarah'})
            with wave.open(io.BytesIO(base64.b64decode(preview['audio']))) as audio:
                result = {'prepare_preserved_selection': True, 'applied': applied['active'], 'preview_content_type':preview['content_type'], 'preview_sample_rate':audio.getframerate(), 'preview_seconds':round(audio.getnframes()/audio.getframerate(),3), 'agent_messages_queued':len(state.drain())}
            assert result['agent_messages_queued'] == 0
            post('/speech-settings', {'operation':'apply', 'choice':'whisper:base', 'revision':selection.revision(), 'bindings':{}})
            assert providers.direction_ready('stt') and providers.voice_ready(), 'Keyless local setup is not ready'
            result['keyless_local_ready'] = True
            result['final_selection'] = selection.active_choices()
            result['current_voice_labels'] = selection.active_voice_labels()
            Path(__file__).with_name('settings-api-results.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result))
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            config.PROVIDERS_FILE = original_path
            credentials.api_key = original_key_reader


if __name__ == '__main__':
    main()
