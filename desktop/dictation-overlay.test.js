const test = require("node:test");
const assert = require("node:assert/strict");
const { placeOverlay, overlayWanted, startDictationOverlay, OVERLAY_WIDTH, OVERLAY_HEIGHT } = require("./dictation-overlay");

// A 1440x900 display with a 25pt menu bar and a 70pt Dock: the visible frame.
const workArea = { x: 0, y: 25, width: 1440, height: 805 };
const size = { width: 380, height: 140 };
const caret = (x, y) => ({ x, y, width: 1, height: 18 });

test("opens below the cursor's line when there is room", () => {
  assert.deepEqual(placeOverlay({ anchor: caret(200, 300), workArea, size, gap: 8 }), { x: 200, y: 326, placement: "below" });
});

test("opens above when the bottom of the visible frame is too close", () => {
  assert.deepEqual(placeOverlay({ anchor: caret(200, 760), workArea, size, gap: 8 }), { x: 200, y: 612, placement: "above" });
});

test("never runs off the right edge, nor the left", () => {
  assert.equal(placeOverlay({ anchor: caret(1400, 300), workArea, size }).x, 1440 - 380);
  assert.equal(placeOverlay({ anchor: caret(-30, 300), workArea, size }).x, 0);
});

test("a cramped display keeps the bubble inside, on the roomier side", () => {
  const short = { x: 0, y: 25, width: 1440, height: 200 };
  assert.deepEqual(placeOverlay({ anchor: caret(10, 100), workArea: short, size, gap: 8 }), { x: 10, y: 85, placement: "below" });
  assert.deepEqual(placeOverlay({ anchor: caret(10, 120), workArea: short, size, gap: 8 }), { x: 10, y: 25, placement: "above" });
});

test("works on a display placed above the main one (negative coordinates)", () => {
  const upper = { x: -424, y: -1080, width: 1920, height: 1055 };
  const field = { x: 1500, y: -143, width: 853, height: 66 };
  assert.deepEqual(placeOverlay({ anchor: field, workArea: upper, size, gap: 8 }), { x: 1116, y: -291, placement: "above" });
});

test("visible while recording and while the words are on their way in", () => {
  assert.deepEqual(
    [null, { active: true }, { active: false, pending: true }, { active: false, pending: false }].map(overlayWanted),
    [false, true, true, false],
  );
});

function harness() {
  const calls = [];
  let finishLoad;
  const win = {
    visible: false,
    isDestroyed: () => false,
    isVisible() { return this.visible; },
    loadURL: (u) => calls.push(["load", u]),
    setBounds: (b) => calls.push(["bounds", b]),
    showInactive() { this.visible = true; calls.push(["show"]); },
    hide() { this.visible = false; calls.push(["hide"]); },
    webContents: {
      once: (_e, fn) => (finishLoad = fn),
      executeJavaScript: (js) => (calls.push(["js", js]), Promise.resolve()),
    },
  };
  let snapshot = null;
  let clock = 0;
  const overlay = startDictationOverlay({
    createWindow: (opts) => (calls.push(["create", opts]), win),
    screen: {
      getCursorScreenPoint: () => ({ x: 50, y: 60 }),
      getDisplayMatching: () => ({ workArea }),
    },
    fetchDictation: async () => snapshot,
    url: () => "http://127.0.0.1:9765/next/dictate",
    now: () => clock,
    setTimer: () => 0,
    clearTimer: () => {},
  });
  return {
    calls, win, overlay,
    set: (s) => (snapshot = s),
    at: (t) => (clock = t),
    load: () => finishLoad(),
  };
}

test("shows without focus next to the cursor, then hides after the words land", async () => {
  const h = harness();
  h.set({ active: true, pending: false, session: 1, anchor: caret(200, 300) });
  await h.overlay.tick();          // creates and loads the window
  h.load();
  await h.overlay.tick();          // painted: show it
  h.set({ active: false, pending: true, session: 1, anchor: caret(200, 300) });
  h.at(1000); await h.overlay.tick();
  h.set({ active: false, pending: false, session: 1, anchor: caret(200, 300) });
  h.at(1200); await h.overlay.tick();   // lingers
  h.at(1800); await h.overlay.tick();   // gone
  assert.deepEqual(h.calls, [
    ["create", { width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT }],
    ["load", "http://127.0.0.1:9765/next/dictate"],
    ["bounds", { x: 200, y: 326, width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT }],
    ["js", 'location.hash = "below"'],
    ["show"],
    ["hide"],
  ]);
});

test("falls back to the pointer when the daemon cannot find the cursor in time", async () => {
  const h = harness();
  h.set({ active: true, pending: false, session: 1, anchor: null });
  await h.overlay.tick();
  h.load();
  h.at(100); await h.overlay.tick();    // still waiting for the anchor
  h.at(500); await h.overlay.tick();    // gave up: the pointer
  assert.deepEqual(h.calls.filter(([k]) => k === "bounds"), [["bounds", { x: 50, y: 68, width: OVERLAY_WIDTH, height: OVERLAY_HEIGHT }]]);
});
