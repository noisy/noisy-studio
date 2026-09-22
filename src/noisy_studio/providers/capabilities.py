"""Serializable provider/model facts; no device, network, or model loading.

None language codes means unknown/voice-dependent, never 'all languages'.
An incomplete list is guidance, not a validation whitelist.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LanguageCapabilities:
    codes: tuple[str, ...] | None
    auto_detect: bool | None
    selectable: bool = True
    exhaustive: bool = True
    purpose: Literal['recognition', 'synthesis', 'formatting', 'voice'] = 'recognition'
    note: str = ''


@dataclass(frozen=True)
class SmartTurnCapabilities:
    modes: tuple[str, ...] = ('live',)
    minimum: float = 0.0
    maximum: float = 1.0
    off_value: float = 0.0


@dataclass(frozen=True)
class AudioCapabilities:
    model: str
    modes: tuple[str, ...]
    languages: LanguageCapabilities
    smart_turn: SmartTurnCapabilities | None = None
