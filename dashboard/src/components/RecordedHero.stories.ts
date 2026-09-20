import type { Meta, StoryObj } from "@storybook/vue3";
import { ref, onMounted, onBeforeUnmount } from "vue";
import RecordedHeroScene from "./marketing/RecordedHeroScene.vue";

const meta: Meta<typeof RecordedHeroScene> = {
  title: "Website/RecordedHero",
  component: RecordedHeroScene,
  parameters: { layout: "fullscreen" },
  args: { cameraZoom: 1.35, cameraOffsetX: 0, cameraOffsetY: 0 },
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
export const RecordingV1: StoryObj<typeof RecordedHeroScene> = {
  name: "Recording V1",
  render: args => ({
    components: { RecordedHeroScene },
    setup() {
      const scene = ref<InstanceType<typeof RecordedHeroScene>>();
      const frame = ref<HTMLElement>();
      const scale = ref(1);
      let observer: ResizeObserver;
      onMounted(() => {
        observer = new ResizeObserver(() => { scale.value = Math.min(1, (frame.value?.clientWidth ?? 1200) / 1200); });
        if (frame.value) observer.observe(frame.value);
      });
      onBeforeUnmount(() => observer?.disconnect());
      return { args, scene, frame, scale };
    },
    template: `<div><div style="padding:12px;display:flex;gap:12px;background:#18191e;color:white">
      <button @click="scene?.restart(); scene?.toggleSound()">Replay / toggle sound</button>
      <span>Camera {{ args.cameraZoom.toFixed(2) }}× · visible {{ Math.round(100 / args.cameraZoom) }}% · X {{ args.cameraOffsetX }} · Y {{ args.cameraOffsetY }} · adjust in Controls</span>
      </div><div ref="frame" :style="{height: (760 * scale) + 'px', overflow: 'hidden'}"><RecordedHeroScene ref="scene" v-bind="args" :style="{transform: 'scale(' + scale + ')', transformOrigin: 'top left'}" /></div></div>`,
  }),
};
