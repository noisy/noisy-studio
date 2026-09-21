"""#104: one canonical spelling for key chords, and honest collision rules."""

from __future__ import annotations

import pytest

from noisy_studio.listener import chords
from noisy_studio.listener.chords import Chord, ChordError, canonical, matches, parse_chord, problems


@pytest.mark.parametrize("text, expected", [
    ("F8", "F8"), ("f8", "F8"), ("shift+cmd+F8", "cmd+shift+F8"),
    ("Command+Option+Space", "cmd+alt+space"), ("esc", "escape"),
    ("right_option", "right_option"), ("ctrl+alt+g", "ctrl+alt+g"),
    ("ArrowUp", "up"), ("Backspace", "delete"),
])
def test_canonical_spelling(text, expected):
    assert canonical(text) == expected


@pytest.mark.parametrize("text", ["", "+", "hyper+F8", "cmd+right_option", "F99", "cmd+"])
def test_unbindable_text_is_an_error(text):
    with pytest.raises(ChordError):
        parse_chord(text)


def test_every_key_has_a_unique_keycode():
    codes = list(chords.KEYCODES.values())
    assert len(codes) == len(set(codes))
    assert chords.KEY_BY_CODE[122] == "F1" and chords.KEY_BY_CODE[100] == "F8"


def test_matching_requires_exactly_the_chord_modifiers():
    f8 = parse_chord("F8")
    cmd_f8 = parse_chord("cmd+F8")
    assert matches(f8, f8.keycode, 0)
    assert not matches(f8, f8.keycode, chords.FLAG_MASKS["cmd"])   # cmd+F8 must not fire plain F8
    assert matches(cmd_f8, f8.keycode, chords.FLAG_MASKS["cmd"])
    assert not matches(cmd_f8, f8.keycode, 0)
    assert not matches(cmd_f8, f8.keycode, chords.FLAG_MASKS["cmd"] | chords.FLAG_MASKS["shift"])


def test_bare_modifier_key_matches_with_its_own_flag_set():
    ro = parse_chord("right_option")
    assert matches(ro, ro.keycode, chords.FLAG_MASKS["alt"])


def test_collision_between_our_actions_is_reported_on_both_sides():
    out = problems({"hold": "F8", "tab1": "f8", "toggle": "F15"})
    assert out["tab1"]["kind"] == "collision" and "hold" in out["tab1"]["detail"]
    assert out["hold"]["kind"] == "collision" and "tab1" in out["hold"]["detail"]
    assert "toggle" not in out


def test_system_shortcut_is_a_warning_not_a_block():
    out = problems({"hold": "cmd+space", "scratch": "escape"})
    assert out["hold"]["kind"] == "system" and "Spotlight" in out["hold"]["detail"]
    assert "scratch" not in out


def test_invalid_text_is_reported_per_action_and_ignored_elsewhere():
    out = problems({"hold": "F99", "toggle": "F15", "tab1": ""})
    assert out == {"hold": {"kind": "invalid", "detail": "unknown key 'F99'"}}


def test_chord_flags_and_str():
    c = Chord("F8", frozenset({"shift", "cmd"}))
    assert str(c) == "cmd+shift+F8"
    assert c.flags == chords.FLAG_MASKS["cmd"] | chords.FLAG_MASKS["shift"]


def test_double_press_spelling_and_base():
    assert canonical("escape x2") == "escape x2"
    assert canonical("Escape ×2") == "escape x2"
    assert canonical("cmd+F8 X2") == "cmd+F8 x2"
    assert parse_chord("escape x2").taps == 2 and str(parse_chord("escape x2").base) == "escape"


def test_single_and_double_on_the_same_key_collide():
    out = problems({"scratch": "escape x2", "toggle": "escape"})
    assert out["toggle"]["kind"] == "collision" and out["scratch"]["kind"] == "collision"
