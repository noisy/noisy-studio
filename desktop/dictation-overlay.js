/**
 * The live dictation overlay: a small bubble next to the text cursor that
 * shows the words while a dictation records, and goes away once they are
 * pasted.
 *
 * The daemon knows where the cursor was (it has the Accessibility
 * permission; this process does not) and publishes it at GET /dictation.
 * This file only decides where the window goes and when it is visible.
 *
 * The window must never take focus: the paste goes to the frontmost app,
 * and a focused overlay would receive the words itself. Hence a
 * non-activating panel, `focusable: false`, `showInactive()`, and mouse
 * events that pass straight through.
 */

// Fixed size: the bubble grows inside it up to these limits, then scrolls.
const OVERLAY_WIDTH = 380;
const OVERLAY_HEIGHT = 140;
// Air between the cursor's line and the bubble.
const OVERLAY_GAP = 8;
// How long the bubble stays after the words are in, so the user sees them land.
const LINGER_MS = 700;
const POLL_MS = 150;
// The daemon locates the cursor off the hotkey thread; give it this long
// before falling back to the pointer.
const ANCHOR_WAIT_MS = 450;

const clamp = (value, low, high) => Math.min(Math.max(value, low), Math.max(low, high));

/**
 * Where the window goes: below the cursor's line, or above it when there
 * is not enough room below; always inside the visible frame (`workArea`,
 * which excludes the menu bar and the Dock) of the display holding it.
 */
function placeOverlay({ anchor, workArea, size, gap = OVERLAY_GAP }) {
  const bottom = workArea.y + workArea.height;
  const below = anchor.y + anchor.height + gap;
  const above = anchor.y - gap - size.height;
  let placement = "below";
  let y = below;
  if (below + size.height > bottom) {
    const roomBelow = bottom - below;
    const roomAbove = anchor.y - gap - workArea.y;
    if (above >= workArea.y || roomAbove > roomBelow) {
      placement = "above";
      y = above;
    }
  }
  return {
    x: Math.round(clamp(anchor.x, workArea.x, workArea.x + workArea.width - size.width)),
    y: Math.round(clamp(y, workArea.y, bottom - size.height)),
    placement,
  };
}

/** Visible while recording, and while its words are still on the way in. */
function overlayWanted(snapshot) {
  return !!snapshot && (snapshot.active || snapshot.pending);
}

/**
 * Drive the overlay window from the daemon's dictation snapshot.
 * Everything Electron is passed in, so the policy can be tested.
 */
function startDictationOverlay({ createWindow, screen, fetchDictation, url, now = Date.now, setTimer = setInterval, clearTimer = clearInterval }) {
  let win = null;
  let loaded = false;
  let shownSession = 0;
  let wantedSince = null; // when the overlay was first wanted for this session
  let lingerUntil = 0;

  const ensureWindow = () => {
    if (win && !win.isDestroyed()) return win;
    loaded = false;
    win = createWindow({ width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT });
    win.webContents.once("did-finish-load", () => (loaded = true));
    win.loadURL(url());
    return win;
  };

  const show = (snapshot) => {
    const w = ensureWindow();
    if (!loaded) return; // the next tick shows it, painted
    const anchor = snapshot.anchor ?? { ...screen.getCursorScreenPoint(), width: 0, height: 0 };
    const display = screen.getDisplayMatching({
      x: Math.round(anchor.x), y: Math.round(anchor.y),
      width: Math.max(1, Math.round(anchor.width)), height: Math.max(1, Math.round(anchor.height)),
    });
    const spot = placeOverlay({ anchor, workArea: display.workArea, size: { width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT } });
    w.setBounds({ x: spot.x, y: spot.y, width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT });
    w.webContents.executeJavaScript(`location.hash = ${JSON.stringify(spot.placement)}`).catch(() => {});
    w.showInactive();
    shownSession = snapshot.session;
  };

  const hide = () => {
    if (win && !win.isDestroyed() && win.isVisible()) win.hide();
    shownSession = 0;
  };

  const tick = async () => {
    const snapshot = await fetchDictation().catch(() => null);
    const t = now();
    if (overlayWanted(snapshot)) {
      lingerUntil = t + LINGER_MS;
      if (snapshot.session === shownSession) return;
      if (wantedSince === null) wantedSince = t;
      if (snapshot.anchor || t - wantedSince >= ANCHOR_WAIT_MS) {
        wantedSince = null;
        show(snapshot);
      } else {
        ensureWindow(); // load while the daemon finds the cursor
      }
    } else if (shownSession && t >= lingerUntil) {
      hide();
    } else if (!shownSession) {
      wantedSince = null;
    }
  };

  const timer = setTimer(tick, POLL_MS);
  return {
    tick,
    reload: () => win && !win.isDestroyed() && win.loadURL(url()),
    stop: () => clearTimer(timer),
  };
}

module.exports = { placeOverlay, overlayWanted, startDictationOverlay, OVERLAY_WIDTH, OVERLAY_HEIGHT, OVERLAY_GAP };
