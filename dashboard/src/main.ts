import { initializeAccentPalette } from "./composables/useAccentPalette";
import { createApp } from "vue";
import App from "./App.vue";
import CompanionView from "./components/CompanionView.vue";
import DictationOverlayView from "./components/DictationOverlayView.vue";
import DebugView from "./debug/DebugView.vue";
import StatusView from "./components/StatusView.vue";
import LogsView from "./logs/LogsView.vue";
import "./styles/hud.css";

// Client-side view routing on pathname:
// /debug — chat-window sandbox (hand-clicked state transitions).
// /logs  — live daemon event stream (incl. #16 nudge decisions).
// /companion — the always-on-top widget (#28), fed by the live daemon.
// /dictate — the live dictation bubble the desktop shell opens by the cursor.
function rootView() {
  // The daemon serves this bundle under /next/, so every view arrives with
  // that prefix; vite serves it at the root. Strip it before matching, or
  // /next/companion falls through to the full dashboard - which is exactly
  // what it did.
  const path = window.location.pathname.replace(/^\/next/, "");
  // /status(-page) - the human self-test board. NOTE: on vite, bare
  // /status is proxied to the daemon JSON API; use /next/status there.
  if (path.startsWith("/status") || path.startsWith("/stt-lab")) return StatusView;
  if (path.startsWith("/debug")) return DebugView;
  if (path.startsWith("/logs")) return LogsView;
  if (path.startsWith("/companion")) return CompanionView;
  if (path.startsWith("/dictate")) return DictationOverlayView;
  return App;
}
initializeAccentPalette();
createApp(rootView()).mount("#app");
