"""Wake an idle Claude; speech stays in the hook-owned queue."""
import threading
import time
import uuid
from collections import defaultdict

from noisy_studio.harness.claude.socket_transport import Endpoint, send, validate
from noisy_studio.harness.provider import Availability, Receipt, WakeResult

QUIET_SECONDS = 2.0
PICKUP_ALLOWANCE_SECONDS = 1.0
CONTINUATION_CAP_SECONDS = 20.0


class SocketWake:
    def __init__(self, journal, sender=send, clock=time.time, can_wake=lambda _conversation: True):
        self.journal = journal
        self._send = sender
        self._clock = clock
        self._endpoints = {}
        self._quiet_since = {}
        self._failures = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = None
        self._failure = ''
        self._can_wake = can_wake
        self._unsupported = set()

    def attach(self, registration):
        if registration.participant or registration.connection is None:
            return
        path = registration.connection.get('socket') if isinstance(registration.connection, dict) else None
        with self._lock:
            self._endpoints.pop(registration.conversation, None)
            self.journal.forget_registration(registration.conversation)
            if not isinstance(registration.connection, dict) or registration.connection.get('hook_protocol') != 2:
                self._unsupported.add(registration.conversation)
                return  # An old hook cannot consume the wake_delivery response.
            self._unsupported.discard(registration.conversation)
            try:
                valid = str(uuid.UUID(registration.native_session_id)) == registration.native_session_id.lower()
            except (ValueError, AttributeError):
                valid = False
            if valid and isinstance(path, str) and path:
                self.journal.save_registration(registration)
                self._endpoints[registration.conversation] = Endpoint(registration.native_session_id, path)
                self._failures.pop(registration.conversation, None)

    def observe(self, events):
        with self._lock:
            for event in events:
                if event.kind == 'session_started' and event.participant is None:
                    # Explicit session restart permits a fresh control signal, never
                    # a replay of speech. Late retired controls remain recognizable.
                    self.journal.retire_wakes(event.conversation)
                if event.kind == 'session_ended' and event.participant is None:
                    self._endpoints.pop(event.conversation, None)
                    self.journal.forget_registration(event.conversation)

    def availability(self, conversation):
        if self._failure:
            return Availability(False, self._failure, True)
        with self._lock:
            endpoint = self._endpoints.get(conversation)
            if conversation in self._unsupported:
                return Availability(False, 'Update the Noisy Studio integration in Claude, then resume this conversation to enable voice delivery.', True)
        if endpoint and validate(endpoint) is None:
            return Availability(True, 'socket wake available; speech delivered by hooks')
        return Availability(False, 'Open this Claude conversation and type and send any message—for example, “hello”—to reconnect voice delivery. No special command is needed.', True)

    def wake(self, conversation):
        with self._lock:
            if self._failure or not self._can_wake(conversation):
                return WakeResult('unavailable', self._failure or 'session is closed')
            endpoint = self._endpoints.get(conversation)
            if endpoint is None:
                return WakeResult('unavailable', self.availability(conversation).reason)
            prompt = (
                'Noisy Studio is waking Claude to receive your queued voice messages through its hooks. '
                'The notice below is added automatically by Claude Code. '
                '[wake: ' + uuid.uuid4().hex[:12] + ']'
            )
            if not self.journal.claim_wake(conversation, prompt):
                return WakeResult('pending', 'wake-up already pending')
            try:
                result = self._send(endpoint, prompt)
            except Exception:
                return WakeResult('uncertain', 'wake attempt interrupted; not retried')
            state = {'sent': 'requested', 'uncertain': 'uncertain'}.get(result.state, 'unavailable')
            self.journal.finish_wake(prompt, state)
            if state == 'unavailable':
                self._endpoints.pop(conversation, None)
                self.journal.forget_registration(conversation)
            detail = self.availability(conversation).reason if state == 'unavailable' else result.detail
            return WakeResult(state, detail)

    def accept_wake(self, conversation, prompt):
        return isinstance(prompt, str) and self.journal.accept_wake(conversation, prompt)

    def tick(self, record_receipt, recording=lambda: False):
        groups = defaultdict(list)
        for speech, _ in self.journal.entries('queued'):
            groups[speech.conversation].append(speech)
        for conversation, speeches in groups.items():
            if not self._can_wake(conversation):
                continue
            now = self._clock()
            first = min(s.created_at for s in speeches)
            quiet = max(max(s.created_at for s in speeches), self._quiet_since.get(conversation, 0))
            if recording():
                self._quiet_since[conversation] = quiet = now
            if now-first < CONTINUATION_CAP_SECONDS and now-quiet < QUIET_SECONDS + PICKUP_ALLOWANCE_SECONDS:
                continue
            result = self.wake(conversation)
            if result.state in ('unavailable', 'uncertain') and self._failures.get(conversation) != result.detail:
                self._failures[conversation] = result.detail
                for speech in speeches:
                    record_receipt(speech, Receipt(speech.utterance_id, conversation, 'unavailable',
                        'Your voice message is still queued. ' + result.detail))

    def start(self, record_receipt, recording):
        if self._worker:
            return
        def work():
            while not self._stop.wait(0.25):
                try:
                    self.tick(record_receipt, recording)
                except Exception:
                    # No unrecorded retry after a storage or transport failure.
                    self._failure = 'Wake-up paused because its delivery journal is unavailable'
                    return
        self._worker = threading.Thread(target=work, daemon=True, name='claude-hook-wake')
        self._worker.start()

    def stop(self):
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=4)
