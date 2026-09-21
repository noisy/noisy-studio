from unittest.mock import Mock

import pytest

from noisy_studio.harness.claude.journal import Journal
from noisy_studio.harness.claude.socket_delivery import SocketDelivery
from noisy_studio.harness.claude.socket_transport import WriteResult
from noisy_studio.harness.provider import Registration, Speech

SESSION_1 = '00000000-0000-4000-8000-000000000001'
SESSION_2 = '00000000-0000-4000-8000-000000000002'


@pytest.fixture
def delivery_world(tmp_path):
    now = [100.0]
    journal = Journal(tmp_path / 'deliveries.sqlite3')
    sender = Mock(return_value=WriteResult('sent', 'unconfirmed'))
    delivery = SocketDelivery(journal, sender=sender, clock=lambda: now[0])
    endpoint = tmp_path / 'inbox'
    endpoint.touch()
    for session in (SESSION_1, SESSION_2):
        delivery.attach(Registration(session, session, {'socket': str(endpoint)}))
    receipts = []
    return delivery, journal, sender, now, lambda speech, receipt: receipts.append(receipt), receipts


def test_continuations_are_grouped_in_order_without_crossing_recipients(delivery_world):
    delivery, _journal, sender, now, record, _receipts = delivery_world
    delivery.submit(Speech(1, SESSION_1, 'first part', 100))
    now[0] = 101.5
    delivery.submit(Speech(2, SESSION_1, 'continuation', 101.5))
    delivery.submit(Speech(3, SESSION_2, 'other conversation', 101.5))
    delivery.flush(record)
    sender.assert_not_called()

    now[0] = 104
    delivery.flush(record)

    assert [(call.args[0].session_id, call.args[1].split('\n[Receipt IDs:')[0]) for call in sender.call_args_list] == [
        (SESSION_1, '[VOICE · Noisy Studio transcript]\nfirst part\ncontinuation'),
        (SESSION_2, '[VOICE · Noisy Studio transcript]\nother conversation'),
    ]


def test_recording_extends_grace_but_not_past_twenty_seconds(delivery_world):
    delivery, _journal, sender, now, record, _receipts = delivery_world
    delivery.submit(Speech(1, SESSION_1, 'long thought', 100))
    now[0] = 110
    delivery.flush(record, recording=lambda: True)
    sender.assert_not_called()

    now[0] = 120
    delivery.flush(record, recording=lambda: True)

    sender.assert_called_once()


@pytest.mark.parametrize('outcome', ['sent', 'uncertain'])
def test_ambiguous_attempt_is_not_replayed_after_restart_or_registration(delivery_world, outcome):
    delivery, journal, sender, now, record, receipts = delivery_world
    sender.return_value = WriteResult(outcome, 'unconfirmed')
    speech = Speech(1, SESSION_1, 'do this once', 100)
    delivery.submit(speech)
    now[0] = 103
    delivery.flush(record)
    restored = SocketDelivery(Journal(journal._path), sender=sender, clock=lambda: 120)
    restored.attach(Registration(SESSION_1, SESSION_1, {'socket': 'new-endpoint'}))
    restored.submit(speech)

    restored.flush(record)

    assert (sender.call_count, [r.state for r in receipts]) == (1, ['uncertain', outcome])


def test_attempt_is_durable_before_sender_runs(delivery_world):
    delivery, journal, sender, now, record, _receipts = delivery_world
    observed = []
    def send(endpoint, text):
        observed.extend(receipt.state for _, receipt in Journal(journal._path).entries())
        return WriteResult('sent', 'unconfirmed')
    sender.side_effect = send
    delivery.submit(Speech(1, SESSION_1, 'first', 100))
    now[0] = 103

    delivery.flush(record)

    assert observed == ['uncertain']


def test_prewrite_failure_waits_for_explicit_registration_before_retry(delivery_world):
    delivery, _journal, sender, now, record, _receipts = delivery_world
    sender.return_value = WriteResult('unavailable', 'connection refused')
    delivery.submit(Speech(1, SESSION_1, 'first', 100))
    now[0] = 103
    delivery.flush(record)
    delivery.flush(record)
    assert sender.call_count == 1

    delivery.attach(Registration(SESSION_1, SESSION_1, {'socket': 'replacement'}))
    sender.return_value = WriteResult('sent', 'unconfirmed')
    delivery.flush(record)

    assert sender.call_count == 2


def test_cancelled_item_is_not_sent(delivery_world):
    delivery, journal, sender, now, record, _receipts = delivery_world
    delivery.submit(Speech(1, SESSION_1, 'cancel me', 100))
    now[0] = 103

    delivery.flush(record, reserve=lambda speeches: [])

    sender.assert_not_called()
    assert [receipt.state for _, receipt in journal.entries()] == ['rejected']


def test_journal_failure_prevents_unrecorded_io(delivery_world, monkeypatch):
    delivery, journal, sender, now, record, _receipts = delivery_world
    delivery.submit(Speech(1, SESSION_1, 'first', 100))
    now[0] = 103
    monkeypatch.setattr(journal, 'claim', Mock(side_effect=OSError('storage unavailable')))

    with pytest.raises(OSError):
        delivery.flush(record)

    sender.assert_not_called()


