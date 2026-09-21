"""Key chords for global hotkeys (#104): "cmd+shift+F8", "F15", "right_option",
"escape x2" (a double press within DOUBLE_TAP_SECONDS).

Pure functions, no Quartz: the dashboard captures a chord from a keydown
event, the daemon stores it as text and matches it against the event tap.
Both sides agree on ONE canonical spelling so equality is string equality:
modifiers in a fixed order (cmd, ctrl, alt, shift), then the key name.
"""

from __future__ import annotations

from dataclasses import dataclass

MODIFIER_ORDER = ("cmd", "ctrl", "alt", "shift")
DOUBLE_TAP_SECONDS = 0.35  # two presses closer than this are one "x2" chord
TAPS_SUFFIX = " x2"
MODIFIER_ALIASES = {
    "cmd": "cmd", "command": "cmd", "meta": "cmd", "super": "cmd",
    "ctrl": "ctrl", "control": "ctrl",
    "alt": "alt", "option": "alt", "opt": "alt",
    "shift": "shift",
}

# macOS virtual keycodes (Carbon HIToolbox Events.h), US layout for letters.
KEYCODES: dict[str, int] = {
    **{c: k for c, k in zip("asdfhgzxcv", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9))},
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26,
    "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35,
    "return": 36, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43,
    "/": 44, "n": 45, "m": 46, ".": 47, "tab": 48, "space": 49, "`": 50,
    "delete": 51, "escape": 53,
    "right_cmd": 54, "right_shift": 60, "right_option": 61, "right_ctrl": 62,
    "capslock": 57, "fn": 63,
    "F17": 64, "F18": 79, "F19": 80, "F20": 90,
    "F5": 96, "F6": 97, "F7": 98, "F3": 99, "F8": 100, "F9": 101, "F11": 103,
    "F13": 105, "F16": 106, "F14": 107, "F10": 109, "F12": 111, "F15": 113,
    "help": 114, "home": 115, "pageup": 116, "forward_delete": 117, "F4": 118,
    "end": 119, "F2": 120, "pagedown": 121, "F1": 122,
    "left": 123, "right": 124, "down": 125, "up": 126,
}
KEY_BY_CODE: dict[int, str] = {code: name for name, code in KEYCODES.items()}

# Keys that are modifiers themselves: they arrive as flagsChanged, never
# keyDown, and are bound alone (a right-hand Option as push-to-talk).
MODIFIER_KEYS = {"right_cmd", "right_shift", "right_option", "right_ctrl", "capslock", "fn"}

# CGEventFlags masks, for matching a chord's modifiers against the tap.
FLAG_MASKS = {"cmd": 0x100000, "shift": 0x20000, "alt": 0x80000, "ctrl": 0x40000}

# Chords macOS itself listens for out of the box. Binding one is allowed
# but flagged: it will only reach us if the user changed the system side.
SYSTEM_SHORTCUTS: dict[str, str] = {
    "cmd+space": "opens Spotlight",
    "cmd+tab": "switches apps",
    "cmd+shift+3": "takes a screenshot",
    "cmd+shift+4": "takes a screenshot",
    "cmd+shift+5": "opens the screenshot tools",
    "cmd+q": "quits the front app",
    "cmd+w": "closes the front window",
    "cmd+h": "hides the front app",
    "cmd+m": "minimizes the front window",
    "cmd+alt+escape": "opens Force Quit",
    "cmd+alt+d": "shows or hides the Dock",
    "cmd+ctrl+q": "locks the screen",
    "cmd+shift+q": "logs out",
    "ctrl+up": "opens Mission Control",
    "ctrl+down": "shows the app's windows",
    "ctrl+left": "moves a Space left",
    "ctrl+right": "moves a Space right",
    "cmd+ctrl+f": "toggles full screen",
    "cmd+ctrl+space": "opens the emoji picker",
    # System Settings > Keyboard > Keyboard Shortcuts > Keyboard: macOS
    # consumes these before any app sees them.
    "ctrl+F1": "toggles full keyboard access",
    "ctrl+F2": "focuses the menu bar",
    "ctrl+F3": "focuses the Dock",
    "ctrl+F4": "moves focus to the next window",
    "ctrl+F5": "focuses the window toolbar",
    "ctrl+F6": "focuses the floating window",
    "ctrl+F7": "changes keyboard navigation",
    "ctrl+F8": "focuses the status menus",
}


