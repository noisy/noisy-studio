import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, onMounted, onUnmounted, type PropType } from "vue";
import Companion, { type CompanionMessage } from "./Companion.vue";
import ClaudeCodeMock from "./marketing/ClaudeCodeMock.vue";

/* Synthetic screenshots: the widget floating over the Claude Code session
 * it narrates.
 *
 * The terminal (marketing/ClaudeCodeMock.vue) is the full-bleed backdrop of
 * the whole 1200x760 frame - fresh-session ASCII banner on top, transcript
 * in the left ~58%, a compact widget docked on the right. The
 * widget text deliberately differs from the wallpaper variants.
 */
const meta: Meta = {
  title: "Website/CompanionOverClaudeCode",
  parameters: { layout: "fullscreen" },
  args: { widgetWidth: 540 },
  argTypes: { widgetWidth: { control: { type: "range", min: 320, max: 800, step: 20 } } },
};
export default meta;

const VOICE_FIX: CompanionMessage[] = [
  { id: 1, role: "user", text: "what's wrong with the webhook?" },
  { id: 2, role: "claude", text: "Bad signatures were retried forever. I made them fail fast." },
  { id: 3, role: "user", text: "any risk for valid deliveries?" },
  { id: 4, role: "claude", text: "None - they take the same path as before. Test pins it." },
  { id: 5, role: "user", text: "good, run the full suite" },
];

const DIFF_REVIEW: CompanionMessage[] = [
  { id: 1, role: "user", text: "read me the diff before you commit" },
  { id: 2, role: "claude", text: "One file, 18 lines: the handler now returns 401 and skips the retry queue." },
  { id: 3, role: "user", text: "and the test?" },
  { id: 4, role: "claude", text: "Two cases: bad signature dropped, valid one delivered." },
];

const HANDS_FREE: CompanionMessage[] = [
  { id: 1, role: "user", text: "status?" },
  { id: 2, role: "claude", text: "Suite is green, fix is in. Writing the summary now." },
  { id: 3, role: "user", text: "read it to me when done" },
  { id: 4, role: "claude", text: "Will do - about two minutes." },
];

/** Full-bleed terminal with the widget docked in its empty right half. */
const TerminalShot = defineComponent({
  components: { Companion, ClaudeCodeMock },
  props: {
    feed: { type: Array as PropType<CompanionMessage[]>, required: true },
    mode: { type: String as PropType<"claude" | "idle">, default: "claude" },
    banner: { type: String as PropType<"mascot" | "both">, default: "mascot" },
    widgetWidth: { type: Number, required: true },
  },
  setup() {
    onMounted(() => document.body.classList.add("companion-transparent"));
    onUnmounted(() => document.body.classList.remove("companion-transparent"));
  },
  template: `
    <div :style="{
      width: '1200px', height: '760px',
      background: 'linear-gradient(160deg, #1a1d2b 0%, #23283c 55%, #181b28 100%)',
      borderRadius: '14px', overflow: 'hidden', position: 'relative',
    }">
      <div style="position:absolute; inset:26px 30px">
        <ClaudeCodeMock full-bleed :banner="banner" />
      </div>
      <div :style="{ position: 'absolute', right: '32px', bottom: '28px', width: widgetWidth + 'px' }">
        <Companion :mode="mode" voice="lux" :feed="feed" :max-height="200"
                   :agents="[
                     { name: 'orderflow-api', voice: 'lux', active: true },
                     { name: 'chat', voice: 'eve' },
                   ]" />
      </div>
    </div>
  `,
});

const terminalShot = (
  feed: CompanionMessage[],
  mode: "claude" | "idle" = "claude",
  banner: "mascot" | "both" = "mascot",
): StoryObj => ({
  render: (args) => ({
    components: { TerminalShot },
    setup: () => ({ feed, mode, banner, args }),
    template: `<TerminalShot :feed="feed" :mode="mode" :banner="banner" :widget-width="args.widgetWidth" />`,
  }),
});

/* Banner comparison: VoiceFix carries mascot PLUS the block banner, the
 * other two the mascot-and-welcome header only. */
export const TerminalVoiceFix = terminalShot(VOICE_FIX, "claude", "both");
export const TerminalDiffReview = terminalShot(DIFF_REVIEW);
export const TerminalHandsFree = terminalShot(HANDS_FREE, "idle");
