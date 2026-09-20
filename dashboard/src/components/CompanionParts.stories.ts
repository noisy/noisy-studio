import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, onMounted, ref } from "vue";
import Bubble from "./Bubble.vue";
import VoiceAvatar from "./VoiceAvatar.vue";
import { VOICES } from "./characterMath";

/* The pieces the companion is assembled from, in isolation.
 *
 * The widget stories show whether it LOOKS right; these show whether each
 * part behaves on its own - which is where a change usually breaks first.
 */
const meta: Meta = { title: "Widget/CompanionParts", parameters: { layout: "centered" } };
export default meta;

/** The bubble at each of the widget's three sizes, both sides.
 *
 * Sizing is per message: a class decided from the text's own length, fixed
 * when it renders. These are the three classes, side by side. */
export const BubbleSizes: StoryObj = {
  render: () => ({
    components: { Bubble },
    setup: () => ({
      rows: [
        { cls: "size-l", side: "left", accent: "amber", text: "On it." },
        { cls: "size-m", side: "right", accent: "violet", text: "Storybook first - you pick, then I wire it to the daemon." },
        {
          cls: "size-s",
          side: "left",
          accent: "amber",
          text:
            "A long message drops to the smallest size so it fits without pushing " +
            "everything else out of the widget, and it keeps that size for good - " +
            "text that resizes after you have started reading it is worse than text " +
            "that was always small.",
        },
      ],
    }),
    template: `
      <div style="width:360px;display:flex;flex-direction:column;gap:10px">
        <Bubble v-for="r in rows" :key="r.cls" :class="r.cls" compact
          :side="r.side" :accent="r.accent" who="" status-kind="off"
          status-label="" time="" :text="r.text" />
      </div>
    `,
  }),
};

/** The voice spectrum: idle breathing, then driven by a level.
 *
 * The bars are the same geometry the widget draws in its hexagon. Silence
 * has to look like listening, not like a dead component. */
const Spectrum = defineComponent({
  props: { level: { type: Number, default: 0 } },
  setup(props) {
    const PHASE = [0, 1.9, 3.4, 0.7, 2.6, 4.3, 1.2];
    const WEIGHT = [0.55, 0.95, 0.7, 1, 0.78, 0.9, 0.6];
    const bars = ref<number[]>(new Array(7).fill(7));
    const smoothed = ref(0);
    onMounted(() => {
      const step = (now: number) => {
        const target = props.level;
        smoothed.value += (target - smoothed.value) * (target > smoothed.value ? 0.35 : 0.08);
        const t = now / 1000;
        bars.value = PHASE.map((p, i) => {
          const breath = Math.sin(t * 1.6 + p) * 3.5;
          const voice = smoothed.value * 46 * WEIGHT[i];
          const flicker = smoothed.value * Math.sin(t * 11 + p * 2.3) * 6;
          return Math.max(2, 7 + breath + voice + flicker);
        });
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
    return { bars };
  },
  template: `
    <svg viewBox="0 0 100 100" style="width:72px;height:72px;color:var(--amber)">
      <polygon points="50,4 90,27 90,73 50,96 10,73 10,27" fill="none"
        stroke="currentColor" stroke-width="5" />
      <g>
        <rect v-for="(h, i) in bars" :key="i" :x="26 + i * 7.5" :y="50 - h / 2"
          width="4.5" :height="h" rx="2" fill="currentColor" />
      </g>
    </svg>
  `,
});

export const SpectrumIdle: StoryObj = {
  render: () => ({ components: { Spectrum }, template: `<Spectrum :level="0" />` }),
};

export const SpectrumSpeaking: StoryObj = {
  render: () => ({ components: { Spectrum }, template: `<Spectrum :level="0.75" />` }),
};

/** Every voice identity, using the same avatar as the dashboard and widget. */
export const VoicePortraits: StoryObj = {
  render: () => ({
    components: { VoiceAvatar },
    setup: () => ({
      voices: Object.keys(VOICES).sort(),
    }),
    template: `
      <div style="display:flex;flex-wrap:wrap;gap:20px;max-width:600px;font-family:var(--sans)">
        <div v-for="v in voices" :key="v" style="display:flex;flex-direction:column;align-items:center;gap:8px;width:72px">
          <VoiceAvatar :voice="v" :size="56" />
          <small style="font-size:12px;color:var(--muted)">{{ v }}</small>
        </div>
      </div>
    `,
  }),
};
