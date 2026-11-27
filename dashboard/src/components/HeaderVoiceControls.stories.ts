import type { Meta, StoryObj } from "@storybook/vue3";
import HeaderVoiceControls from "./HeaderVoiceControls.vue";
import type { DaemonStatus } from "../types";

const meta: Meta<typeof HeaderVoiceControls> = {
  title: "Dashboard/HeaderVoiceControls",
  component: HeaderVoiceControls,
};
export default meta;

// The mic button carries the global talk hotkey (here the toggle, F15).
const HOTKEYS = { configured: true, permission: "granted", armed: true, bindings: { toggle: "F15" }, stored: { toggle: "F15" } } as DaemonStatus["hotkeys"];
const status = (patch: Partial<DaemonStatus>) => ({ detection_mode: "auto", muted: false, ptt_held: false, voice_muted: false, hotkeys: HOTKEYS, ...patch }) as DaemonStatus;
const STATES: { caption: string; status: DaemonStatus; offline?: boolean }[] = [
  { caption: "Auto · listening", status: status({}) },
  { caption: "Auto · mic muted + agents muted", status: status({ muted: true, voice_muted: true }) },
  { caption: "Push to talk · idle", status: status({ detection_mode: "ptt" }) },
  { caption: "Push to talk · held (on air)", status: status({ detection_mode: "ptt", ptt_held: true }) },
  { caption: "Push to talk · mute left over from Auto (click unmutes)", status: status({ detection_mode: "ptt", muted: true }) },
  { caption: "Voice service offline", status: status({}), offline: true },
  { caption: "No talk hotkey bound (no key cap)", status: status({ hotkeys: { configured: true, permission: "granted", armed: true, bindings: {}, stored: {} } }) },
];

/** Every state of the header's input/output groups. Each button keeps its
 *  width across states, so nothing beside it moves. */
export const StateMatrix: StoryObj = {
  render: () => ({
    components: { HeaderVoiceControls },
    setup: () => ({ STATES }),
    template: `<div style="display:grid;gap:14px;padding:20px;background:var(--bg0);color:var(--ink);font:13px var(--sans)">
      <div v-for="s in STATES" :key="s.caption">
        <div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px">{{ s.caption }}</div>
        <HeaderVoiceControls :status="s.status" :offline="!!s.offline" :level="0.4" />
      </div>
    </div>`,
  }),
};
