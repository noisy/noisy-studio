import type { Meta, StoryObj } from "@storybook/vue3";
import { onMounted, onUnmounted, ref } from "vue";
import HeaderOptions, { type HeaderState, type HeaderVariant } from "./HeaderOptions.vue";

// Option board for the dashboard header: the mic control moves into the
// header as ONE slot (Mute mic in Auto, Hold to talk in Push to talk).
// The sectioned conversation list from this board was promoted to
// Dashboard/AgentTabs. Pick a header variant; the winner is built into App
// and this board is deleted.
const meta: Meta = {
  title: "Lab/DashboardLayout",
  parameters: { layout: "fullscreen" },
};
export default meta;

const VARIANTS: { id: HeaderVariant; name: string; idea: string }[] = [
  { id: "A", name: "A · Paired plates", idea: "Mic slot (with live scope) and agents plate side by side on the right; icon + word tell them apart." },
  { id: "B", name: "B · Centre console", idea: "The mic is the instrument: scope and the mic slot as one console in the middle of the header." },
  { id: "C", name: "C · Input | Output", idea: "Two labelled groups, YOU · INPUT and AGENTS · OUTPUT. The frame says which way sound goes." },
];
const STATES: { caption: string; state: HeaderState }[] = [
  { caption: "Auto · listening", state: { mode: "auto", micMuted: false, pttHeld: false, agentsMuted: false } },
  { caption: "Auto · mic muted + agents muted", state: { mode: "auto", micMuted: true, pttHeld: false, agentsMuted: true } },
  { caption: "Push to talk · idle", state: { mode: "ptt", micMuted: false, pttHeld: false, agentsMuted: false } },
  { caption: "Push to talk · held (on air)", state: { mode: "ptt", micMuted: false, pttHeld: true, agentsMuted: false } },
  { caption: "Push to talk · mute left over from Auto (slot offers unmute)", state: { mode: "ptt", micMuted: true, pttHeld: false, agentsMuted: false } },
];

const BOARD_WIDTH_PX = 1280;

function useFakeLevel() {
  const level = ref(0.3);
  let timer: ReturnType<typeof setInterval> | undefined;
  onMounted(() => {
    timer = setInterval(() => {
      level.value = Math.max(0.05, Math.min(0.9, level.value + (Math.random() - 0.5) * 0.25));
    }, 90);
  });
  onUnmounted(() => clearInterval(timer));
  return level;
}

export const Header: StoryObj = {
  render: () => ({
    components: { HeaderOptions },
    setup: () => ({ VARIANTS, STATES, level: useFakeLevel(), width: BOARD_WIDTH_PX + "px" }),
    template: `
      <div style="background:var(--bg0);color:var(--ink);font:13px var(--sans);padding:24px;min-height:100vh">
        <section v-for="v in VARIANTS" :key="v.id" :style="{ width, marginBottom: '36px' }">
          <h2 style="font-size:16px;margin:0 0 2px">{{ v.name }}</h2>
          <p style="color:var(--muted);margin:0 0 10px">{{ v.idea }}</p>
          <div v-for="s in STATES" :key="s.caption" style="margin-bottom:6px">
            <div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 2px 20px">{{ s.caption }}</div>
            <div style="border:1px dashed var(--line);border-radius:10px;overflow:hidden">
              <HeaderOptions :variant="v.id" :state="s.state" :level="level" />
            </div>
          </div>
        </section>
      </div>`,
  }),
};
