import type { Meta, StoryObj } from "@storybook/vue3";
import { computed, defineComponent, onMounted, onUnmounted, ref } from "vue";
import Companion, { type CompanionMessage } from "./Companion.vue";

/** GRADIENT LAB (day 4): the thread's top melt-away, on a WHITE backdrop,
 *  four curves side by side, with sliders for the dead zone and the total
 *  length. Pick by eye; the winner's stops go into Companion.vue. */
const meta: Meta = { title: "Lab/CompanionFade" };
export default meta;

const FEED: CompanionMessage[] = Array.from({ length: 9 }, (_, i) => ({
  id: i + 1,
  role: i % 2 ? "claude" : "user",
  text: `message ${i + 1} - enough words that the fade has real text to eat as it scrolls away`,
}));

type Curve = { name: string; stops: (dead: number, full: number) => string };
const CURVES: Curve[] = [
  { name: "linear",
    stops: (d, f) => `transparent 0 ${d}px, black ${f}px` },
  { name: "ease-out (current)",
    stops: (d, f) => {
      const r = f - d;
      return `transparent 0 ${d}px, rgba(0,0,0,.35) ${d + r * 0.32}px, rgba(0,0,0,.75) ${d + r * 0.64}px, black ${f}px`;
    } },
  { name: "ease-in",
    stops: (d, f) => {
      const r = f - d;
      return `transparent 0 ${d}px, rgba(0,0,0,.12) ${d + r * 0.4}px, rgba(0,0,0,.45) ${d + r * 0.75}px, black ${f}px`;
    } },
  { name: "ease-in-out",
    stops: (d, f) => {
      const r = f - d;
      return `transparent 0 ${d}px, rgba(0,0,0,.15) ${d + r * 0.3}px, rgba(0,0,0,.85) ${d + r * 0.7}px, black ${f}px`;
    } },
];

const Lab = defineComponent({
  components: { Companion },
  setup() {
    // TRANSPARENT mode, as over a real desktop: the whole point of judging
    // the fade on white is seeing through the widget onto the backdrop.
    onMounted(() => document.body.classList.add("companion-transparent"));
    onUnmounted(() => document.body.classList.remove("companion-transparent"));
    const dead = ref(16);
    const full = ref(72);
    const masks = computed(() =>
      CURVES.map((c) => ({
        name: c.name,
        mask: `linear-gradient(to bottom, ${c.stops(dead.value, Math.max(full.value, dead.value + 8))})`,
      })),
    );
    return { dead, full, masks, FEED };
  },
  template: `
    <div style="background:#ffffff;min-height:100vh;padding:18px;font:12px ui-monospace,monospace;color:#333">
      <div style="display:flex;gap:18px;align-items:center;margin-bottom:14px">
        <label>dead zone <input type="range" min="0" max="40" v-model.number="dead" /> {{ dead }}px</label>
        <label>full opacity at <input type="range" min="24" max="140" v-model.number="full" /> {{ full }}px</label>
        <span style="color:#888">white backdrop on purpose - the fade must survive the worst case</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div v-for="m in masks" :key="m.name">
          <div style="margin:0 0 6px;font-weight:700">{{ m.name }}</div>
          <div :style="{ '--companion-thread-mask': m.mask }">
            <Companion mode="idle" voice="lux" :feed="FEED" :max-height="170"
              :agents="[{ name: 'lab', voice: 'lux', active: true }]" />
          </div>
        </div>
      </div>
    </div>
  `,
});

export const GradientLab: StoryObj = {
  render: () => ({ components: { Lab }, template: "<Lab />" }),
  parameters: { layout: "fullscreen" },
};
