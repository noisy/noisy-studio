/**
 * A window, and nothing else.
 *
 * The daemon stays in Python and the UI stays in the browser bundle it
 * already ships; this process exists only to do the four things a browser
 * cannot: be transparent, stay above other applications, let clicks pass
 * through to whatever is underneath, and have no window frame.
 *
 * Deliberately thin. If Electron turns out to be the wrong choice, the
 * thing being replaced should be this file, not an application.
 */
const { app, BrowserWindow, Tray, Menu, globalShortcut, nativeImage, screen, dialog } = require("electron");
const path = require("node:path");
const { loadDesktopIcons } = require("./icons");
const http = require("node:http");
const { createDesktopAnalytics, loadAnalyticsConfig } = require('./analytics');
let analytics = null;

// V3 uses distinct canonical production and development profiles.
const profileName = app.getName() === "Noisy Studio Dev" ? "Noisy Studio Dev" : "Noisy Studio";
app.setPath("userData", path.join(app.getPath("appData"), profileName));
if (process.env.NOISY_SMOKE) {
  // A smoke run must not share the Chromium profile with a running install:
  // the profile lock would make the second instance exit before it prints.
  app.setPath("userData", require("node:fs").mkdtempSync(path.join(require("node:os").tmpdir(), "noisy-smoke-")));
}
const { spawn } = require("node:child_process");

// The daemon serves the built dashboard under /next/ - the bare /companion
// path belongs to the vite dev server, not to the daemon.
/* TWO MODES, and nothing in between.
 *
 *   production  the app owns everything: it starts the daemon it carries,
 *               serves the UI from that daemon, and stops it on quit. This
 *               is what a user gets, and the default.
 *
 *   local       the app owns NOTHING: it attaches to a daemon you already
 *               run from source, and loads the UI from vite. It never
 *               starts them - your terminal shows their logs, you restart
 *               them your own way, and nothing of yours can be orphaned by
 *               an app that quit.
 *
 * Chosen at launch (NOISY_MODE=local), because you pick it once when you
 * sit down to work. A menu that switched it live would cost reloaded
 * windows, a swapped config directory and a daemon lifecycle question, to
 * save one relaunch of something you change twice a day.
 */
// Baked into the build (dev variant) or set for one run. A packaged app
// should not depend on how it was launched - double-clicking an icon
// passes no environment.
const BUILT_MODE = (() => {
  try {
    return require("./package.json").noisyMode;
  } catch {
    return undefined;
  }
})();
const MODE =
  (process.env.NOISY_MODE || BUILT_MODE) === "local" ? "local" : "production";

const OWN_PORT = Number(process.env.NOISY_APP_PORT || 9765);
const LOCAL_DAEMON_PORT = Number(process.env.NOISY_LOCAL_PORT || 7765);
const LOCAL_UI = process.env.NOISY_LOCAL_UI || "http://localhost:5173";

/** Can this port serve what the app needs? Not "is something alive" - an
 *  older daemon answers /status happily and then 404s the widget, which
 *  looks like a broken app rather than an unsuitable daemon. */
function serves(port, path) {
  return new Promise((resolve) => {
    const request = http.get(
      { host: "127.0.0.1", port, path, timeout: 700 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      },
    );
    request.on("timeout", () => (request.destroy(), resolve(false)));
    request.on("error", () => resolve(false));
  });
}

let child = null;   // the daemon WE started, if any

/** Where the frozen daemon lives: inside the bundle once packaged, in the
 *  build directory during development. */
// The engine ships as its own app bundle so macOS lists its permissions
// under a stable name and icon (#98); the bare binary is the pre-bundle
// layout, still produced next to it for local runs.
const ENGINE_EXECUTABLE = path.join("Noisy Studio Engine.app", "Contents", "MacOS", "noisy-studio-daemon");

