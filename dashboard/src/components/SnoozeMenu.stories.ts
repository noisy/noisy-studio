import type { Meta, StoryObj } from "@storybook/vue3";
import SnoozeMenu from "./SnoozeMenu.vue";
import "../styles/dashboard.css";

const meta: Meta<typeof SnoozeMenu> = {
  component: SnoozeMenu,
  title: "Dashboard/SnoozeMenu",
  decorators: [() => ({ template: '<div style="width:200px;padding:16px"><story /></div>' })],
};
export default meta;

/** The clock on a conversation row opens this: each choice with the time
 *  the conversation comes back (today as "15:30", another day with its
 *  weekday). Tomorrow and Next week wake at 09:00 local time. */
export const WednesdayAfternoon: StoryObj<typeof SnoozeMenu> = {
  args: { now: Math.floor(new Date(2026, 10, 25, 14, 30).getTime() / 1000) },
};
/** Late in the evening the hour choices cross midnight and show the
 *  weekday they land on. */
export const LateEvening: StoryObj<typeof SnoozeMenu> = {
  args: { now: Math.floor(new Date(2026, 10, 25, 23, 30).getTime() / 1000) },
};
