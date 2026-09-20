import type { Meta, StoryObj } from "@storybook/vue3";
import type { Utterance } from "../types";
import ConversationLog from "./ConversationLog.vue";

const meta: Meta<typeof ConversationLog> = {
  component: ConversationLog,
  title: "HUD/ConversationLog",
};
export default meta;

const now = Date.now() / 1000;
const feed: Utterance[] = [
  { id: 1, role: "user", status: "delivered to Claude", text: "Sprawdź czy pipeline na branchu feature/auth przeszedł.", detail: "STT 1.1 s · 7.8 s AUDIO", cost_usd: 0.0005, agent: null, started_at: now - 260, updated_at: now - 250, committed_at: now - 260 },
  { id: 2, role: "claude", status: "played", text: "[altair] „Pipeline #48210 passed — 214 tests green.”", detail: "TTS 1.4 s · 11.2 s AUDIO", cost_usd: 0.0038, agent: null, started_at: now - 240, updated_at: now - 230, committed_at: now - 240 },
  { id: 3, role: "user", status: "delivered to Claude", text: "Okej, odpal deploy na staging i daj znać jak skończy.", detail: "STT 0.9 s · 6.4 s AUDIO", cost_usd: 0.0004, agent: null, started_at: now - 120, updated_at: now - 110, committed_at: now - 120 },
  { id: 4, role: "claude", status: "synthesizing (Grok TTS)…", text: "", detail: "QUEUE POS 1", cost_usd: 0, agent: null, started_at: now - 20, updated_at: now - 20, committed_at: now - 20 },
  { id: 5, role: "user", status: "recording…", text: "No dobra, to teraz przejdźmy do refaktoru modułu billing i", detail: "VAD OPEN · 3.2 s", cost_usd: 0, agent: null, started_at: now - 4, updated_at: now, committed_at: now - 4 },
];

export const Feed: StoryObj<typeof ConversationLog> = {
  args: { utterances: feed },
  render: (args) => ({
    components: { ConversationLog },
    setup: () => ({ args }),
    template: `<div style="max-width:760px"><ConversationLog v-bind="args" /></div>`,
  }),
};

export const AgentMetadata: StoryObj<typeof ConversationLog> = {
  ...Feed,
  args: {
    utterances: feed.map((row) => ({ ...row, agent_label: "Build assistant" })),
  },
};

// #22: a subagent's speech stays in the parent conversation's feed, but is
// clearly NOT the main agent - own name, own accent. This story is the
// design surface for that decoration.
const subagentFeed: Utterance[] = [
  { id: 1, role: "user", status: "delivered to Claude", text: "Spawn a researcher and summarize the findings aloud.", detail: "STT 0.8 s · 5.2 s AUDIO", cost_usd: 0.0004, agent: null, started_at: now - 200, updated_at: now - 195, committed_at: now - 200 },
  { id: 2, role: "claude", status: "played", voice: "lux", text: "On it - the researcher will report back in a moment.", detail: "TTS 1.2 s · 6.0 s AUDIO", cost_usd: 0.0021, agent: null, started_at: now - 180, updated_at: now - 170, committed_at: now - 180 },
  { id: 3, role: "claude", status: "played", speaker: "researcher", voice: "luna", text: "Findings: three of the five endpoints lack rate limiting - details on screen.", detail: "TTS 1.5 s · 9.4 s AUDIO", cost_usd: 0.0034, agent: null, started_at: now - 120, updated_at: now - 110, committed_at: now - 120 },
  { id: 4, role: "claude", status: "played", voice: "lux", text: "That matches my read - I suggest we fix the auth endpoint first.", detail: "TTS 1.1 s · 7.2 s AUDIO", cost_usd: 0.0025, agent: null, started_at: now - 60, updated_at: now - 50, committed_at: now - 60 },
];

export const WithSubagent: StoryObj<typeof ConversationLog> = {
  args: { utterances: subagentFeed },
  render: (args) => ({
    components: { ConversationLog },
    setup: () => ({ args }),
    template: `<div style="max-width:760px"><ConversationLog v-bind="args" /></div>`,
  }),
};

export const InboxDeliveryStates: StoryObj<typeof ConversationLog> = {
  ...Feed,
  args: {utterances: [
    ["delivery confirmed", "Receiving agent acknowledged this message; task completion is separate."],
    ["delivery unknown", "No acknowledgement received from Claude. It may have arrived; check the session before resending. No automatic resend. Receipt support requires the updated Noisy Studio MCP tools."],
    ["sent — unconfirmed", "Written to the inbox; the host may hold or refuse it."],
    ["delivery uncertain — not retried", "The connection ended during the write. No automatic resend."],
    ["unavailable — registration required", "Type once in this Claude session to register it again."],
    ["delivery rejected", "The registered endpoint could not be used."],
  ].map(([status, delivery_detail], index) => ({
    ...feed[0]!, id: index + 20, text: "Please check the release changes.",
    status, delivery_detail, agent_label: "Release assistant",
  }))},
};
