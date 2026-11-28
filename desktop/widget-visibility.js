/* Whether the widget is on screen is the user's call, made from the tray.
 *
 * Two things used to overrule it:
 * - a page reload ended with a plain show(), so a widget the user had hidden
 *   came back on every reload;
 * - show() activates the app, and activating an app on macOS brings ALL its
 *   windows forward: asking for the widget also raised the dashboard over
 *   whatever you were working in.
 *
 * So the wish is kept here, apart from the window's momentary visibility
 * (a reload hides it for a moment on purpose), and the widget is always
 * shown inactive: it floats on top anyway and never needs focus to appear.
 */

function createWidgetVisibility({ getWindow, createWindow, track = () => {} }) {
  let wanted = true;
  const live = () => {
    const win = getWindow();
    return win && !win.isDestroyed() ? win : null;
  };

  function show() {
    wanted = true;
    const win = live();
    if (!win) return createWindow();
    win.showInactive();
    win.setAlwaysOnTop(true, "screen-saver");
    track("widget_shown");
  }

  function hide() {
    wanted = false;
    live()?.hide();
    track("widget_hidden");
  }

  return {
    show,
    hide,
    toggle: () => (isShown() ? hide() : show()),
    isShown,
    /* A load finished (first paint or reload): bring the widget back only if
     * the user wants it, and without raising the rest of the app. */
    afterLoad() {
      if (wanted) live()?.showInactive();
    },
  };

  function isShown() {
    return wanted && live() !== null;
  }
}

module.exports = { createWidgetVisibility };
