"""One provider per agent system, composing its private delivery implementation."""
from __future__ import annotations

from noisy_coding.harness.provider import (
    Availability, ProviderCapabilities, Receipt, Registration, Speech, provider_name,
)


class HookDelivery:
    """Pull delivery: the core keeps speech queued until a valid hook picks it up."""
    allows_hook_pickup = True

    def __init__(self, registry):
        self._registry = registry

    def attach(self, registration: Registration) -> Availability:
        return self.availability(registration.conversation)

    def submit(self, speech: Speech) -> Receipt:
        return Receipt(speech.utterance_id, speech.conversation, 'queued')

    def observe(self, events) -> None:
        # The normalized registry already records lifecycle events.
        pass

    def availability(self, conversation: str) -> Availability:
        return self._registry.availability(conversation)


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

    def attach(self, registration: Registration) -> Availability:
        if registration.participant:
            return self.availability(registration.conversation)
        self._sessions.add(registration.conversation)
        return self._implementation.attach(registration)

    def submit(self, speech: Speech) -> Receipt:
        if speech.conversation not in self._sessions:
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', 'registration required')
        return self._implementation.submit(speech)

    def observe(self, events) -> None:
        self._implementation.observe(events)

    def availability(self, conversation: str) -> Availability:
        if conversation not in self._sessions:
            return Availability(False, 'registration required', True)
        return self._implementation.availability(conversation)


class AgentProviders:
    def __init__(self, registry, providers=None):
        capabilities = ProviderCapabilities(True, True, True, 'none')
        self._providers = providers if providers is not None else {
            name: AgentProvider(name, label, HookDelivery(registry), capabilities)
            for name, label in [('claude', 'Claude Code'), ('codex', 'Codex')]
        }
        self._registry = registry

    def get(self, name: str):
        return self._providers.get(provider_name(name))

    def for_conversation(self, key: str):
        conversation = self._registry.get(key)
        return self.get(conversation.harness) if conversation else None

    def submit(self, speech: Speech) -> Receipt:
        provider = self.for_conversation(speech.conversation)
        if provider is None:
            return Receipt(speech.utterance_id, speech.conversation, 'unavailable', 'provider not registered')
        return provider.submit(speech)
