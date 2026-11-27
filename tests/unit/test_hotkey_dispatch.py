"""#104: the tap dispatches chords to actions; per-tab keys hand the mic over."""

from __future__ import annotations

import pytest

from noisy_studio.listener import hotkey
from noisy_studio.listener.chords import FLAG_MASKS, KEYCODES


class _State:
    def __init__(self, tabs=3):
        self.tabs = tabs
        self.log: list[str] = []
        self.selected: list[int] = []

    def refresh_ptt_hold(self): self.log.append("hold")
    def release_ptt(self): self.log.append("release")
    def request_recording_abort(self): self.log.append("abort")
    def talk_to_tab(self, index):
        self.selected.append(index)
        return index <= self.tabs
    def talk_to_conversation(self, key):
        self.selected.append(key)
        return key != "gone"


@pytest.fixture
def armed(monkeypatch):
    """A listener with permission granted and the tap faked away."""
    st = _State()
    lst = hotkey.HotkeyListener(st, st.log.append)
    monkeypatch.setattr(hotkey, "input_monitoring_status", lambda: "granted")
    monkeypatch.setattr(lst, "_start_tap", lambda: setattr(lst, "_tap_thread", object()))
    monkeypatch.setattr(lst, "_stop_tap", lambda: setattr(lst, "_tap_thread", None))
    # no renew thread in tests
    monkeypatch.setattr(hotkey.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    return lst, st


def press(lst, name, flags=0):
    lst._on_event(KEYCODES[name], flags, True)
    lst._on_event(KEYCODES[name], flags, False)


def test_bindings_snapshot_and_problems(armed):
    lst, _ = armed
    lst.configure_bindings({"hold": "F8", "tab1": "f8", "toggle": "cmd+space", "tab2": "F2"})
    snap = lst.snapshot()
    assert snap["bindings"] == {"toggle": "cmd+space", "tab2": "F2"}   # collided pair not armed
    assert snap["problems"]["hold"]["kind"] == "collision"
    assert snap["problems"]["tab1"]["kind"] == "collision"
    assert snap["problems"]["toggle"]["kind"] == "system"                # warned, still armed
    assert snap["armed"] is True


def test_hold_key_opens_and_closes_with_the_key(armed):
    lst, st = armed
    lst.configure_bindings({"hold": "F8"})
    press(lst, "F8")
    assert st.log[-2:] == ["hold", "release"]


def test_modifiers_must_match_exactly(armed):
    lst, st = armed
    lst.configure_bindings({"hold": "F8", "toggle": "cmd+F8"})
    press(lst, "F8", FLAG_MASKS["cmd"])       # cmd+F8 -> toggle opens, not hold
    assert st.log == ["hold"]
    press(lst, "F8", FLAG_MASKS["cmd"])       # second press closes the toggle
    assert st.log == ["hold", "release"]


def test_tab_key_selects_then_toggles_and_hands_over(armed):
    lst, st = armed
    lst.configure_bindings({"tab1": "F1", "tab2": "F2"})
    press(lst, "F1")
    assert st.selected == [1] and st.log == ["hold"]
    press(lst, "F1")                            # same tab again: close
    assert st.log == ["hold", "release"]
    press(lst, "F1"); press(lst, "F2")          # hand-over: release tab 1, open tab 2
    assert st.selected == [1, 1, 2] and st.log[-3:] == ["hold", "release", "hold"]


def test_missing_tab_does_nothing(armed):
    lst, st = armed
    st.tabs = 1
    lst.configure_bindings({"tab3": "F3"})
    press(lst, "F3")
    assert st.log == ["hotkey: no visible conversation #3"]


def test_scratch_aborts_and_closes_any_latch(armed):
    lst, st = armed
    lst.configure_bindings({"tab1": "F1", "scratch": "escape"})
    press(lst, "F1"); press(lst, "escape")
    assert st.log == ["hold", "abort", "release"]


def test_legacy_three_key_configure_keeps_tab_bindings(armed):
    lst, _ = armed
    lst.configure_bindings({"tab1": "F1"})
    lst.configure("F8", "", "escape")
    assert lst.snapshot()["bindings"] == {"hold": "F8", "scratch": "escape", "tab1": "F1"}


def test_double_press_fires_on_the_second_press_within_the_window(armed):
    lst, st = armed
    clock = [0.0]
    lst._clock = lambda: clock[0]
    lst.configure_bindings({"scratch": "escape x2"})
    press(lst, "escape")
    assert st.log == []                                     # one press: nothing yet
    clock[0] = 0.2; press(lst, "escape")
    assert st.log == ["abort"]                              # nothing was engaged, so no release
    clock[0] = 1.0; press(lst, "escape"); clock[0] = 1.6; press(lst, "escape")   # too slow
    assert st.log == ["abort"]


def test_hold_refuses_a_double_press(armed):
    lst, _ = armed
    lst.configure_bindings({"hold": "F8 x2"})
    snap = lst.snapshot()
    assert snap["bindings"] == {} and snap["problems"]["hold"]["kind"] == "invalid"


def test_global_toggle_closes_a_lease_a_tab_key_opened(armed):
    lst, st = armed
    lst.configure_bindings({"toggle": "F15", "tab2": "F17"})
    press(lst, "F17")                 # start talking to tab 2
    assert st.selected == [2] and st.log == ["hold"]
    press(lst, "F15")                 # finish with the everyday toggle
    assert st.log == ["hold", "release"]
    press(lst, "F15"); press(lst, "F17")   # toggle open, tab key hands over
    assert st.log[-3:] == ["hold", "release", "hold"]


class _Dictation:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls: list[str] = []

    def start(self):
        self.calls.append("start")
        return self.allowed

    def stop(self):
        self.calls.append("stop")


def _with_dictation(armed, allowed=True):
    lst, st = armed
    dictation = _Dictation(allowed)
    lst._dictation = dictation
    lst.configure_bindings({"dictate": "F13", "toggle": "F15", "scratch": "escape"})
    return lst, st, dictation


def test_dictate_key_toggles_a_dictation_on_the_talk_lease(armed):
    lst, st, dictation = _with_dictation(armed)
    press(lst, "F13")
    press(lst, "F13")
    assert (st.log, dictation.calls) == (["hold", "release"], ["start", "stop"])


def test_a_refused_dictation_leaves_an_open_talk_lease_alone(armed):
    lst, st, dictation = _with_dictation(armed, allowed=False)
    press(lst, "F15")                           # talking to the agent
    press(lst, "F13")                           # no permission: nothing changes
    assert (st.log, dictation.calls) == (["hold"], ["start"])


def test_dictate_ends_a_talk_lease_and_toggle_ends_the_dictation(armed):
    lst, st, dictation = _with_dictation(armed)
    press(lst, "F15")
    press(lst, "F13")
    press(lst, "F15")
    assert (st.log, dictation.calls) == (["hold", "release", "hold", "release"], ["start", "stop"])


def test_scratch_drops_the_dictation(armed):
    lst, st, dictation = _with_dictation(armed)
    press(lst, "F13")
    press(lst, "escape")
    assert (st.log, dictation.calls) == (["hold", "abort", "release"], ["start", "stop"])


def test_talk_key_hands_the_mic_to_its_own_conversation_and_toggles(armed):
    lst, st = armed
    lst.configure_bindings({}, talk_keys={"conv-a": "F13"})

    press(lst, "F13")
    press(lst, "F13")

    assert (st.selected, st.log) == (["conv-a"], ["hold", "release"])


def test_talk_keys_and_tab_keys_hand_the_mic_over_to_each_other(armed):
    lst, st = armed
    lst.configure_bindings({"tab1": "F16"}, talk_keys={"conv-a": "F13", "conv-b": "F14"})

    press(lst, "F13")
    press(lst, "F14")
    press(lst, "F16")

    assert (st.selected, st.log) == (["conv-a", "conv-b", 1], ["hold", "release", "hold", "release", "hold"])


def test_talk_key_of_a_vanished_conversation_does_nothing(armed):
    lst, st = armed
    lst.configure_bindings({}, talk_keys={"gone": "F13"})

    press(lst, "F13")

    assert st.log == ["hotkey: the talk key's conversation is gone"]


def test_snapshot_reports_talk_keys_apart_from_the_action_bindings(armed):
    lst, _ = armed
    lst.configure_bindings({"hold": "F8", "toggle": "F13"}, talk_keys={"conv-a": "f13", "conv-b": "F14"})

    snap = lst.snapshot()

    assert (snap["bindings"], snap["talk_keys"], snap["problems"], snap["talk_key_problems"]) == (
        {"hold": "F8"},
        {"conv-b": "F14"},
        {"toggle": {"kind": "collision", "detail": "F13 is also bound to a conversation's talk key"}},
        {"conv-a": {"kind": "collision", "detail": "F13 is already bound to toggle"}},
    )


def test_configuring_actions_keeps_the_talk_keys_and_vice_versa(armed):
    lst, _ = armed
    lst.configure_bindings({"hold": "F8"}, talk_keys={"conv-a": "F13"})

    lst.configure_bindings({"hold": "F9"})
    lst.configure_talk_keys({"conv-b": "F14"})

    snap = lst.snapshot()
    assert (snap["bindings"], snap["talk_keys"]) == ({"hold": "F9"}, {"conv-b": "F14"})
