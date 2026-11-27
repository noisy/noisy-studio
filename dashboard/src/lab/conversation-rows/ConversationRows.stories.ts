import type { Meta, StoryObj } from "@storybook/vue3";
import ConversationRows from "./ConversationRows.vue";

/** Three options for the left column's conversation rows, built for the
 *  manager model: a few long-lived conversations, each delegating work.
 *  Each board shows the realistic desk and every remaining state, at the
 *  real 268 px width, in dark and in a proposed light theme. Hover rows to
 *  see actions; the snooze menu and details card start open on their
 *  specimens. See README.md in this folder. */
const meta = {
  title: "Lab/ConversationRows",
  component: ConversationRows,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof ConversationRows>;
export default meta;
type Story = StoryObj<typeof meta>;

export const OptionACalmRows: Story = { args: { option: "a" } };
export const OptionBManagerDesk: Story = { args: { option: "b" } };
export const OptionCOrgTree: Story = { args: { option: "c" } };
