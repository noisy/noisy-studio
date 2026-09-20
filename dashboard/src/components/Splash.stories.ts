import type { Meta, StoryObj } from "@storybook/vue3";
import Splash from "./Splash.vue";

/* The launch splash (#96) as shipped: icon and name as one lockup, the
 * progress line under it (round-2 variant F). Rendered at the Electron
 * window's real size, 320x170. The alternatives live in
 * Splash.variants.stories.ts. */
const meta: Meta<typeof Splash> = { component: Splash, title: "Dashboard/Splash" };
export default meta;

export const Chosen: StoryObj<typeof Splash> = {
  args: { look: "row" },
  render: (args) => ({
    components: { Splash },
    setup: () => ({ args }),
    template: `<div style="padding:24px;background:#0b0c0e;display:inline-block;border-radius:12px"><Splash v-bind="args" style="border-radius:10px;box-shadow:0 12px 40px rgba(0,0,0,.6)" /></div>`,
  }),
};
