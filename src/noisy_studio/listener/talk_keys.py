"""Per-conversation talk keys: any conversation may own one global chord.

Pressing it does what a tabN key does (toggle-to-talk: hand the mic to the
conversation, a second press closes, another talk key hands over), but it
is aimed at the conversation itself, not at a position in the list.

Rules, in one place:

- A talk key may not reuse a chord any global action holds (hold, toggle,
  scratch, tabN, dictate) - refused as a "collision", the previous key
  survives. The reverse holds too: a global action may not take a chord a
  conversation owns (see `taken_by_conversations`).
- A chord another conversation owns MOVES: the new owner gets it, the old
  one is left without a key, and the result names it (`moved_from`).
- A conversation with its own talk key drops out of the tabN numbering, so
  each conversation is reached by exactly one key and the positional keys
  flow on to the conversations that have none (ListenerState.tab_shortcuts).

The registry stores the chords; this module only decides what to store.
"""

from __future__ import annotations

from dataclasses import dataclass

from noisy_studio.listener.chords import ChordError, canonical, problems

# How a talk key is named among the hotkey listener's bindings and in the
# chord problem reports: never a valid action name, so the two cannot clash.
TALK_PREFIX = "talk:"
REFUSED_KINDS = ("collision", "invalid")


def binding_name(conversation: str) -> str:
    return TALK_PREFIX + conversation


def conversation_of(binding: str) -> str | None:
    """The conversation a listener binding talks to, or None for an action."""
    return binding[len(TALK_PREFIX):] if binding.startswith(TALK_PREFIX) else None


@dataclass(frozen=True)
class TalkKeyChange:
    conversation: str
    talk_key: str               # what the conversation owns afterwards ("" = none)
    moved_from: str | None      # the conversation that lost the chord to it
    problem: dict[str, str] | None  # a HotkeyProblem; refused when collision/invalid

    @property
    def refused(self) -> bool:
        return self.problem is not None and self.problem.get("kind") in REFUSED_KINDS


def assign(registry, actions: dict[str, str], conversation: str, chord_text: str) -> TalkKeyChange:
    """Give `conversation` (a registry key) the chord, or clear it with "".

    `actions` is the stored {action: chord text} map of the global hotkeys."""
    current = registry.talk_key(conversation)
    if not chord_text.strip():
        registry.set_talk_key(conversation, "")
        return TalkKeyChange(conversation, "", None, None)
    try:
        chord = canonical(chord_text)
    except ChordError as error:
        return TalkKeyChange(conversation, current, None, {"kind": "invalid", "detail": str(error)})
    name = binding_name(conversation)
    found = problems({**{a: t for a, t in actions.items() if t}, name: chord}).get(name)
    if found is not None and found["kind"] in REFUSED_KINDS:
        return TalkKeyChange(conversation, current, None, found)
    moved_from = registry.set_talk_key(conversation, chord)
    return TalkKeyChange(conversation, chord, moved_from, found)


def taken_by_conversations(registry) -> dict[str, str]:
    """{binding name: chord} of every talk key, for checking a global action
    against them; `display_names` turns the binding names into words."""
    return {binding_name(key): chord for key, chord in registry.talk_keys().items()}


def display_names(registry) -> dict[str, str]:
    """How a problem report names a talk key: by its conversation's label,
    never by an id (a tab never shows one)."""
    names = {}
    for key in registry.talk_keys():
        conversation = registry.get(key)
        label = conversation.label() if conversation is not None else "another conversation"
        names[binding_name(key)] = f"the conversation '{label}'"
    return names
