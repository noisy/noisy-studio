import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, onMounted, ref } from "vue";

/* Which half of the hexagon should carry the state?
 *
 * Two elements, two candidate jobs. Changing BOTH when you start speaking
 * means neither one is a signal, so exactly one has to stay constant.
 * Shown side by side, idle above and live below, on a slider backdrop -
 * because the whole reason this came up is that the widget floats over
 * unknown pixels.
 */
const meta: Meta = { title: "Widget/CompanionHex" };
export default meta;

const Hex = defineComponent({
  props: {
    variant: { type: String, default: "outline" }, // outline | bars
    live: { type: Boolean, default: false },
  },
  setup(props) {
    const PHASE = [0, 1.9, 3.4, 0.7, 2.6, 4.3, 1.2];
    const WEIGHT = [0.55, 0.95, 0.7, 1, 0.78, 0.9, 0.6];
    const bars = ref<number[]>(new Array(7).fill(7));
    onMounted(() => {
      const step = (now: number) => {
        const t = now / 1000;
        const level = props.live ? 0.7 : 0;
        bars.value = PHASE.map((p, i) => {
          const breath = Math.sin(t * 1.6 + p) * 3.5;
          const voice = level * 46 * WEIGHT[i];
          const flicker = level * Math.sin(t * 11 + p * 2.3) * 6;
          return Math.max(2, 7 + breath + voice + flicker);
        });
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });

    const AMBER = "#ffb454";
    const SLATE = "#55647d";
    const RED = "#ff4d4d";
    // outline: bars always amber, the ring lights up.
    // bars:    ring always amber, the bars light up.
    // outline: bars always amber, the ring lights up
    // bars:    ring always amber, the bars light up
    // record:  ring always amber, the bars turn RED while recording
    const stroke = () =>
      props.variant === "outline" ? (props.live ? AMBER : SLATE) : AMBER;
    const fill = () => {
      if (props.variant === "bars") return props.live ? AMBER : SLATE;
      if (props.variant === "record") return props.live ? RED : AMBER;
      return AMBER;
    };

    return { bars, stroke, fill };
  },
  template: `
    <svg viewBox="0 0 100 100" style="width:64px;height:64px;display:block"
         :style="{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.35))' }">
      <polygon points="50,4 90,27 90,73 50,96 10,73 10,27"
        fill="#050e18" :stroke="stroke()" stroke-width="5" />
      <rect v-for="(h, i) in bars" :key="i" :x="26 + i * 7.5" :y="50 - h / 2"
        width="4.5" :height="h" rx="2" :fill="fill()" />
    </svg>
  `,
});

/** Three candidates, idle and live, over a backdrop you can slide. */
export const SideBySide: StoryObj = {
  render: () => ({
    components: { Hex },
    setup() {
      const level = ref(12);
      return { level };
    },
    template: `
      <div style="display:flex;flex-direction:column;gap:14px;font:11px/1.4 monospace">
        <label>backdrop
          <input type="range" min="0" max="100" v-model.number="level" />
        </label>

        <div :style="{
          background: 'rgb(' + Math.round(level*2.55) + ',' + Math.round(level*2.55) + ',' + Math.round(level*2.55) + ')',
          padding: '22px', borderRadius: '10px', display: 'flex', gap: '48px'
        }">
          <div style="display:flex;flex-direction:column;gap:10px;align-items:center">
            <b style="color:#9aa7bd">A - ring signals</b>
            <span style="color:#9aa7bd">idle</span>
            <Hex variant="outline" :live="false" />
            <span style="color:#9aa7bd">live</span>
            <Hex variant="outline" :live="true" />
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;align-items:center">
            <b style="color:#9aa7bd">B - bars signal</b>
            <span style="color:#9aa7bd">idle</span>
            <Hex variant="bars" :live="false" />
            <span style="color:#9aa7bd">live</span>
            <Hex variant="bars" :live="true" />
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;align-items:center">
            <b style="color:#9aa7bd">C - record red</b>
            <span style="color:#9aa7bd">idle</span>
            <Hex variant="record" :live="false" />
            <span style="color:#9aa7bd">live</span>
            <Hex variant="record" :live="true" />
          </div>
        </div>
      </div>
    `,
  }),
};
