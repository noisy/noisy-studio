"""#104: hotkeys as an action map - collisions are refused, tabs resolve to conversations."""

from __future__ import annotations

from noisy_studio.listener import http_api
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.state import ListenerState


class _Listener:
    def __init__(self):
        self.calls = []

    def configure_bindings(self, bindings, *, may_prompt=False):
        self.calls.append((dict(bindings), may_prompt))

    def snapshot(self):
        return {"configured": True, "permission": "granted", "armed": True, "bindings": {}, "problems": {}}


def _state():
    st = ListenerState()
    st.hotkey_listener = _Listener()
    return st


def test_patch_merges_and_rearms_with_prompt_allowed():
    st = _state()
    stored, problems = http_api._apply_hotkeys(st, {"hold": "f8", "tab1": "F1"})
    assert stored == {"hold": "f8", "tab1": "F1"} and problems == {}
    assert st.hotkey_listener.calls[-1] == ({"hold": "f8", "tab1": "F1"}, True)


def test_colliding_chord_is_refused_and_the_old_binding_survives():
    st = _state()
    http_api._apply_hotkeys(st, {"hold": "F8", "tab1": "F1"})
    stored, problems = http_api._apply_hotkeys(st, {"tab1": "F8"})
    assert stored == {"hold": "F8", "tab1": "F1"}          # F1 kept, F8 not taken
    assert problems["tab1"]["kind"] == "collision" and "hold" in problems["tab1"]["detail"]
    assert "hold" not in problems                            # the holder is not blamed


def test_invalid_chord_is_refused():
    st = _state()
    stored, problems = http_api._apply_hotkeys(st, {"hold": "F99"})
    assert stored == {"hold": ""} and problems["hold"]["kind"] == "invalid"   # nothing armed, explicit off


def test_system_shortcut_is_stored_with_a_warning():
    st = _state()
    stored, problems = http_api._apply_hotkeys(st, {"toggle": "cmd+space"})
    assert stored == {"toggle": "cmd+space"} and problems["toggle"]["kind"] == "system"


def test_empty_clears_and_unknown_actions_are_ignored():
    st = _state()
    http_api._apply_hotkeys(st, {"hold": "F8", "bogus": "F9"})
    stored, _ = http_api._apply_hotkeys(st, {"hold": ""})
    assert stored == {"hold": ""}                       # explicit off, no bogus action


def test_legacy_views_read_the_map():
    st = _state()
    st.set_hotkeys({"hold": "F8", "scratch": "escape"})
    assert (st.ptt_hold_key, st.ptt_toggle_key, st.ptt_cancel_key) == ("F8", "", "escape")
    st.set_ptt_keys(None, "F15", None)
    assert st.hotkeys == {"hold": "F8", "scratch": "escape", "toggle": "F15"}


def test_talk_to_tab_counts_visible_conversations_left_to_right(tmp_path):
    st = ListenerState()
    st.conversations = ConversationRegistry(path=tmp_path / "c.json")
    for key in ("a", "b", "c"):
        st.conversations.adopt(key, key.upper(), "fake")
        st.register_agent(key, key.upper())
    st.conversations.hide("b")
    assert st.talk_to_tab(1) and st.active_agent == "a"
    assert st.talk_to_tab(2) and st.active_agent == "c"     # hidden b is skipped
    assert st.talk_to_tab(3) is False and st.active_agent == "c"
    assert st.talk_to_tab(0) is False


def test_defaults_fill_untouched_actions_but_never_an_explicit_off():
    from noisy_studio.listener.hotkey import DEFAULT_HOTKEYS

    st = _state()
    st.set_hotkeys({"toggle": "F15", "tab1": ""})   # tab1 cleared on purpose
    st.fill_default_hotkeys(DEFAULT_HOTKEYS)
    h = st.hotkeys
    assert h["toggle"] == "F15" and h["tab1"] == ""
    assert h["scratch"] == "escape x2" and h["tab2"] == "F17" and h["tab4"] == "F19"


def test_clearing_over_http_is_an_explicit_off():
    st = _state()
    http_api._apply_hotkeys(st, {"tab1": "F16"})
    stored, problems = http_api._apply_hotkeys(st, {"tab1": ""})
    assert stored["tab1"] == "" and problems == {}
    assert st.hotkey_listener.calls[-1][0]["tab1"] == ""
