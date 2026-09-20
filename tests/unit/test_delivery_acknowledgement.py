import http.client
import json

from noisy_coding.harness.claude.socket_transport import WriteResult
from noisy_coding.harness.hook_gateway import _apply_harness_event
from noisy_coding.listener.conversations import ConversationRegistry
from noisy_coding.listener.http_api import start_http_api
from noisy_coding.listener.state import ListenerState


def test_acknowledgement_during_send_confirms_only_its_session_and_is_not_downgraded(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    session1 = '00000000-0000-4000-8000-000000000001'
    session2 = '00000000-0000-4000-8000-000000000002'
    for session in (session1, session2):
        _apply_harness_event(state, 'claude-hooks', {
            'hook_event_name': 'SessionStart', 'session_id': session,
            'noisy_studio_connection': {'socket': str(tmp_path / 'inbox')},
        })
    delivery = state.conversations.providers.get('claude')._implementation
    delivery._clock = lambda: 10**12
    utterance = state.create_utterance('user', 'transcribing', agent=session1)
    state.add_transcript('Confirm just this message.', utterance)
    speech = delivery.journal.entries()[0][0]
    message_id = delivery.journal.key(speech)
    server = start_http_api(state, 0)
    responses = []

    def acknowledge(session):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=3)
        connection.request('POST', '/delivery/acknowledge', json.dumps({'agent': session, 'message_ids': [message_id]}))
        response = connection.getresponse()
        result = json.loads(response.read())
        connection.close()
        return result

    def send(_endpoint, _text):
        responses.append(acknowledge(session2))
        responses.append(acknowledge(session1))
        return WriteResult('sent', 'write complete')

    delivery._send = send
    try:
        delivery.flush(state.record_delivery, state.reserve_speech)
        repeated = acknowledge(session1)
    finally:
        server.shutdown()

    assert responses == [
        {'confirmed': [], 'unmatched': [message_id]},
        {'confirmed': [message_id], 'unmatched': []},
    ]
    assert repeated == responses[1]
    assert state.snapshot_transcripts() == []
    card = next(row for row in state.snapshot_utterances() if row['id'] == utterance)
    assert (card['delivery_state'], card['status']) == ('confirmed', 'delivery confirmed')
