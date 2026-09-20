import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, ref } from "vue";
import CompanionCrewScene from "./marketing/CompanionCrewScene.vue";

/* Synthetic screenshots: three agents sharing one widget, one voice at a time.
 *
 * The scene itself lives in marketing/CompanionCrewScene.vue, because the
 * website's crew section renders the SAME component - one definition, so
 * the story and the site cannot drift. What stays here is the chrome the
 * story wants and the website must never show: the sound toggle and the
 * step-through buttons.
 */
const meta: Meta = {
  title: "Website/CompanionCrew",
  parameters: { layout: "fullscreen" },
};
export default meta;

const CONTROLS = {
  position: "absolute" as const,
  left: "24px",
  top: "24px",
  display: "flex",
  alignItems: "center",
  gap: "10px",
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  fontSize: "13px",
  color: "rgba(233,231,245,0.85)",
  zIndex: "3",
};

const BUTTON = {
  background: "rgba(255,255,255,0.08)",
  border: "1px solid rgba(255,255,255,0.22)",
  borderRadius: "6px",
  color: "inherit",
  font: "inherit",
  padding: "6px 12px",
  cursor: "pointer",
};

/** The scene plus the story's own controls, laid over its top-left corner.
 *  Everything here talks to the scene through its exposed API - the story
 *  drives the scene, it does not reach into it. */
const CrewStory = defineComponent({
  components: { CompanionCrewScene },
  props: {
    camera: { type: Boolean, default: false },
    manual: { type: Boolean, default: false },
  },
  setup() {
    const scene = ref<InstanceType<typeof CompanionCrewScene> | null>(null);
    return { scene, CONTROLS, BUTTON };
  },
  template: `
    <div style="position: relative; display: inline-block">
      <!-- Controls FIRST in document order: the widget's own avatar rail is
           made of buttons too, and the spec (and anyone tabbing) reaches
           the story's controls before the scene's internals. -->
      <div :style="CONTROLS">
        <button type="button" :style="BUTTON" data-testid="sound-toggle"
                @click="scene?.toggleSound()">{{ scene?.soundOn ? 'SOUND OFF' : 'SOUND ON' }}</button>
        <template v-if="manual">
          <button type="button" :style="BUTTON" @click="scene?.step(-1)">BACK</button>
          <button type="button" :style="BUTTON" @click="scene?.step(1)">NEXT</button>
          <button type="button" :style="BUTTON" @click="scene?.restart()">RESTART</button>
          <span data-testid="beat-readout">{{ scene?.readout }}</span>
        </template>
      </div>
      <CompanionCrewScene ref="scene" :camera="camera" :manual="manual" />
    </div>
  `,
});

/** The loop: deploy gate, PR interrupt, personal reminder, repeat.
 *  Static camera by default; flip the `camera` control to put the zoom
 *  back on the handovers. */
export const Crew: StoryObj = {
  argTypes: { camera: { control: "boolean" } },
  args: { camera: false },
  render: (args) => ({
    components: { CrewStory },
    setup: () => ({ args }),
    template: `<CrewStory :camera="args.camera" />`,
  }),
};

/** The same scene with the clock in your hands: NEXT/BACK walk the beats
 *  one at a time, the readout names the one you are looking at, and no
 *  timer is running behind you. */
export const Step: StoryObj = {
  ...Crew,
  render: (args) => ({
    components: { CrewStory },
    setup: () => ({ args }),
    template: `<CrewStory manual :camera="args.camera" />`,
  }),
};
