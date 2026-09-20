import type { Meta, StoryObj } from "@storybook/vue3";
import ShutdownBanner from "./ShutdownBanner.vue";

const meta: Meta = { title: "Dashboard/ShutdownBanner" };
export default meta;

const wrap = (variant: string) => ({
  components: { ShutdownBanner },
  setup: () => ({ variant }),
  // Full-width context: this bar sits at the very top of the page.
  template: `<div style="width:100%;display:flex;flex-direction:column;gap:14px">
    <ShutdownBanner :variant="variant" label="4:52" />
    <ShutdownBanner :variant="variant" label="9s" />
  </div>`,
});

export const D5_ThreeColumns: StoryObj = { render: () => wrap("card-d5") };
