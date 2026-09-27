import type { Meta, StoryObj } from "@storybook/vue3";
import CompactUsage from "./CompactUsage.vue";
const meta = {
  title: "Lab/Compact Usage",
  component: CompactUsage,
  parameters: { layout: "fullscreen" },
  args: { variant: "meters", light: false, startInDetails: false },
  argTypes: {
    variant: { control: "select", options: ["meters", "rows", "badges"] },
  },
} satisfies Meta<typeof CompactUsage>;
export default meta;
type Story = StoryObj<typeof meta>;
export const TinyMeters: Story = {};
export const TextAndReset: Story = { args: { variant: "rows" } };
export const SingleLineBadges: Story = { args: { variant: "badges" } };
export const UsageHistory: Story = { args: { startInDetails: true } };
export const LightDashboard: Story = { args: { light: true } };
export const LightUsage: Story = {
  args: { light: true, startInDetails: true },
};
