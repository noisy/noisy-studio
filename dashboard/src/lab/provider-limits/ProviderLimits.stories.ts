import type { Meta, StoryObj } from "@storybook/vue3";
import DashboardLimits from "./DashboardLimits.vue";
import { resetScenario } from "../../storybook/daemon.fixture";
const meta = {
  title: "Lab/Provider Limits",
  component: DashboardLimits,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Synthetic design only. Actual dashboard with fixture conversations; quota percentages and reset times are illustrative. No accounts connected.",
      },
    },
  },
  render: (args) => {
    resetScenario("conversation", {
      version: __APP_VERSION__,
      latest_version: __APP_VERSION__,
    });
    return {
      components: { DashboardLimits },
      setup: () => ({ args }),
      template: '<DashboardLimits v-bind="args" />',
    };
  },
} satisfies Meta<typeof DashboardLimits>;
export default meta;
type Story = StoryObj<typeof meta>;
export const ThinBars: Story = { args: { variant: "rows" } };
export const BoldBars: Story = { args: { variant: "inset" } };
export const ThreeColumns: Story = { args: { variant: "columns" } };
