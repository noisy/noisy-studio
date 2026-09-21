<script setup lang="ts">
import { computed } from "vue";

// Footer version indicator. One quiet number when the UI build and the
// daemon agree; both versions plus the FIX for whichever side is stale
// when they don't (skew = someone's old artifact: a cached UI build or
// an old container).
const props = withDefaults(
  defineProps<{
    /** Daemon-reported version from /status (undefined until first poll). */
    daemonVersion?: string | null;
    /** UI build version; injectable for tests, defaults to the baked-in one. */
    uiVersion?: string;
    /** Newest published release (daemon checks GitHub periodically). */
    latestVersion?: string | null;
    /** Platform override for tests/stories; defaults to the browser's own. */
    platform?: "mac" | "windows" | "linux";
    /** LOCAL DEV instance: the stale-daemon fix is a restart, not a
     *  container update. */
    devInstance?: boolean;
  }>(),
  {
    daemonVersion: null,
    latestVersion: null,
    uiVersion: () => __APP_VERSION__,
    platform: undefined,
    devInstance: false,
  },
);

function newer(a: string, b: string): boolean {
  return a.localeCompare(b, undefined, { numeric: true }) > 0;
}

// A published release newer than what's running (skew has priority — fix
// the inconsistency first, then upgrade).
const updateAvailable = computed(() => {
  const latest = props.latestVersion;
  if (!latest || skew.value) return null;
  return newer(latest, props.uiVersion) ? latest : null;
});

function detectPlatform(): "mac" | "windows" | "linux" {
  const ua = navigator.userAgent;
  if (/Mac/i.test(ua)) return "mac";
  if (/Win/i.test(ua)) return "windows";
  return "linux";
}
const HARD_REFRESH_KEYS = {
  mac: "⌘⇧R",
  windows: "Ctrl+Shift+R",
  linux: "Ctrl+Shift+R",
} as const;

const skew = computed(() => {
  const daemon = props.daemonVersion;
  // "dev" = editable install without package metadata — nothing to compare.
  if (!daemon || daemon === "dev" || daemon === props.uiVersion) return null;
  const daemonNewer = newer(daemon, props.uiVersion);
  const keys = HARD_REFRESH_KEYS[props.platform ?? detectPlatform()];
  if (daemonNewer) {
    return { action: `HARD-REFRESH THIS TAB (${keys})`, hint: "The browser cached an older UI build." }
  }
  // Stale daemon: the fix depends on which daemon this is.
  return props.devInstance
    ? { action: "RESTART THE DEV DAEMON (scripts/dev_daemon.sh)", hint: "The local dev daemon started before the version bump." }
    : { action: "UPDATE THE NOISY STUDIO APP", hint: "The daemon runs an older release." };
});
</script>

<template>
  <span v-if="skew" class="verskew" :title="skew.hint">
    ⚠ UI v{{ uiVersion }} ≠ DAEMON v{{ daemonVersion }} — {{ skew.action }}
  </span>
  <span
    v-else-if="updateAvailable"
    class="verupdate"
    title="A newer release is published — run /noisy-studio:update"
  >
    v{{ uiVersion }} · NEW v{{ updateAvailable }} AVAILABLE
  </span>
  <span v-else class="ver" :title="`UI and daemon both v${uiVersion}`">v{{ uiVersion }}</span>
</template>

<style scoped>
.ver { color: var(--muted); letter-spacing: normal; }
.verupdate {
  color: var(--green, #4dffb4);
  letter-spacing: normal;
  text-shadow: none;
}
.verskew {
  color: var(--amber, #ffb454);
  letter-spacing: normal;
  text-shadow: none;
  animation: none;
}
@keyframes ver-blink { 50% { opacity: 0.55; } }
</style>
