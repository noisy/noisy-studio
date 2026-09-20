import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent } from "vue";

/* Candidate app icons, drawn as SVG so they can be judged at real sizes.
 *
 * macOS does NOT mask or outline an app icon - whatever the file contains
 * is what you see, including any background the renderer left behind. The
 * white ring on the current build is exactly that: a transparent SVG
 * flattened onto white during conversion, not something the system added.
 */
const meta: Meta = { title: "Dashboard/AppIcon" };
export default meta;

const HEX = "22,3 39,13 39,31 22,41 5,31 5,13";

const Icon = defineComponent({
  props: { variant: { type: String, required: true }, size: { type: Number, default: 128 } },
  template: `
    <svg :width="size" :height="size" viewBox="0 0 44 44">
      <!-- A: dark rounded square, cyan hexagon (today's, minus the white) -->
      <template v-if="variant === 'squircle'">
        <rect x="1" y="1" width="42" height="42" rx="10" fill="#050e18" />
        <polygon points="${HEX}" fill="none" stroke="#3fd8ff" stroke-width="2.2"
                 transform="scale(0.82) translate(4.8, 4.8)" />
        <g fill="#3fd8ff" transform="scale(0.82) translate(4.8, 4.8)">
          <rect x="15" y="17" width="2.4" height="10" rx="1.2" />
          <rect x="20.8" y="13" width="2.4" height="18" rx="1.2" />
          <rect x="26.6" y="18" width="2.4" height="8" rx="1.2" />
        </g>
      </template>

      <!-- B: the hexagon IS the icon - no container, no square -->
      <template v-if="variant === 'bare'">
        <polygon points="${HEX}" fill="#050e18" stroke="#3fd8ff" stroke-width="2.4" />
        <g fill="#3fd8ff">
          <rect x="15" y="17" width="2.4" height="10" rx="1.2" />
          <rect x="20.8" y="13" width="2.4" height="18" rx="1.2" />
          <rect x="26.6" y="18" width="2.4" height="8" rx="1.2" />
        </g>
      </template>

      <!-- C: solid cyan hexagon, dark bars punched out of it -->
      <template v-if="variant === 'solid'">
        <rect x="1" y="1" width="42" height="42" rx="10" fill="#0b1626" />
        <polygon points="${HEX}" fill="#3fd8ff" transform="scale(0.84) translate(4.2, 4.2)" />
        <g fill="#071019" transform="scale(0.84) translate(4.2, 4.2)">
          <rect x="15" y="17" width="2.8" height="10" rx="1.4" />
          <rect x="20.6" y="13" width="2.8" height="18" rx="1.4" />
          <rect x="26.2" y="18" width="2.8" height="8" rx="1.4" />
        </g>
      </template>

      <!-- D: waveform only, no hexagon - reads at 16px, unlike an outline -->
      <template v-if="variant === 'wave'">
        <rect x="1" y="1" width="42" height="42" rx="10" fill="#050e18" />
        <g fill="#3fd8ff">
          <rect x="10" y="19" width="3.2" height="6" rx="1.6" />
          <rect x="16" y="15" width="3.2" height="14" rx="1.6" />
          <rect x="22" y="10" width="3.2" height="24" rx="1.6" />
          <rect x="28" y="16" width="3.2" height="12" rx="1.6" />
          <rect x="34" y="20" width="3.2" height="4" rx="1.6" />
        </g>
      </template>

      <!-- E: amber, matching the voice colour rather than the HUD frame -->
      <template v-if="variant === 'amber'">
        <rect x="1" y="1" width="42" height="42" rx="10" fill="#0d0a06" />
        <polygon points="${HEX}" fill="none" stroke="#ffb454" stroke-width="2.2"
                 transform="scale(0.82) translate(4.8, 4.8)" />
        <g fill="#ffb454" transform="scale(0.82) translate(4.8, 4.8)">
          <rect x="15" y="17" width="2.4" height="10" rx="1.2" />
          <rect x="20.8" y="13" width="2.4" height="18" rx="1.2" />
          <rect x="26.6" y="18" width="2.4" height="8" rx="1.2" />
        </g>
      </template>
    </svg>
  `,
});

const VARIANTS = ["squircle", "bare", "solid", "wave", "amber"];

/** All candidates at Dock, Finder and menu-bar sizes, on both backgrounds. */
export const Candidates: StoryObj = {
  render: () => ({
    components: { Icon },
    setup: () => ({ variants: VARIANTS }),
    template: `
      <div style="font:11px/1.4 monospace;display:flex;flex-direction:column;gap:18px">
        <div v-for="bg in ['#1b1b22', '#f2f2f5']" :key="bg"
             :style="{ background: bg, padding: '18px', borderRadius: '10px' }">
          <div style="display:flex;gap:26px;align-items:flex-end">
            <div v-for="v in variants" :key="v"
                 style="display:flex;flex-direction:column;gap:8px;align-items:center">
              <Icon :variant="v" :size="96" />
              <Icon :variant="v" :size="32" />
              <Icon :variant="v" :size="16" />
              <span :style="{ color: bg === '#f2f2f5' ? '#333' : '#aab' }">{{ v }}</span>
            </div>
          </div>
        </div>
      </div>
    `,
  }),
};
