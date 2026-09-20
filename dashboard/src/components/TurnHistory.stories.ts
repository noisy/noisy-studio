import type { Meta, StoryObj } from "@storybook/vue3";
import TurnHistory from "./TurnHistory.vue";
import type { Utterance } from "../types";

const meta: Meta<typeof TurnHistory> = {
  title: "Dashboard/TurnHistory", component: TurnHistory, parameters: { layout: "centered" },
  decorators: [() => ({ template: '<div style="width:220px;padding:16px;background:var(--panel);border-radius:12px"><story /></div>' })],
};
export default meta;
type Story = StoryObj<typeof TurnHistory>;
const turns = (count: number): Utterance[] => Array.from({ length: count }, (_, i) => ({
  id: i + 1, role: i % 2 ? "claude" : "user", status: "played", text: "A spoken turn", detail: "", cost_usd: 0,
  agent: null, started_at: 100 + i * 30, updated_at: 105 + i * 30, committed_at: 105 + i * 30, duration_s: i % 2 ? 12 : 5,
}));
export const Mixed: Story = { args: { utterances: turns(4) } };
export const Empty: Story = { args: { utterances: [] } };
export const OneTurn: Story = { args: { utterances: turns(1) } };
export const LongSession: Story = { args: { utterances: turns(64) } };
