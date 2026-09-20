"""Private Claude inbox delivery, including continuation grouping and attempts."""
from collections import defaultdict
import os
import threading
import time
import uuid

from noisy_coding.harness.claude.socket_transport import Endpoint, send
from noisy_coding.harness.provider import Availability, Receipt, Registration, Speech

GRACE_SECONDS = 2.0
GRACE_CAP_SECONDS = 20.0


class SocketDelivery:
    allows_hook_pickup = False

    def __init__(self, journal, sender=send, clock=time.time):
        self.journal = journal
        self._send = sender
        self._clock = clock
        self._endpoints = {}
        self._quiet_since = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = None
        self._pending = {}
        self._failure = ""

    def attach(self, registration: Registration) -> Availability:
        if registration.participant:
            return self.availability(registration.conversation)
        if registration.connection is not None:
            connection = registration.connection
            path = connection.get('socket') if isinstance(connection, dict) else None
            try:
                valid = str(uuid.UUID(registration.native_session_id)) == registration.native_session_id.lower()
            except (ValueError, AttributeError):
                valid = False
            with self._lock:
                self._endpoints.pop(registration.conversation, None)
                if valid and isinstance(path, str) and path:
                    self._endpoints[registration.conversation] = Endpoint(registration.native_session_id, path)
                    # Only explicit registration can retry a known pre-write failure.
                    try:
                        retry = [s for s, r in self.journal.entries('unavailable')
                                 if s.conversation == registration.conversation]
                        self.journal.record(retry, 'queued', '')
                    except Exception:
                        self._failure = 'delivery journal unavailable; delivery paused'
        return self.availability(registration.conversation)

    def availability(self, conversation: str) -> Availability:
        if self._failure:
            return Availability(False, self._failure, True)
        with self._lock:
            endpoint = self._endpoints.get(conversation)
        if endpoint is None:
            return Availability(False, 'Claude session registration required', True)
        if not os.path.exists(endpoint.path):
            return Availability(False, 'Claude inbox closed; restart or resume that session', True)
        return Availability(True, 'inbox registered; delivery confirmation unavailable')

    def observe(self, events) -> None:
        with self._lock:
            for event in events:
                if event.kind == 'session_ended' and event.participant is None:
                    self._endpoints.pop(event.conversation, None)

    def submit(self, speech: Speech) -> Receipt:
        with self._lock:
            self._pending[self.journal.key(speech)] = speech
        try:
            receipt = self.journal.add(speech)
        except Exception:
            self._failure = 'delivery journal unavailable; speech has not been sent'
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', self._failure)
        if receipt.state == 'queued' and not self.availability(speech.conversation).ready:
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', self.availability(speech.conversation).reason)
        return receipt

    def flush(self, record_receipt, reserve=lambda speeches: speeches, recording=lambda: False):
        groups = defaultdict(list)
        for speech, receipt in self.journal.entries('queued'):
            groups[speech.conversation].append(speech)
        for conversation, speeches in groups.items():
            with self._lock:
                endpoint = self._endpoints.get(conversation)
            if endpoint is None:
                continue
            now = self._clock()
            first = min(s.created_at for s in speeches)
            latest = max(s.created_at for s in speeches)
            quiet = max(latest, self._quiet_since.get(conversation, latest))
            if recording():
                quiet = now
                self._quiet_since[conversation] = quiet
            if now - first < GRACE_CAP_SECONDS and now - quiet < GRACE_SECONDS:
                continue
            # Durable BEFORE I/O. On crash this remains uncertain, never queued.
            speeches = self.journal.claim(speeches)
            reserved = reserve(speeches)
            cancelled = [s for s in speeches if s not in reserved]
            self.journal.record(cancelled, 'rejected', 'cancelled or closed before socket write')
            for speech in cancelled:
                record_receipt(speech, Receipt(speech.utterance_id, conversation, 'rejected', 'cancelled or closed before socket write'))
            if not reserved:
                continue
            for speech in reserved:
                record_receipt(speech, Receipt(speech.utterance_id, conversation, 'uncertain', 'send attempt started; outcome unknown'))
            parts = []
            previous_origin = None
            for speech in reserved:
                # Zero-ID entries are app notifications, not microphone transcripts.
                origin = ('[VOICE] User speech transcribed and delivered by Noisy Studio:'
                          if speech.utterance_id else '[NOISY STUDIO] App notification:')
                if origin != previous_origin:
                    parts.append(origin)
                    previous_origin = origin
                parts.append(speech.text)
            text = '\n'.join(parts)
            try:
                with self._lock:
                    if self._endpoints.get(conversation) != endpoint:
                        from noisy_coding.harness.claude.socket_transport import WriteResult
                        result = WriteResult('unavailable', 'registration changed before write; register again')
                    else:
                        result = self._send(endpoint, text)
                state, detail = result.state, result.detail
            except Exception:
                state, detail = 'uncertain', 'delivery attempt failed unexpectedly; not retried'
            self.journal.record(reserved, state, detail)
            for speech in reserved:
                record_receipt(speech, Receipt(speech.utterance_id, conversation, state, detail))
                with self._lock:
                    self._pending.pop(self.journal.key(speech), None)
            if state in ('unavailable', 'rejected'):
                with self._lock:
                    if self._endpoints.get(conversation) == endpoint:
                        self._endpoints.pop(conversation, None)

    def cancel(self, speech):
        return self.journal.cancel(speech)

    def start(self, record_receipt, reserve, recording, restore=None):
        if self._worker is not None:
            return
        try:
            entries = self.journal.entries()
        except Exception:
            self._failure = 'delivery journal unavailable; delivery paused'
            return
        for speech, receipt in entries:
            if receipt.state in ('cancelled', 'confirmed'):
                record_receipt(speech, receipt)
            else:
                (restore or record_receipt)(speech, receipt)

        def work():
            while not self._stop.wait(0.2):
                try:
                    self.flush(record_receipt, reserve, recording)
                except Exception:
                    # Fail visibly without falling through to an unrecorded send.
                    self._failure = 'delivery journal unavailable; delivery paused'
                    with self._lock:
                        pending = list(self._pending.values())
                    for speech in pending:
                        record_receipt(speech, Receipt(speech.utterance_id, speech.conversation, 'uncertain', self._failure))
                    return
        self._worker = threading.Thread(target=work, daemon=True, name='claude-inbox-delivery')
        self._worker.start()

    def stop(self):
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=4)
