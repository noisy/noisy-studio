import type { Meta, StoryObj } from "@storybook/vue3";
import HudPanel from "./HudPanel.vue";

const meta: Meta<typeof HudPanel> = {
  component: HudPanel,
  title: "Dashboard/HudPanel",
};
export default meta;

type Story = StoryObj<typeof HudPanel>;

export const Basic: Story = {
  args: { index: "01", title: "MIC INPUT · OSCILLOSCOPE" },
  render: (args) => ({
    components: { HudPanel },
    setup: () => ({ args }),
    template: `<HudPanel v-bind="args"><div style="height:80px; display:grid; place-items:center; color:var(--muted)">panel content</div></HudPanel>`,
  }),
};
