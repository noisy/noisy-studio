"""Provider-owned setup contracts consumed by the generic settings workflow.

An adapter supplies metadata and lifecycle operations here, plus runtime factories
in the provider registry. No provider-specific branches belong in selection.py.
"""

from dataclasses import dataclass
from typing import Callable

from noisy_coding.providers import builtin_selection


@dataclass(frozen=True)
class EngineAdapter:
    choices: Callable[[], list[dict]]
    options: Callable[[dict], dict]
    readiness: Callable[[dict], tuple[str, str]]
    voices: Callable[[dict], list[dict]]
    prepare: Callable[[dict], None]
    active_choice: Callable[[str], str]
    validate_language: Callable[[dict, str], None]
    active_voice_labels: Callable[[], dict[str, str]] | None = None


def _builtin(name: str) -> EngineAdapter:
    return EngineAdapter(
        choices=lambda: [choice for choice in builtin_selection.choices() if choice['provider'] == name],
        options=builtin_selection.options_for,
        readiness=builtin_selection.readiness,
        voices=builtin_selection.voices,
        prepare=builtin_selection.prepare,
        active_choice=lambda direction: builtin_selection.active_choices()[direction],
        validate_language=builtin_selection.validate_language,
        active_voice_labels=builtin_selection.local_voice_labels if name == "local" else None,
    )


adapters = {name: _builtin(name) for name in ('grok', 'local')}


def adapter(name: str) -> EngineAdapter:
    try:
        return adapters[name]
    except KeyError:
        raise ValueError('This speech provider is not available.') from None
