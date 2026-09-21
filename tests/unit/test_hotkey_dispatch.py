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