def test_cancellation_is_durable_and_wins_against_a_later_send_claim(delivery_world):
    delivery, journal, sender, now, record, _receipts = delivery_world
    speech = Speech(1, SESSION_1, 'cancel this', 100)
    delivery.submit(speech)

    assert delivery.cancel(speech) is True
    assert Journal(journal._path).claim([speech]) == []
    now[0] = 103
    delivery.flush(record)
    sender.assert_not_called()


def test_cancellation_cannot_claim_to_recall_a_started_attempt(delivery_world):
    delivery, journal, _sender, _now, _record, _receipts = delivery_world
    speech = Speech(1, SESSION_1, 'already starting', 100)
    delivery.submit(speech)
    journal.claim([speech])

    assert delivery.cancel(speech) is False


def test_app_notifications_are_not_presented_as_microphone_speech(delivery_world):
    delivery, _journal, sender, now, record, _receipts = delivery_world
    delivery.submit(Speech(0, SESSION_1, '[CHARACTER] Values changed.', 100))
    now[0] = 103

    delivery.flush(record)

    assert sender.call_args.args[1].split('\n[Receipt IDs:')[0] == '[NOISY STUDIO] App notification:\n[CHARACTER] Values changed.'


def test_acknowledgement_is_session_bound_idempotent_and_survives_restart(delivery_world):
    delivery, journal, sender, now, record, receipts = delivery_world
    speech1 = Speech(1, SESSION_1, 'first', 100)
    speech2 = Speech(2, SESSION_1, 'second', 100)
    speech3 = Speech(3, SESSION_2, 'other recipient', 100)
    for speech in [speech1, speech2, speech3]:
        delivery.submit(speech)
    now[0] = 103
    delivery.flush(record)
    ids = [journal.key(speech1), journal.key(speech2)]
    assert all(message_id in sender.call_args_list[0].args[1] for message_id in ids)
    assert journal.acknowledge(SESSION_2, ids) == []
    now[0] = 200
    delivery.flush(record)

    restored = Journal(journal._path)
    confirmed = restored.acknowledge(SESSION_1, ids + ids)
    repeated = restored.acknowledge(SESSION_1, ids)
    # Simulate socket completion arriving after the receiver's acknowledgement.
    restored.record([speech1, speech2], 'sent', 'write complete')

    assert [(s.utterance_id, r.state) for s, r in confirmed] == [(1, 'confirmed'), (2, 'confirmed')]
    assert repeated == confirmed
    assert [(s.utterance_id, r.state) for s, r in restored.entries()] == [(1, 'confirmed'), (2, 'confirmed'), (3, 'unknown')]


def test_acknowledgement_cannot_confirm_a_message_that_was_never_attempted(delivery_world):
    delivery, journal, _sender, _now, _record, _receipts = delivery_world
    speech = Speech(1, SESSION_1, 'still queued', 100)
    delivery.submit(speech)

    assert delivery.acknowledge(SESSION_1, [journal.key(speech)]) == []


def test_sent_deadline_uses_write_time_and_survives_restart_without_resending(delivery_world):
    delivery, journal, sender, now, record, receipts = delivery_world
    speech = Speech(1, SESSION_1, 'delayed before send', 1)
    delivery.submit(speech)
    delivery.flush(record)
    restored = SocketDelivery(Journal(journal._path), sender=sender, clock=lambda: now[0])
    now[0] = 159
    restored.flush(record)
    assert receipts[-1].state == 'sent'

    now[0] = 160
    restored.flush(record)
    restored.attach(Registration(SESSION_1, SESSION_1, {'socket': 'replacement'}))
    restored.submit(speech)
    restored.flush(record)

    assert (sender.call_count, [r.state for r in receipts], restored.cancel(speech)) == (
        1, ['uncertain', 'sent', 'unknown'], False,
    )
    assert [r.state for _, r in Journal(journal._path).entries()] == ['unknown']


def test_expiry_migrates_old_sent_entries_without_rewriting_other_outcomes(tmp_path):
    import json
    import sqlite3
    from dataclasses import asdict

    path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE deliveries (id TEXT PRIMARY KEY, speech TEXT NOT NULL, state TEXT NOT NULL, detail TEXT NOT NULL)')
        for number, state in enumerate(['sent', 'queued', 'confirmed', 'uncertain', 'unavailable'], 1):
            speech = Speech(number, SESSION_1, 'legacy message', 1)
            db.execute('INSERT INTO deliveries VALUES (?, ?, ?, ?)', (Journal.key(speech), json.dumps(asdict(speech)), state, ''))
    journal = Journal(path)

    expired = journal.expire_sent(100, 'No receipt available')

    assert [(speech.utterance_id, receipt.state) for speech, receipt in expired] == [(1, 'unknown')]
    assert [receipt.state for _, receipt in journal.entries()] == ['unknown', 'queued', 'confirmed', 'uncertain', 'unavailable']
    assert journal.expire_sent(200, 'No receipt available') == []
