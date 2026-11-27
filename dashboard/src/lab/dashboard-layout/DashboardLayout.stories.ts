import type { Meta, StoryObj } from "@storybook/vue3";
import { onMounted, onUnmounted, ref } from "vue";
import HeaderOptions, { type HeaderState, type HeaderVariant } from "./HeaderOptions.vue";
import ConversationSections from "./ConversationSections.vue";

// Option board for the dashboard re-layout: the mic control moves into the
// header as ONE slot (Mute mic in Auto, Hold to talk in Push to talk), the
// conversation tabs become a sectioned list in the left column.
// Pick a header variant and confirm the section rules; the winner is then
// built into App/AgentTabs and this board is deleted.
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

const RULES = [
  ["Top (no heading)", "It is your move: the agent is speaking, has messages waiting, or is online and idle (finished its turn)."],
  ["Working", "Online, the agent is working (activity in the last 20 s) and nothing is waiting for you. Visible, dimmed, one line each."],
  ["Settled", "Offline conversations (the session ended). Collapsed by default; the open/closed choice is remembered in this browser."],
  ["No hopping", "A row moves to Working only after 10 s of continuous work, so short tool calls do not make it jump. It comes back to the top the moment it speaks or queues a message."],
  ["Order", "Inside each section: your drag order first, then arrival. The same rule moves into agentOrder.ts so the widget's avatars stay in the same order as the list."],
];
const QUESTIONS = [
  "Should a conversation that has been idle for a long time (e.g. 30 min) also count as Settled, or only ended sessions?",
  "Should you be able to settle a conversation by hand, like in T3? That needs a daemon flag; the rest of this works with what the dashboard already gets.",
  "The viewed conversation: move it to Working like any other, or keep it in place while you are looking at it?",
];

function sectionsStory(settledOpen: boolean): StoryObj {
  return {
    render: () => ({
      components: { ConversationSections },
      setup: () => ({ RULES, QUESTIONS, settledOpen }),
      template: `
        <div style="display:grid;grid-template-columns:minmax(0,900px) 380px;gap:24px;background:var(--bg0);color:var(--ink);font:13px/1.5 var(--sans);padding:12px 24px 24px 0;min-height:100vh">
          <ConversationSections :settled-open="settledOpen" />
          <aside style="padding-top:12px">
            <h2 style="font-size:15px;margin:0 0 10px">Section rules (proposal)</h2>
            <dl style="margin:0">
              <template v-for="[term, text] in RULES" :key="term">
                <dt style="font-weight:600;margin-top:10px">{{ term }}</dt>
                <dd style="margin:2px 0 0;color:var(--muted)">{{ text }}</dd>
              </template>
            </dl>
            <h2 style="font-size:15px;margin:22px 0 8px">Your call</h2>
            <ol style="margin:0;padding-left:18px;color:var(--muted)">
              <li v-for="q in QUESTIONS" :key="q" style="margin-bottom:8px">{{ q }}</li>
            </ol>
          </aside>
        </div>`,
    }),
  };
}

export const Sections = sectionsStory(false);
export const SectionsSettledOpen = sectionsStory(true);
