import type { Meta, StoryObj } from "@storybook/vue3";
import HotkeysSettings, { type HotkeyBinding } from "./HotkeysSettings.vue";

/* Settings > Hotkeys (#104), the layout as picked: one card, push to talk
 * left and per-tab keys right, companion keys below. States that matter:
 * locked behind Input Monitoring, capturing, a collision, a macOS warning. */
const meta: Meta<typeof HotkeysSettings> = { component: HotkeysSettings, title: "Dashboard/HotkeysSettings" };
export default meta;

type Over = Partial<Record<string, Partial<HotkeyBinding>>>;
const b = (over: Over) => (action: string, label: string, chord: string): HotkeyBinding => ({ action, label, chord, ...(over[action] ?? {}) });
const panes = (over: Over = {}) => {
  const k = b(over);
  return {
    talk: {
      title: "Push to talk",
      caption: "Works in any app. Hold opens the mic while held; toggle opens and closes on a press; scratch drops the recording in progress.",
      bindings: [k("hold", "Hold", "F8"), k("toggle", "Toggle", "F15"), k("scratch", "Scratch", "escape")],
    },
    tabs: {
      title: "…to a specific tab",
      caption: "Toggle aimed at one conversation, counted left to right. Press again to close; another tab's key hands the mic over.",
      bindings: [k("tab1", "Tab 1", "F1"), k("tab2", "Tab 2", "F2"), k("tab3", "Tab 3", "F3"), k("tab4", "Tab 4", "F4")],
    },
    app: {
      title: "Companion window",
      bindings: [k("ghost", "Ghost mode", "ctrl+alt+g"), k("reload", "Reload windows", "ctrl+alt+r")],
    },
  };
};

const story = (state: object, over: Over = {}): StoryObj<typeof HotkeysSettings> => ({
  args: { ...panes(over), permission: "granted", ...state },
  render: (args) => ({
    components: { HotkeysSettings },
    setup: () => ({ args }),
    template: `<div style="max-width:760px;container-type:inline-size"><HotkeysSettings v-bind="args" /></div>`,
  }),
});

export const Hotkeys = story({});
export const Locked = story({ permission: "missing" });
export const Capturing = story({ capturing: "tab2" });
export const Collision = story({}, { tab1: { chord: "F8", problem: { kind: "collision", detail: "F8 is already Hold." } } });
export const DoublePress = story({}, { scratch: { chord: "escape x2" } });
export const SystemShortcut = story({}, { hold: { chord: "cmd+space", problem: { kind: "system", detail: "⌘ Space opens Spotlight unless you changed that in System Settings." } } });
export const Narrow: StoryObj<typeof HotkeysSettings> = {
  ...story({}),
  render: (args) => ({
    components: { HotkeysSettings },
    setup: () => ({ args }),
    template: `<div style="max-width:480px;container-type:inline-size"><HotkeysSettings v-bind="args" /></div>`,
  }),
};
