"""Where is the text cursor? The anchor for the live dictation overlay.

Asked once, when a dictation starts, through the Accessibility API (the
permission dictation already needs to paste). Best answer first:

1. caret  - kAXBoundsForRangeParameterizedAttribute of the focused
            element's kAXSelectedTextRange: the insertion point itself.
2. field  - the focused element's own frame, when it is field-sized.
3. mouse  - the pointer, which is usually near where the user clicked.

Chromium-based apps (Electron, Chrome) build their accessibility tree only
when an assistive app asks for it, so the first caret query fails there.
For those we set AXManualAccessibility (Electron's documented switch) once
per app and ask again.

All coordinates are global points with the origin at the top-left of the
main display - the system AX and Electron's `screen` both use.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

AX_SUCCESS = 0
# A hung target app must not stall a dictation start for the system default
# of six seconds; the overlay can fall back to the pointer instead.
MESSAGING_TIMEOUT_SECONDS = 0.3
# Chromium needs a moment to build the tree after AXManualAccessibility.
TREE_BUILD_SECONDS = 0.15
# A focused "element" taller than this is a whole document or web area, not
# a text field: anchoring to its corner would put the overlay far away.
FIELD_MAX_HEIGHT = 120
MANUAL_ACCESSIBILITY = "AXManualAccessibility"


@dataclass(frozen=True)
class Anchor:
    x: float
    y: float
    width: float
    height: float
    source: str  # "caret" | "field" | "mouse"

    def as_dict(self) -> dict:
        return asdict(self)


def _ax():
    try:
        import ApplicationServices  # noqa: PLC0415

        return ApplicationServices
    except ImportError:
        return None


def _quartz():
    try:
        import Quartz  # noqa: PLC0415

        return Quartz
    except ImportError:
        return None


def _appkit():
    try:
        import AppKit  # noqa: PLC0415

        return AppKit
    except ImportError:
        return None


class CaretLocator:
    def __init__(self, ax=None, quartz=None, appkit=None, sleep=time.sleep) -> None:
        self._ax = ax if ax is not None else _ax()
        self._quartz = quartz if quartz is not None else _quartz()
        self._appkit = appkit if appkit is not None else _appkit()
        self._sleep = sleep
        self._awakened: set[int] = set()  # pids we switched AXManualAccessibility on for

    def locate(self) -> Anchor | None:
        try:
            return self._from_focus() or self._mouse()
        except Exception:  # noqa: BLE001 - an overlay position is never worth a crash
            return self._safe_mouse()

    # -- focus -------------------------------------------------------------

    def _from_focus(self) -> Anchor | None:
        if self._ax is None or self._appkit is None:
            return None
        app = self._appkit.NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        pid = int(app.processIdentifier())
        element = self._ax.AXUIElementCreateApplication(pid)
        self._ax.AXUIElementSetMessagingTimeout(element, MESSAGING_TIMEOUT_SECONDS)
        focused = self._attribute(element, self._ax.kAXFocusedUIElementAttribute)
        caret = self._caret(focused) if focused is not None else None
        if caret is None and self._awaken(element, pid):
            focused = self._attribute(element, self._ax.kAXFocusedUIElementAttribute)
            caret = self._caret(focused) if focused is not None else None
        if caret is not None:
            return caret
        return self._field(focused) if focused is not None else None

    def _awaken(self, element, pid: int) -> bool:
        """Chromium: ask it to build its accessibility tree. Once per app."""
        if pid in self._awakened:
            return False
        if self._attribute(element, MANUAL_ACCESSIBILITY) is not False:
            return False  # not an Electron app, or already on
        self._awakened.add(pid)
        if self._ax.AXUIElementSetAttributeValue(element, MANUAL_ACCESSIBILITY, True) != AX_SUCCESS:
            return False
        self._sleep(TREE_BUILD_SECONDS)
        return True

    def _caret(self, focused) -> Anchor | None:
        ax = self._ax
        selected = self._attribute(focused, ax.kAXSelectedTextRangeAttribute)
        if selected is None:
            return None
        rect = self._bounds(focused, selected)
        if rect is None:
            # Some apps measure nothing for an empty range: measure the
            # character before the insertion point and take its right edge.
            ok, (location, length) = ax.AXValueGetValue(selected, ax.kAXValueCFRangeType, None)
            if not ok or length or location <= 0:
                return None
            previous = ax.AXValueCreate(ax.kAXValueCFRangeType, (location - 1, 1))
            rect = self._bounds(focused, previous)
            if rect is None:
                return None
            x, y, width, height = rect
            return Anchor(x + width, y, 0.0, height, "caret")
        return Anchor(*rect, "caret")

    def _bounds(self, focused, text_range) -> tuple[float, float, float, float] | None:
        ax = self._ax
        error, value = ax.AXUIElementCopyParameterizedAttributeValue(
            focused, ax.kAXBoundsForRangeParameterizedAttribute, text_range, None
        )
        if error != AX_SUCCESS or value is None:
            return None
        ok, rect = ax.AXValueGetValue(value, ax.kAXValueCGRectType, None)
        if not ok:
            return None
        bounds = (rect.origin.x, rect.origin.y, rect.size.width, rect.size.height)
        # Chromium answers an unknown position with an all-zero rectangle.
        return bounds if bounds[3] > 0 and (bounds[0] or bounds[1]) else None

    def _field(self, focused) -> Anchor | None:
        ax = self._ax
        position = self._attribute(focused, ax.kAXPositionAttribute)
        size = self._attribute(focused, ax.kAXSizeAttribute)
        if position is None or size is None:
            return None
        ok_p, point = ax.AXValueGetValue(position, ax.kAXValueCGPointType, None)
        ok_s, extent = ax.AXValueGetValue(size, ax.kAXValueCGSizeType, None)
        if not (ok_p and ok_s) or not 0 < extent.height <= FIELD_MAX_HEIGHT:
            return None
        return Anchor(point.x, point.y, extent.width, extent.height, "field")

    def _attribute(self, element, name):
        error, value = self._ax.AXUIElementCopyAttributeValue(element, name, None)
        return value if error == AX_SUCCESS else None

    # -- pointer -------------------------------------------------------------

    def _mouse(self) -> Anchor | None:
        if self._quartz is None:
            return None
        point = self._quartz.CGEventGetLocation(self._quartz.CGEventCreate(None))
        return Anchor(point.x, point.y, 0.0, 0.0, "mouse")

    def _safe_mouse(self) -> Anchor | None:
        try:
            return self._mouse()
        except Exception:  # noqa: BLE001
            return None
