const test = require("node:test");
const assert = require("node:assert/strict");
const { createWidgetVisibility } = require("./widget-visibility");

function fakeWindow() {
  const calls = [];
  return {
    calls,
    destroyed: false,
    isDestroyed() { return this.destroyed; },
    show: () => calls.push("show"),
    showInactive: () => calls.push("showInactive"),
    hide: () => calls.push("hide"),
    setAlwaysOnTop: () => {},
  };
}

function setup(win = fakeWindow()) {
  const created = [];
  const visibility = createWidgetVisibility({ getWindow: () => win, createWindow: () => created.push(true) });
  return { win, created, visibility };
}

test("showing the widget never activates the app, so the dashboard stays where it is", () => {
  const { win, visibility } = setup();
  visibility.hide();
  visibility.show();
  assert.deepEqual(win.calls, ["hide", "showInactive"]);
});

test("a reload does not bring back a widget the user hid", () => {
  const { win, visibility } = setup();
  visibility.hide();
  visibility.afterLoad();
  assert.deepEqual(win.calls, ["hide"]);
});

test("a reload brings back a widget the user wants, still without activating the app", () => {
  const { win, visibility } = setup();
  visibility.afterLoad();
  assert.deepEqual(win.calls, ["showInactive"]);
});

test("the tray toggle follows the user's choice, not a reload's brief hide", () => {
  const { visibility } = setup();
  assert.equal(visibility.isShown(), true);
  visibility.toggle();
  assert.equal(visibility.isShown(), false);
  visibility.toggle();
  assert.equal(visibility.isShown(), true);
});

test("asking for a widget whose window is gone opens a new one", () => {
  const win = fakeWindow();
  win.destroyed = true;
  const { created, visibility } = setup(win);
  assert.equal(visibility.isShown(), false);
  visibility.show();
  assert.deepEqual(created, [true]);
});