function daemonBinary() {
  const fs = require("node:fs");
  // Packaged: Contents/Helpers - where macOS expects nested code (a bundle
  // under Resources is sealed as data, not validated as code). The old
  // Resources/daemon location is kept as a fallback for older builds.
  const roots = [
    path.join(process.resourcesPath || "", "..", "Helpers"),
    path.join(process.resourcesPath || "", "daemon"),
    path.join(__dirname, "build", "daemon"),
  ];
  for (const root of roots) {
    for (const candidate of [path.join(root, ENGINE_EXECUTABLE), path.join(root, "noisy-studio-daemon", "noisy-studio-daemon")]) {
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return path.join(roots[0], ENGINE_EXECUTABLE);
}

/** Start the daemon we carry and wait for it to answer. */
async function spawnDaemon() {
  const bin = daemonBinary();
  if (!require("node:fs").existsSync(bin)) return null;

  child = spawn(bin, [], {
    env: {
      ...process.env,
      NOISY_STUDIO_LISTENER_PORT: String(OWN_PORT),
      // The engine exits by itself when this process is gone - the only
      // protection against an orphan holding the microphone after a crash.
      NOISY_STUDIO_PARENT_PID: String(process.pid),
      // Its own config directory: sharing one means sharing settings,
      // history and the voice ledger, where the last writer wins.
      NOISY_STUDIO_CONFIG_DIR:
        process.env.NOISY_STUDIO_CONFIG_DIR ||
        path.join(app.getPath("home"), ".config", "noisy-studio"),
    },
    stdio: "ignore",
    detached: false,
  });
  child.on("exit", () => (child = null));

  // The engine initializes audio and loads the dashboard before it answers;
  // a cold start on a slow disk can take a while, which is how "the bundled
  // daemon did not start" once appeared while it was in fact still coming
  // up. Wait up to 60s.
  for (let i = 0; i < 120; i += 1) {
    if (await serves(OWN_PORT, "/status")) return OWN_PORT;
    await new Promise((r) => setTimeout(r, 500));
  }
  return null;
}

/** Resolve the mode into a daemon and a UI, or a reason it cannot. */
async function resolveMode() {
  if (MODE === "local") {
    // A GUEST here: attach to what is already running, start nothing.
    const daemonOk = await serves(LOCAL_DAEMON_PORT, "/status");
    const uiOk = await new Promise((resolve) => {
      const request = http.get(`${LOCAL_UI}/`, { timeout: 700 }, (res) => {
        res.resume();
        resolve(res.statusCode < 500);
      });
      request.on("timeout", () => (request.destroy(), resolve(false)));
      request.on("error", () => resolve(false));
    });

    base = `http://127.0.0.1:${LOCAL_DAEMON_PORT}`;
    attachedPort = daemonOk ? LOCAL_DAEMON_PORT : null;
    // A missing vite is not a reason to show nothing: the daemon still has
    // a built copy of the UI.
    uiBase = uiOk ? LOCAL_UI : base;

    const missing = [];
    if (!daemonOk) missing.push(`daemon on :${LOCAL_DAEMON_PORT}`);
    if (!uiOk) missing.push(`vite on ${LOCAL_UI}`);
    problem = missing.length ? `local mode: no ${missing.join(", no ")}` : null;
    return;
  }

  // Production: the OWNER. Start the daemon we carry.
  attachedPort = (await serves(OWN_PORT, "/next/companion"))
    ? OWN_PORT
    : await spawnDaemon();
  base = `http://127.0.0.1:${attachedPort || OWN_PORT}`;
  uiBase = base;
  problem = attachedPort ? null : "the bundled daemon did not start";
}

/* Two windows, one app:
 *   - the DASHBOARD, an ordinary window with the full UI
 *   - the WIDGET, frameless and always on top
 * Both are views of the same bundle served by the daemon, so neither
 * duplicates anything; the app is a window manager, not a second client. */
let base = null;        // where the DATA comes from (the daemon)
let uiBase = null;      // where the SCREEN comes from - not always the same
let attachedPort = null;
let problem = null;     // what to say when the mode's parts are missing

/* Vite serves the views at the root; the daemon serves the built bundle
 * under /next/. Same app, two prefixes. */
const widgetUrl = () =>
  uiBase === LOCAL_UI
    ? `${uiBase}/companion?transparent=1`
    : `${uiBase}/next/companion?transparent=1`;
const dashboardUrl = () => (uiBase === LOCAL_UI ? `${uiBase}/` : `${uiBase}/next/`);

let win = null;
let dash = null;
let tray = null;
/** Click-through: the widget is visible but the editor beneath stays usable. */
let ghost = false;

function createDashboard() {
  analytics?.track('dashboard_opened');
  if (dash && !dash.isDestroyed()) {
    dash.show();
    dash.focus();
    return dash;
  }
  dash = new BrowserWindow({
    width: 1400,
    height: 900,
    // An ordinary window: it has a title bar, it goes behind other windows,
    // it belongs in the Dock. Everything the widget deliberately is not.
    title: "Noisy Studio",
    backgroundColor: "#050e18",
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  dash.loadURL(dashboardUrl());
  dash.once("ready-to-show", () => dash.show());
  dash.on("closed", () => (dash = null));
  return dash;
}

function createWindow() {
  win = new BrowserWindow({
    width: 420,
    height: 280,
    // The widget reflows under 420px (rails drop below the bubbles), so
    // the window floor is the bubbles' own minimum, not the design width.
    minWidth: 280,
    minHeight: 200,
    // Frameless and transparent: the page paints its own background, and
    // /companion?transparent=1 strips the HUD's dark chrome for exactly this.
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    hasShadow: false,
    resizable: true,
    // Show only once it has painted - a transparent window that appears
    // before its content does flashes as a black rectangle.
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });

  // "screen-saver" rather than "floating": the lower levels lose to
  // full-screen applications, which is where a widget is most wanted.
  win.setAlwaysOnTop(true, "screen-saver");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  win.loadURL(widgetUrl());
  win.once("ready-to-show", () => {
    win.show();
    analytics?.track('widget_shown');
  });

  /* Hide the window while it reloads.
   *
   * A transparent window is only transparent once the page's CSS says so -
   * before that Chromium paints its default white base, so every reload
   * flashes a white rectangle for a second. Nothing can make that paint
   * transparent; what we CAN do is not show it. Briefly absent reads as a
   * reload; briefly white reads as a bug. */
  win.webContents.on("did-start-loading", () => win.hide());
  win.webContents.on("did-stop-loading", async () => {
    /* Wait for the page to be TRANSPARENT, not merely loaded.
     *
     * A fixed delay guesses, and guesses differently for each source: the
     * built bundle finishes loading fast, so a 90ms timer showed the window
     * while Chromium's white base was still painted; vite is slower, so the
     * same timer happened to be enough. Ask the page instead - it knows
     * when its own stylesheet has landed. */
    for (let i = 0; i < 40; i += 1) {
      const ready = await win?.webContents
        .executeJavaScript(
          'document.body?.classList.contains("companion-transparent") === true',
        )
        .catch(() => false);
      if (ready) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    // One frame more, so the first paint is the transparent one.
    await new Promise((r) => setTimeout(r, 32));
    win?.show();
  });

  watchHover(win);
  win.on("closed", () => (win = null));
}

/* Is the pointer over the window?
 *
 * The page cannot answer this by itself: the drag handle is an OS
 * app-region, and macOS swallows mouse events inside it - so moving onto
 * the handle looks exactly like leaving the window, and anything that
 * depends on hover disappears under the cursor.
 *
 * The main process has no such blind spot: it can ask the system where the
 * cursor is and compare it with the window's own bounds. Polled rather than
 * evented because there is no "cursor entered window" event to listen to;
 * 120ms is under the threshold where a fade feels late.
 */
function watchHover(win) {
  let inside = null;
  const timer = setInterval(() => {
    if (win.isDestroyed()) return clearInterval(timer);
    const { x, y } = screen.getCursorScreenPoint();
    const b = win.getBounds();
    const now = x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height;
    // Re-assert every tick rather than only on change. The page has its own
    // mouseout fallback for the browser, and inside the app that fallback
    // fires when the pointer crosses into the drag strip - the OS stops
    // sending events there, which looks to the page like leaving the window.
    // It would then clear the class and this watcher, believing nothing had
    // changed, would never put it back. So the authority repeats itself.
    if (now === inside && !now) return;
    inside = now;
    win.webContents
      .executeJavaScript(`document.body.classList.toggle("hovering", ${now})`)
      .catch(() => {});
  }, 120);
  win.on("closed", () => clearInterval(timer));
}

function setGhost(on) {
  ghost = on;
  analytics?.track(on ? 'click_through_enabled' : 'click_through_disabled');
  // forward:true keeps hover and scroll working while clicks pass through -
  // without it the widget becomes a picture you cannot even scroll.
  win?.setIgnoreMouseEvents(on, { forward: true });
  win?.webContents.send("ghost", on);
  buildTray();
}

/** Swap the UI source and reload. Data (the daemon) does not move. */
function useUi(which) {
  uiBase = which === "vite" ? LOCAL_UI : base;
  win?.loadURL(widgetUrl());
  dash?.loadURL(dashboardUrl());
  buildTray();
}

function buildTray() {
  const menu = Menu.buildFromTemplate([
    // Which daemon is answering matters when three can be running: the app
    // should never leave you guessing whose conversation you are looking at.
    {
      // A fact, not a choice - the mode is decided at launch. But with two
      // possible daemons on one machine, which one you see must never be a
      // guess.
      label:
        MODE === "local"
          ? `LOCAL - daemon :${attachedPort ?? "?"}, ui ${uiBase === LOCAL_UI ? "vite" : "built"}`
          : `Production - daemon :${attachedPort ?? "?"}${child ? " (ours)" : ""}`,
      enabled: false,
    },
    /* Only in local mode, and only for the UI.
     *
     * The daemon is chosen when you sit down; the interface is not. Vite
     * dies mid-session on a bad import, and when it does you still want a
     * working widget - so this is recovery from a failure, not a
     * preference, and that is why it earns a live switch. */
    ...(MODE === "local"
      ? [
          { type: "separator" },
          {
            label: "Interface: vite (hot reload)",
            type: "radio",
            checked: uiBase === LOCAL_UI,
            click: () => useUi("vite"),
          },
          {
            label: "Interface: built (stable)",
            type: "radio",
            checked: uiBase !== LOCAL_UI,
            click: () => useUi("built"),
          },
        ]
      : []),
    { type: "separator" },
    { label: "Open dashboard", click: () => createDashboard() },
    {
      label: win && !win.isDestroyed() && win.isVisible() ? "Hide widget" : "Show widget",
      click: () => {
        if (!win || win.isDestroyed()) return createWindow();
        const wasVisible = win.isVisible();
        wasVisible ? win.hide() : win.show();
        analytics?.track(wasVisible ? 'widget_hidden' : 'widget_shown');
        buildTray();
      },
    },
    { type: "separator" },
    { label: ghost ? "Click-through: ON" : "Click-through: OFF", click: () => setGhost(!ghost) },
    {
      label: "Reload both (Ctrl+Alt+R)",
      click: () => {
        win?.reload();
        dash?.reload();
      },
    },
    { type: "separator" },
    ...(analytics?.available ? [{
      label: 'Share optional usage analytics',
      type: 'checkbox',
      checked: analytics.enabled,
      enabled: !analytics.excluded,
      click: async (item) => {
        if (item.checked) {
          const { response } = await dialog.showMessageBox({
            type: 'question',
            message: 'Share usage analytics?',
            detail: 'Send app starts, daemon readiness, and window actions to PostHog with a random installation ID, app version, and operating system. No audio, conversations, file paths, or session recordings are collected. You can turn this off in the menu at any time.',
            buttons: ['No thanks', 'Allow analytics'],
            defaultId: 0,
            cancelId: 0,
          });
          analytics.setEnabled(response === 1);
        } else analytics.setEnabled(false);
        buildTray();
      },
    }, {
      label: 'Exclude this device from analytics (all variants)',
      type: 'checkbox',
      checked: analytics.excluded,
      click: (item) => {
        try { analytics.setExcluded(item.checked); }
        catch { dialog.showErrorBox('Could not save analytics exclusion', 'Check that your application settings folder is writable, then try again.'); }
        buildTray();
      },
    }, { type: 'separator' }] : []),
    { label: "Quit", role: "quit" },
  ]);
  tray?.setContextMenu(menu);
}

/* A cold production start waits for the engine to boot - seconds with
 * nothing on screen reads as "the app is broken". The splash is a tiny
 * self-contained page (no daemon, no bundle) that exists only to prove the
 * app is alive while resolveMode() waits. Design: dashboard Storybook,
 * App/Splash (#96); splash.html mirrors the chosen look. */
function createSplash() {
  const splash = new BrowserWindow({
    width: 320,
    height: 170,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    backgroundColor: "#151619",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  splash.loadFile(path.join(__dirname, "splash.html"));
  return splash;
}

app.whenReady().then(async () => {
  analytics = createDesktopAnalytics({
    config: loadAnalyticsConfig(),
    dataPath: app.getPath('userData'),
    exclusionPath: path.join(app.getPath('appData'), 'noisy-studio-analytics-excluded'),
    mode: MODE,
    isPackaged: app.isPackaged,
    version: app.getVersion(),
    platform: process.platform,
  });
  analytics.track('app_started');
  /* Attach before opening anything: both windows are views of a daemon, and
   * pointing them at nothing produces a not-found page that looks like a
   * bug rather than a missing service. */
  const splash = createSplash();
  await resolveMode();
  analytics.track(attachedPort ? 'daemon_ready' : 'daemon_unavailable');
  splash.destroy();
  if (process.env.NOISY_SMOKE) {
    /* Smoke run (CI and `npm run smoke`): prove the packaged app starts,
     * reaches a daemon and reports the right version - then leave. A missing
     * module, a broken engine bundle or a wrong port all end here with a
     * non-zero exit instead of a dialog nobody is watching. */
    let version = null;
    try {
      const res = await fetch(`http://127.0.0.1:${attachedPort}/status`);
      version = (await res.json()).version ?? null;
    } catch { /* attachedPort null or daemon gone: reported below */ }
    const ok = !!attachedPort && (!process.env.NOISY_SMOKE_VERSION || version === process.env.NOISY_SMOKE_VERSION);
    // Synchronous write: app.exit() would drop a buffered stdout line.
    require("node:fs").writeSync(1, `${JSON.stringify({ smoke: ok ? "ok" : "fail", mode: MODE, port: attachedPort, version, problem: problem || null })}\n`);
    app.exit(ok ? 0 : 1);
    return;
  }
  if (problem) {
    // Say what is missing rather than opening a window onto nothing - a
    // not-found page reads as a broken app, not an absent service.
    dialog.showMessageBox({
      type: "warning",
      message: `Noisy Studio (${MODE})`,
      detail: `${problem}.\n\nStart it, then reload with Ctrl+Alt+R.`,
      buttons: ["Continue"],
    });
  }

  /* Keep the Dock icon for as long as the app runs.
   *
   * macOS drops an app out of the Dock once it owns no ordinary windows -
   * and the widget is frameless, always-on-top and visible on every space,
   * which does not count. So the icon appeared at launch and vanished a
   * moment later, exactly as described. Asking for it explicitly keeps it. */
  const { dockIcon, trayIcon } = loadDesktopIcons(MODE, nativeImage);
  if (!dockIcon.isEmpty()) app.dock?.setIcon(dockIcon);
  app.dock?.show();

  createWindow();

  // A real menu-bar icon. "Template" in the filename tells macOS it is a
  // monochrome mask, so it inverts correctly in light and dark menu bars.
  // Without this the app is running and completely invisible - which is
  // exactly how it felt.
  /* macOS forces monochrome only on images marked as TEMPLATE - that is
   * what makes the production icon adapt to a light or dark menu bar. The
   * dev build deliberately opts out: a coloured icon cannot adapt, but it
   * also cannot be mistaken for the production one at a glance. */
  tray = new Tray(trayIcon.isEmpty() ? nativeImage.createEmpty() : trayIcon);
  if (trayIcon.isEmpty()) tray.setTitle("◉");
  // Clicking the icon brings the widget back if it was closed or lost.
  tray.on("click", () => {
    if (!win || win.isDestroyed()) return createWindow();
    win.show();
    analytics?.track('widget_shown');
    win.setAlwaysOnTop(true, "screen-saver");
  });
  tray.setToolTip(
    attachedPort
      ? `Noisy Studio - attached to :${attachedPort}`
      : `Noisy Studio - no daemon found (expected :${OWN_PORT})`,
  );
  buildTray();

  // A keyboard escape hatch: a click-through window cannot be clicked to
  // turn click-through off again.
  globalShortcut.register("Control+Alt+G", () => setGhost(!ghost));

  /* Reload BOTH windows from anywhere, even when the widget has no focus -
   * which it usually does not, since it floats over whatever you are
   * actually working in. Testing a change should not require hunting for
   * the window first. */
  globalShortcut.register("Control+Alt+R", () => {
    win?.reload();
    dash?.reload();
  });

  /* A frameless window has no menu of its own, so the ordinary shortcuts
   * have to be registered by hand - without them there is no way to reload
   * or quit except the tray, which is easy to miss on a window with no
   * chrome. Application-scoped, so they only fire while it has focus. */
  const menu = Menu.buildFromTemplate([
    {
      label: "Companion",
      submenu: [
        { role: "reload", accelerator: "CommandOrControl+R" },
        { role: "toggleDevTools", accelerator: "CommandOrControl+Alt+I" },
        { type: "separator" },
        { role: "quit", accelerator: "CommandOrControl+Q" },
      ],
    },
    /* Cut, copy and paste are not free on macOS: they are MENU ITEMS, and
     * a window whose application menu lacks them simply does not respond to
     * the shortcuts. Replacing the default menu without an Edit submenu
     * silently disables pasting - which matters most on the one screen a
     * new user meets first, where they have to paste an API key. */
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
  ]);
  Menu.setApplicationMenu(menu);

  // Clicking the Dock icon opens the dashboard - the widget is always
  // there, so it is not what someone is asking for.
  app.on("activate", () => createDashboard());
});

/* Closing a window does NOT quit: the app lives in the menu bar and the
 * widget is meant to outlive any particular window. Quit from the tray. */
app.on("window-all-closed", () => {});

/* Take the daemon down with us. It was started for this app; leaving it
 * running would hold the microphone open with nothing to talk to. */
let flushingAnalytics = false;
app.on("before-quit", (event) => {
  child?.kill("SIGTERM");
  child = null;
  if (analytics && !flushingAnalytics) {
    flushingAnalytics = true;
    event.preventDefault();
    void analytics.shutdown().finally(() => app.quit());
  }
});
