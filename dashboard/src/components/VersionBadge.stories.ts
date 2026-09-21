import type { Meta, StoryObj } from "@storybook/vue3";
import VersionBadge from "./VersionBadge.vue";

const meta: Meta<typeof VersionBadge> = {
  component: VersionBadge,
  title: "Dashboard/VersionBadge",
  decorators: [
    () => ({
      template:
        '<div style="background:#02060c;padding:16px;font:10px monospace;"><story /></div>',
    }),
  ],
};
export default meta;

/** UI and daemon agree — one quiet version number. */
export const InSync: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.8.0", daemonVersion: "2.8.0" },
};

/** Daemon is newer → the browser cached an old UI build; hard-refresh.
 *  The shortcut matches the platform (⌘⇧R / Ctrl+Shift+R). */
export const UiStale: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.7.7", daemonVersion: "2.8.0", platform: "mac" },
};

/** Same skew on Windows/Linux — Ctrl+Shift+R wording. */
export const UiStaleWindows: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.7.7", daemonVersion: "2.8.0", platform: "windows" },
};

/** UI is newer → the native app runs an old release; update it. */
export const DaemonStale: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.8.0", daemonVersion: "2.7.7" },
};

/** Stale daemon on a LOCAL DEV instance — the fix is a restart, not a
 *  native app update. */
export const DaemonStaleDev: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.9.0", daemonVersion: "2.8.0", devInstance: true },
};

/** A newer release is published — calm green invitation to update. */
export const UpdateAvailable: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.8.0", daemonVersion: "2.8.0", latestVersion: "2.9.0" },
};

/** Daemon not polled yet (or dev install without metadata) — no verdict. */
export const Unknown: StoryObj<typeof VersionBadge> = {
  args: { uiVersion: "2.8.0", daemonVersion: null },
};
