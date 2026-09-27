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
export const CompactHeader: Story = { args: { header: "inline" } };
export const ConversationRibbon: Story = { args: { header: "ribbon" } };
export const CompanionHeader: Story = { args: { header: "companion" } };
export const CannotEmbed: Story = {
  args: { header: "inline", unavailable: true },
};
