import type { Meta, StoryObj } from "@storybook/vue3";
import "../styles/dashboard.css";
import CatchUpBar from "./CatchUpBar.vue";

const meta: Meta<typeof CatchUpBar> = {
  component: CatchUpBar,
  title: "Dashboard/CatchUpBar",
  render: (args) => ({
    components: { CatchUpBar },
    setup: () => ({ args }),
    // The bubbles column of the conversation frame — never under the rail.
    template: `<main class="hud" style="width:640px;max-width:100%;padding:24px"><CatchUpBar v-bind="args" /></main>`,
  }),
};
export default meta;

/** A muted conversation piled up five messages: hear them, squash them or drop them. */
export const Backlog: StoryObj<typeof CatchUpBar> = {
  args: { count: 5, canSummarize: true },
};

/** The session went offline: nobody can retell, so Summarize rests disabled. */
export const SessionOffline: StoryObj<typeof CatchUpBar> = {
  args: { count: 5, canSummarize: false },
};

/** Narrow window: Skip all wraps below, the two halves stay equal. */
export const Narrow: StoryObj<typeof CatchUpBar> = {
  args: { count: 12, canSummarize: true },
  render: (args) => ({
    components: { CatchUpBar },
    setup: () => ({ args }),
    template: `<main class="hud" style="width:360px;max-width:100%;padding:24px"><CatchUpBar v-bind="args" /></main>`,
  }),
};

/** Nothing unheard: the row is gone, not empty. */
export const NothingUnheard: StoryObj<typeof CatchUpBar> = {
  args: { count: 0, canSummarize: true },
};
