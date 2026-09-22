"""One provider per agent system, composing its private delivery implementation."""
from __future__ import annotations

from noisy_studio.harness.claude.journal import Journal
from noisy_studio.harness.claude.socket_delivery import SocketDelivery
from noisy_studio.harness.claude.socket_wake import SocketWake
from noisy_studio.harness.claude.socket_transport import Endpoint, validate
import sqlite3
from noisy_studio.harness import hook_runtime

# Deliberate rollback: change only this choice, then restart/re-register sessions.
CLAUDE_DELIVERY = "hook-wake"

from noisy_studio.harness.provider import (
    Availability, ProviderCapabilities, Receipt, Registration, Speech, WakeResult, provider_name,
)


class HookDelivery:
    """Pull delivery: the core keeps speech queued until a valid hook picks it up."""
    allows_hook_pickup = True

    def __init__(self, registry, journal=None, waker=None):
        self._registry = registry
        self.journal = journal
        self.waker = waker

    def attach(self, registration: Registration) -> Availability:
        if self.waker:
            self.waker.attach(registration)
        return self.availability(registration.conversation)

    def submit(self, speech: Speech) -> Receipt:
        if self.journal:
            return self.journal.add(speech)
        return Receipt(speech.utterance_id, speech.conversation, 'queued')

    def prepare_hook_pickup(self, speeches):
        if self.journal:
            for speech in speeches:
                self.journal.add(speech)
            self.journal.claim(speeches)

    def acknowledge(self, conversation, message_ids):
        return self.journal.acknowledge(conversation, message_ids) if self.journal else []

    def complete_hook_pickup(self, speeches):
        if self.journal:
            self.journal.record(speeches, 'confirmed', 'handed to the receiving hook')

    def wake(self, conversation):
        return self.waker.wake(conversation) if self.waker else WakeResult('unavailable', 'independent wake-up is unsupported')

    def accept_wake(self, conversation, prompt):
        return self.waker.accept_wake(conversation, prompt) if self.waker else False

    def cancel(self, speech):
        return self.journal.cancel(speech) if self.journal else True

    def start(self, record_receipt, reserve, recording, restore=None):
        if self.journal:
            for speech, receipt in self.journal.entries():
                if receipt.state in ('cancelled', 'confirmed'):
                    record_receipt(speech, receipt)
                else:
                    (restore or record_receipt)(speech, receipt)
        if self.waker:
            self.waker.start(record_receipt, recording)

    def stop(self):
        if self.waker:
            self.waker.stop()

    def observe(self, events) -> None:
        if self.waker:
            self.waker.observe(events)

    def availability(self, conversation: str) -> Availability:
        registered = self._registry.get(conversation)
        capabilities = self._registry._capabilities.get(registered.harness) if registered else None
        hooks = hook_runtime.availability(registered, capabilities, self._registry._clock())
        if hooks.ready or not self.waker or not registered or registered.ended:
            return hooks
        return self.waker.availability(conversation)


