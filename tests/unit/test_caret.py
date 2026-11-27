"""Dictation overlay anchor: caret first, then the field, then the pointer."""

from __future__ import annotations

from types import SimpleNamespace

from noisy_studio.listener.caret import MANUAL_ACCESSIBILITY, Anchor, CaretLocator

OK, FAILURE = 0, -25200


def _rect(x, y, w, h):
    return SimpleNamespace(origin=SimpleNamespace(x=x, y=y), size=SimpleNamespace(width=w, height=h))


class _AX:
    """Just enough of HIServices: values are (kind, payload) tuples."""

    kAXFocusedUIElementAttribute = "AXFocusedUIElement"
    kAXSelectedTextRangeAttribute = "AXSelectedTextRange"
    kAXBoundsForRangeParameterizedAttribute = "AXBoundsForRange"
    kAXPositionAttribute = "AXPosition"
    kAXSizeAttribute = "AXSize"
    kAXValueCFRangeType = "range"
    kAXValueCGRectType = "rect"
    kAXValueCGPointType = "point"
    kAXValueCGSizeType = "size"

    def __init__(self, focused=None, bounds=None, app_attributes=None, wakes_to=None):
        self.focused = focused or {}
        self.bounds = bounds or {}            # (location, length) -> rect
        self.app = {"AXFocusedUIElement": "field", **(app_attributes or {})}
        self.wakes_to = wakes_to              # bounds that appear once the tree is built
        self.set_calls = []

    def AXUIElementCreateApplication(self, pid):
        return "app"

    def AXUIElementSetMessagingTimeout(self, element, seconds):
        return OK

    def AXUIElementCopyAttributeValue(self, element, name, _out):
        source = self.app if element == "app" else self.focused
        return (OK, source[name]) if name in source else (FAILURE, None)

    def AXUIElementSetAttributeValue(self, element, name, value):
        self.set_calls.append((name, value))
        if self.wakes_to:
            self.bounds = self.wakes_to
        return OK

    def AXUIElementCopyParameterizedAttributeValue(self, element, name, text_range, _out):
        rect = self.bounds.get(text_range[1])
        return (OK, ("rect", rect)) if rect else (FAILURE, None)

    def AXValueGetValue(self, value, kind, _out):
        return (value[0] == kind, value[1])

    def AXValueCreate(self, kind, payload):
        return (kind, payload)


class _AppKit:
    class NSWorkspace:
        @staticmethod
        def sharedWorkspace():
            app = SimpleNamespace(processIdentifier=lambda: 42)
            return SimpleNamespace(frontmostApplication=lambda: app)


class _Quartz:
    def CGEventCreate(self, _source):
        return "event"

    def CGEventGetLocation(self, _event):
        return SimpleNamespace(x=640.0, y=480.0)


def _locate(ax):
    return CaretLocator(ax=ax, quartz=_Quartz(), appkit=_AppKit(), sleep=lambda _s: None).locate()


def _field(**extra):
    return {
        "AXSelectedTextRange": ("range", (5, 0)),
        "AXPosition": ("point", SimpleNamespace(x=10.0, y=20.0)),
        "AXSize": ("size", SimpleNamespace(width=300.0, height=24.0)),
        **extra,
    }


def test_the_insertion_point_is_the_anchor():
    ax = _AX(_field(), bounds={(5, 0): _rect(110, 22, 1, 18)})
    assert _locate(ax) == Anchor(110, 22, 1, 18, "caret")


def test_an_empty_range_falls_back_to_the_right_edge_of_the_previous_character():
    ax = _AX(_field(), bounds={(4, 1): _rect(100, 22, 8, 18)})
    assert _locate(ax) == Anchor(108, 22, 0.0, 18, "caret")


def test_an_all_zero_rectangle_means_unknown_and_the_field_frame_is_used():
    ax = _AX(_field(), bounds={(5, 0): _rect(0, 0, 0, 0)})
    assert _locate(ax) == Anchor(10.0, 20.0, 300.0, 24.0, "field")


def test_a_document_sized_element_is_not_a_field_and_the_pointer_wins():
    big = _field(AXSize=("size", SimpleNamespace(width=900.0, height=700.0)))
    assert _locate(_AX(big)) == Anchor(640.0, 480.0, 0.0, 0.0, "mouse")


def test_chromium_is_asked_to_build_its_tree_once_and_queried_again():
    ax = _AX(
        _field(),
        app_attributes={MANUAL_ACCESSIBILITY: False},
        wakes_to={(5, 0): _rect(200, 40, 1, 16)},
    )
    locator = CaretLocator(ax=ax, quartz=_Quartz(), appkit=_AppKit(), sleep=lambda _s: None)

    first = locator.locate()
    ax.bounds = {}
    locator.locate()

    assert (first, ax.set_calls) == (Anchor(200, 40, 1, 16, "caret"), [(MANUAL_ACCESSIBILITY, True)])


def test_without_accessibility_the_pointer_is_the_anchor():
    locator = CaretLocator(ax=None, quartz=_Quartz(), appkit=None)
    locator._ax = None
    assert locator.locate() == Anchor(640.0, 480.0, 0.0, 0.0, "mouse")


def test_an_ax_exception_never_escapes():
    class Broken(_AX):
        def AXUIElementCreateApplication(self, pid):
            raise RuntimeError("boom")

    assert _locate(Broken()) == Anchor(640.0, 480.0, 0.0, 0.0, "mouse")
