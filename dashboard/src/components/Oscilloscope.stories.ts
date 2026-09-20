import type { Meta, StoryObj } from "@storybook/vue3";
import Oscilloscope from "./Oscilloscope.vue";
import SpectrumBars from "./SpectrumBars.vue";

const meta: Meta = {
  title: "Dashboard/Oscilloscope",
  argTypes: { level: { control: { type: "range", min: 0, max: 1, step: 0.05 } } },
};
export default meta;

export const Wave: StoryObj = {
  args: { level: 0.6 },
  render: (args) => ({
    components: { Oscilloscope },
    setup: () => ({ args }),
    template: `<div style="max-width:420px"><Oscilloscope :level="args.level" /></div>`,
  }),
};

export const Spectrum: StoryObj = {
  args: { level: 0.6 },
  render: (args) => ({
    components: { SpectrumBars },
    setup: () => ({ args }),
    template: `<div style="max-width:420px"><SpectrumBars :level="args.level" /></div>`,
  }),
};
