import type { Meta, StoryObj } from "@storybook/vue3";
import ReviewWorkspace from "./ReviewWorkspace.vue";
import { resetScenario } from "../../storybook/daemon.fixture";
const meta = {
  title: "Lab/Task Review",
  component: ReviewWorkspace,
  parameters: { layout: "fullscreen" },
  render: (args) => {
    resetScenario("conversation", {
      version: __APP_VERSION__,
      latest_version: __APP_VERSION__,
    });
    return {
      components: { ReviewWorkspace },
      setup: () => ({ args }),
      template: '<ReviewWorkspace v-bind="args" />',
    };
  },
} satisfies Meta<typeof ReviewWorkspace>;
export default meta;
type Story = StoryObj<typeof meta>;
export const FloatingControls: Story = { args: { placement: "floating" } };
export const TopStrip: Story = { args: { placement: "strip" } };
export const SideDock: Story = { args: { placement: "dock" } };
export const CannotEmbed: Story = {
  args: { placement: "floating", unavailable: true },
};
