import type { Meta, StoryObj } from "@storybook/vue3";
import App from "../App.vue";
import { resetScenario } from "../storybook/daemon.fixture";

// Capture the actual application layout with isolated demonstration data.
// A parallel marketing layout drifts whenever the product changes.
const meta: Meta = {
  title: "Website/DashboardMarketing",
  component: App,
  parameters: { layout: "fullscreen" },
};
export default meta;

export const Content: StoryObj = {
  render: () => {
    resetScenario("conversation");
    return { components: { App }, template: "<App />" };
  },
};
