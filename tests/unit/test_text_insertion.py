"""Dictate anywhere: paste into the focused app and give the clipboard back."""

from __future__ import annotations

import pytest

from noisy_studio.listener import text_insertion
from noisy_studio.listener.text_insertion import InsertionError, PasteInserter


class _Item:
    def __init__(self, types: dict[str, object] | None = None):
        self.data = dict(types or {})

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def types(self):
        return list(self.data)

    def dataForType_(self, kind):
        return self.data.get(kind)

    def setData_forType_(self, data, kind):
        self.data[kind] = data


class _Pasteboard:
    def __init__(self, items: list[dict[str, object]]):
        self.items = [_Item(types) for types in items]
        self.count = 1
        self.on_paste = None  # what "the user" does while the target app pastes

    def pasteboardItems(self):
        return list(self.items)

    def changeCount(self):
        return self.count

    def clearContents(self):
        self.items = []
        self.count += 1

    def setString_forType_(self, text, kind):
        if not self.items:
            self.items.append(_Item())
        self.items[0].data[kind] = text

    def writeObjects_(self, items):
        self.items.extend(items)

    def contents(self):
        return [item.data for item in self.items]


class _AppKit:
    NSPasteboardItem = _Item

    def __init__(self, pasteboard):
        board = pasteboard

        class NSPasteboard:
            @staticmethod
            def generalPasteboard():
                return board

        class _App:
            def localizedName(self):
                return "Terminal"

        class NSWorkspace:
            @staticmethod
            def sharedWorkspace():
                return type("W", (), {"frontmostApplication": lambda self: _App()})()

        self.NSPasteboard = NSPasteboard
        self.NSWorkspace = NSWorkspace


class _Quartz:
    kCGEventSourceStateHIDSystemState = 1
    kCGEventFlagMaskCommand = 1 << 20
    kCGHIDEventTap = 0

    def __init__(self, pasteboard, granted=True):
        self.pasteboard = pasteboard
        self.granted = granted
        self.posted: list[tuple[int, bool, int]] = []
        self.pasted_text: list[str] = []

    def CGPreflightPostEventAccess(self):
        return self.granted

    def CGEventSourceCreate(self, _state):
        return "source"

    def CGEventCreateKeyboardEvent(self, _source, keycode, down):
        return {"keycode": keycode, "down": down, "flags": 0}

    def CGEventSetFlags(self, event, flags):
        event["flags"] = flags

    def CGEventPost(self, _tap, event):
        self.posted.append((event["keycode"], event["down"], event["flags"]))
        if event["down"]:
            # The focused app reads the pasteboard while handling Cmd+V.
            self.pasted_text.append(self.pasteboard.items[0].data[text_insertion.STRING_TYPE])
            if self.pasteboard.on_paste:
                self.pasteboard.on_paste()


@pytest.fixture
def board():
    return _Pasteboard([{"public.html": b"<b>mine</b>", "public.utf8-plain-text": b"mine"}])


def _inserter(board, granted=True):
    quartz = _Quartz(board, granted)
    return PasteInserter(appkit=_AppKit(board), quartz=quartz, sleep=lambda _s: None), quartz


def test_pastes_the_text_with_cmd_v_and_restores_every_clipboard_type(board):
    inserter, quartz = _inserter(board)

    result = inserter.insert("hello world")

    assert {
        "pasted": quartz.pasted_text,
        "keys": quartz.posted,
        "clipboard": board.contents(),
        "app": result.app,
    } == {
        "pasted": ["hello world"],
        "keys": [(9, True, 1 << 20), (9, False, 1 << 20)],
        "clipboard": [{"public.html": b"<b>mine</b>", "public.utf8-plain-text": b"mine"}],
        "app": "Terminal",
    }


def test_the_temporary_text_is_marked_transient_for_clipboard_managers(board):
    inserter, _ = _inserter(board)
    seen = []
    board.on_paste = lambda: seen.append(sorted(board.items[0].data))

    inserter.insert("secret")

    assert seen == [sorted([text_insertion.STRING_TYPE, *text_insertion.TRANSIENT_TYPES])]


def test_a_copy_made_during_the_paste_is_not_overwritten_by_the_restore(board):
    inserter, _ = _inserter(board)

    def user_copies():
        board.clearContents()
        board.setString_forType_("copied meanwhile", "public.utf8-plain-text")

    board.on_paste = user_copies

    inserter.insert("dictated")

    assert board.contents() == [{"public.utf8-plain-text": "copied meanwhile"}]


def test_an_empty_clipboard_is_left_empty():
    empty = _Pasteboard([])
    inserter, _ = _inserter(empty)
    inserter.insert("text")
    assert empty.contents() == []


def test_without_accessibility_nothing_is_touched(board):
    inserter, quartz = _inserter(board, granted=False)

    with pytest.raises(InsertionError, match="Accessibility"):
        inserter.insert("text")

    assert (quartz.posted, board.count) == ([], 1)


def test_permission_status_and_request(monkeypatch):
    class Q:
        granted = False

        def CGPreflightPostEventAccess(self):
            return self.granted

        def CGRequestPostEventAccess(self):
            self.granted = True
            return True

    quartz = Q()
    monkeypatch.setattr(text_insertion, "_quartz", lambda: quartz)
    before = text_insertion.accessibility_status()
    after_request = text_insertion.request_accessibility()
    monkeypatch.setattr(text_insertion, "_quartz", lambda: None)
    assert (before, after_request, text_insertion.accessibility_status()) == (
        "missing", "granted", "unavailable",
    )