@dataclass(frozen=True)
class Chord:
    key: str
    modifiers: frozenset[str] = frozenset()
    taps: int = 1  # 2 = double press

    @property
    def base(self) -> "Chord":
        """The same keys pressed once - what the tap physically sees."""
        return Chord(self.key, self.modifiers, 1)

    @property
    def keycode(self) -> int:
        return KEYCODES[self.key]

    @property
    def flags(self) -> int:
        return sum(FLAG_MASKS[m] for m in self.modifiers)

    def __str__(self) -> str:
        return format_chord(self)


class ChordError(ValueError):
    """The text is not a chord we can bind."""


def parse_chord(text: str) -> Chord:
    text = str(text).strip()
    taps = 1
    for suffix in (TAPS_SUFFIX, " ×2", "x2", "×2"):
        if text.lower().endswith(suffix.strip().lower()) and len(text) > len(suffix.strip()):
            text = text[: -len(suffix.strip())].rstrip()
            taps = 2
            break
    parts = [p.strip() for p in text.split("+")]
    if not parts or not parts[-1]:
        raise ChordError("empty chord")
    *mods, key = parts
    key = _canonical_key(key)
    modifiers: set[str] = set()
    for m in mods:
        try:
            modifiers.add(MODIFIER_ALIASES[m.lower()])
        except KeyError:
            raise ChordError(f"unknown modifier {m!r}") from None
    if key in MODIFIER_KEYS and modifiers:
        raise ChordError("a modifier key is bound alone, without other modifiers")
    return Chord(key, frozenset(modifiers), taps)


def format_chord(chord: Chord) -> str:
    mods = [m for m in MODIFIER_ORDER if m in chord.modifiers]
    text = "+".join([*mods, chord.key])
    return text + TAPS_SUFFIX if chord.taps == 2 else text


def canonical(text: str) -> str:
    """The one spelling both sides compare: parse + format."""
    return format_chord(parse_chord(text))


def _canonical_key(key: str) -> str:
    if key in KEYCODES:
        return key
    lowered = key.lower()
    if lowered in KEYCODES:
        return lowered
    upper_f = key.upper()
    if upper_f in KEYCODES:  # f8 -> F8
        return upper_f
    aliases = {"esc": "escape", "backspace": "delete", "enter": "return", "spacebar": "space",
               "arrowleft": "left", "arrowright": "right", "arrowup": "up", "arrowdown": "down"}
    if lowered in aliases:
        return aliases[lowered]
    raise ChordError(f"unknown key {key!r}")


def matches(chord: Chord, keycode: int, flags: int) -> bool:
    """Does a tap event (keycode + CGEventFlags) fire this chord? Extra
    modifiers the chord did not ask for do NOT match - cmd+F8 must not
    trigger a plain F8 binding - except for a bare modifier-key chord,
    whose own flag is naturally set."""
    if keycode != chord.keycode:
        return False
    if chord.key in MODIFIER_KEYS:
        return True
    pressed = frozenset(name for name, mask in FLAG_MASKS.items() if flags & mask)
    return pressed == chord.modifiers


# -- problems -------------------------------------------------------------

def problems(bindings: dict[str, str]) -> dict[str, dict[str, str]]:
    """Per action: {"kind": "collision"|"system"|"invalid", "detail": ...}.

    A collision names the OTHER action holding the same chord; both sides
    get it, the UI decides which to keep. A system warning never blocks."""
    out: dict[str, dict[str, str]] = {}
    seen: dict[str, str] = {}
    canon: dict[str, str] = {}
    for action, text in bindings.items():
        if not text:
            continue
        try:
            canon[action] = canonical(text)
        except ChordError as error:
            out[action] = {"kind": "invalid", "detail": str(error)}
    for action, chord in canon.items():
        base = format_chord(parse_chord(chord).base)  # F8 and "F8 x2" cannot coexist
        if base in seen:
            other = seen[base]
            out[action] = {"kind": "collision", "detail": f"{chord} is already bound to {other}"}
            out.setdefault(other, {"kind": "collision", "detail": f"{chord} is also bound to {action}"})
        else:
            seen[base] = action
    for action, chord in canon.items():
        chord = format_chord(parse_chord(chord).base)
        if action not in out and chord in SYSTEM_SHORTCUTS:
            out[action] = {"kind": "system", "detail": f"{chord} {SYSTEM_SHORTCUTS[chord]} on most Macs; it reaches Noisy Studio only if you changed that in System Settings"}
    return out
