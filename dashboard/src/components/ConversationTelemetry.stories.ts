import type { Meta, StoryObj } from "@storybook/vue3";
import ConversationTelemetry from "./ConversationTelemetry.vue";

const meta: Meta<typeof ConversationTelemetry> = {
  component: ConversationTelemetry,
  title: "Dashboard/ConversationTelemetry",
};
export default meta;

/** Healthy pipeline: green latencies, a session's worth of cost. */
export const Healthy: StoryObj<typeof ConversationTelemetry> = {
  args: {
    sttLatencyMs: 320,
    ttsLatencyMs: 1100,
    userCostUsd: 0.0141,
    claudeCostUsd: 0.0212,
    sttSeconds: 542,
    ttsChars: 21_400,
  },
};

/** Degraded: STT in the warn band, TTS over the bad threshold. */
export const Degraded: StoryObj<typeof ConversationTelemetry> = {
  args: {
    sttLatencyMs: 840,
    ttsLatencyMs: 3400,
    userCostUsd: 0.0141,
    claudeCostUsd: 0.0212,
    sttSeconds: 542,
    ttsChars: 21_400,
  },
};

/** Fresh session: no measurements yet, zero cost. */
export const Empty: StoryObj<typeof ConversationTelemetry> = {
  args: {
    sttLatencyMs: null,
    ttsLatencyMs: null,
    userCostUsd: 0,
    claudeCostUsd: 0,
    sttSeconds: 0,
    ttsChars: 0,
  },
};
