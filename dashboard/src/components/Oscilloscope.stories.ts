import type { Meta, StoryObj } from "@storybook/vue3";
import Oscilloscope from "./Oscilloscope.vue";

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

// The size it is drawn at in the header's YOU · INPUT group.
export const HeaderMeter: StoryObj = {
  args: { level: 0.6 },
  render: (args) => ({
    components: { Oscilloscope },
    setup: () => ({ args }),
    template: `<div style="width:84px;height:30px"><Oscilloscope :level="args.level" style="height:100%;min-height:0" /></div>`,
  }),
};
