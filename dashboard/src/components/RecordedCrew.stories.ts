import type { Meta, StoryObj } from "@storybook/vue3";
import { ref } from "vue";
import RecordedCrewScene from "./marketing/RecordedCrewScene.vue";

const meta: Meta<typeof RecordedCrewScene> = {
  title: "Website/RecordedCrew",
  component: RecordedCrewScene,
  parameters: { layout: "fullscreen" },
  args: { camera: true, compact: false, cameraZoom: 1.35, cameraOffsetX: 0, cameraOffsetY: 0 },
  argTypes: {
    cameraZoom: {
      name: "Camera zoom",
      description: "1× = full frame; 2× = central 50%; 2.5× = central 40%. Only the webcam crop changes.",
      control: { type: "range", min: 1, max: 4, step: 0.05 },
    },
    cameraOffsetX: {
      name: "Camera offset X",
      description: "Moves the image left (negative) or right (positive). ±100 reaches the available edge at the current zoom; 0 centers it.",
      control: { type: "range", min: -100, max: 100, step: 1 },
    },
    cameraOffsetY: {
      name: "Camera offset Y",
      description: "Moves the image up (negative) or down (positive). ±100 reaches the available edge at the current zoom; 0 centers it.",
      control: { type: "range", min: -100, max: 100, step: 1 },
    },
  },
};
export default meta;
export const RecordingV1: StoryObj<typeof RecordedCrewScene> = {
  name: "Recording V5",
  render: args => ({
    components: { RecordedCrewScene },
    setup() {
      const scene = ref<InstanceType<typeof RecordedCrewScene>>();
      return { args, scene };
    },
    template: `<div><div style="padding:12px;display:flex;gap:12px;background:#18191e;color:white">
      <button @click="scene?.restart(); scene?.toggleSound()">Replay / toggle sound</button>
      <span>Camera {{ args.cameraZoom.toFixed(2) }}× · visible {{ Math.round(100 / args.cameraZoom) }}% · X {{ args.cameraOffsetX }} · Y {{ args.cameraOffsetY }} · adjust in Controls</span>
      </div><RecordedCrewScene ref="scene" v-bind="args" /></div>`,
  }),
};
