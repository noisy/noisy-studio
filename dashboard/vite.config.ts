/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";
import pkg from "./package.json";

// Point `vite dev` at another daemon (e.g. the 7765 dev instance) with
// NOISY_STUDIO_DAEMON_URL=http://127.0.0.1:7765 npm run dev
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const env = (globalThis as any).process?.env ?? {};
// Development must default to the isolated dev instance, never production.
const DAEMON = env.NOISY_STUDIO_DAEMON_URL ?? "http://127.0.0.1:7765";
// The client always uses relative URLs: same-origin when the daemon serves
// the built app at /next, proxied to the daemon in `vite dev`.
const DAEMON_PATHS = [
  "/status", "/utterances", "/character", "/drain", "/events", "/delivery",
  "/stream", "/pause", "/resume", "/mute", "/mode", "/settings",
  "/voice", "/active-agent", "/devices", "/speak", "/ptt", "/cancel",
  "/interrupt", "/playback-pause", "/skip-unheard", "/shutdown", "/shutdown-cancel", "/shutdown-postpone", "/voice-mute", "/credentials", "/dismiss-agent",
  "/reorder-agents", "/providers", "/stt-lab", "/tests",
  // Prefix match, so this covers /speech-settings/preview and /transcribe.
  // Left out when the endpoint was added, and the failure is silent: Vite
  // answers an unproxied path with index.html, the client sees HTTP 200,
  // json() throws, and the caller stores null - so the panel sits on
  // "Loading speech engines..." forever with no error to explain it.
  "/speech-settings",
];

export default defineConfig({
  // vueDevTools only touches `vite dev`: the floating Vue DevTools panel
  // (component tree, props, pinia-less state) — never part of the build.
  // Its vite-plugin-inspect dependency breaks Storybook's vite server
  // ("Can not found environment context for client"), so skip it there.
  //
  // OFF BY DEFAULT (2026-09-08): its floating button sits over the widget,
  // which is only a few hundred pixels tall, and gets in the way far more
  // often than the panel gets used. Set VUE_DEVTOOLS=1 to bring it back.
  plugins:
    env.STORYBOOK || !env.VUE_DEVTOOLS ? [vue()] : [vue(), vueDevTools()],
  // The UI carries its own build-time version; the daemon reports its own
  // in /status — the footer compares the two and flags a skew.
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  base: "./", // served from /next/ — assets must resolve relatively
  server: {
    proxy: Object.fromEntries(DAEMON_PATHS.map((path) => [path, DAEMON])),
  },
  test: {
    environment: "happy-dom",
  },
});