class AgentProvider:
    def __init__(self, name: str, label: str, implementation, capabilities: ProviderCapabilities):
        self.name = name
        self.label = label
        self.capabilities = capabilities
        self._implementation = implementation
        self._sessions: set[str] = set()

    @property
    def allows_hook_pickup(self) -> bool:
        return getattr(self._implementation, 'allows_hook_pickup', False) is True

    @property
    def registration_context(self) -> str:
        return getattr(self._implementation, 'registration_context', '')

    def attach(self, registration: Registration) -> Availability:
        if registration.participant:
            return self.availability(registration.conversation)
        self._sessions.add(registration.conversation)
        return self._implementation.attach(registration)

    def submit(self, speech: Speech) -> Receipt:
        if speech.conversation not in self._sessions:
            if self.allows_hook_pickup:
                self._implementation.submit(speech)  # Persist speech while waiting for reconnection.
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', 'Open this conversation in your agent and type and send any message to reconnect voice delivery. No special command is needed.')
        return self._implementation.submit(speech)

    def prepare_hook_pickup(self, speeches):
        prepare = getattr(self._implementation, 'prepare_hook_pickup', None)
        if prepare:
            prepare(speeches)

    def complete_hook_pickup(self, speeches):
        complete = getattr(self._implementation, 'complete_hook_pickup', None)
        if complete:
            complete(speeches)

    def wake(self, conversation: str) -> WakeResult:
        wake = getattr(self._implementation, 'wake', None)
        return wake(conversation) if wake else WakeResult('unavailable', 'independent wake-up is unsupported')

    def accept_wake(self, conversation, prompt):
        accept = getattr(self._implementation, 'accept_wake', None)
        return accept(conversation, prompt) if accept else False

    def cancel(self, speech: Speech) -> bool:
        cancel = getattr(self._implementation, 'cancel', None)
        return cancel(speech) if cancel else True

    def observe(self, events) -> None:
        self._implementation.observe(events)

    def acknowledge(self, conversation, message_ids):
        acknowledge = getattr(self._implementation, 'acknowledge', None)
        return acknowledge(conversation, message_ids) if acknowledge else []

    def availability(self, conversation: str) -> Availability:
        if conversation not in self._sessions:
            return Availability(False, 'Open this conversation in your agent and type and send any message to reconnect voice delivery. No special command is needed.', True)
        return self._implementation.availability(conversation)


class AgentProviders:
    def __init__(self, registry, providers=None):
        capabilities = ProviderCapabilities(True, True, True, 'none')
        journal_path = registry._path.parent / 'claude-delivery.sqlite3' if registry._path else None
        journal = Journal(journal_path)
        def can_wake(key):
            conversation = registry.get(key)
            return conversation is not None and not conversation.hidden and not conversation.ended
        waker = SocketWake(journal, can_wake=can_wake) if CLAUDE_DELIVERY == 'hook-wake' else None
        claude_delivery = SocketDelivery(journal) if CLAUDE_DELIVERY == 'socket' else HookDelivery(registry, journal, waker)
        self._providers = providers if providers is not None else {
            'claude': AgentProvider('claude', 'Claude Code', claude_delivery, ProviderCapabilities(True, True, True, 'transport')),
            'codex': AgentProvider('codex', 'Codex', HookDelivery(registry), capabilities),
            'grok': AgentProvider('grok', 'Grok', HookDelivery(registry), capabilities),
        }
        self._registry = registry

    def restore_connections(self):
        provider = self.get('claude')
        implementation = provider._implementation if provider else None
        waker = getattr(implementation, 'waker', None)
        if not waker:
            return
        try:
            for registration in waker.journal.registrations():
                conversation = self._registry.get(registration.conversation)
                connection = registration.connection
                if (not conversation or conversation.harness != 'claude'
                        or conversation.hidden or conversation.ended
                        or registration.native_session_id != conversation.key
                        or not isinstance(connection, dict) or connection.get('hook_protocol') != 2
                        or not isinstance(connection.get('socket'), str)
                        or validate(Endpoint(registration.native_session_id, connection['socket']))):
                    waker.journal.forget_registration(registration.conversation)
                    continue
                provider.attach(registration)
            self._registry._readiness['claude'] = provider.availability
        except (OSError, sqlite3.Error):
            # Never discard a corrupt journal: it also protects ambiguous sends.
            waker._failure = 'Voice delivery could not recover its saved state. Restart Noisy Studio; if this persists, report the problem.'

    def start(self, record_receipt, reserve, recording, restore=None):
        for provider in self._providers.values():
            start = getattr(provider._implementation, 'start', None)
            if start:
                start(record_receipt, reserve, recording, restore)

    def get(self, name: str):
        return self._providers.get(provider_name(name))

    def for_conversation(self, key: str):
        conversation = self._registry.get(key)
        return self.get(conversation.harness) if conversation else None

    def submit(self, speech: Speech) -> Receipt:
        conversation = self._registry.get(speech.conversation)
        if conversation and conversation.ended:
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable',
                           'Resume this conversation in your agent to continue receiving voice messages.')
        provider = self.for_conversation(speech.conversation)
        if provider is None:
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', 'provider not registered')
        return provider.submit(speech)
