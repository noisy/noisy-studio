import type { Meta, StoryObj } from "@storybook/vue3";
import type { Utterance } from "../types";
import AgentBubble from "./AgentBubble.vue";
import UserBubble from "./UserBubble.vue";

const meta: Meta = { title: "Dashboard/Bubble" };
export default meta;

function utterance(overrides: Partial<Utterance>): Utterance {
  return {
    id: 1,
    role: "user",
    status: "delivered to Claude",
    text: "Okej, odpal deploy na staging i daj znać jak skończy.",
    detail: "STT 0.9 s · 6.4 s AUDIO",
    cost_usd: 0.0004,
    agent: null,
    started_at: Date.now() / 1000,
    updated_at: Date.now() / 1000,
    committed_at: Date.now() / 1000,
    ...overrides,
  };
}

const feedStyle = "display:flex; flex-direction:column; gap:12px; max-width:720px";

export const Recording: StoryObj = {
  render: () => ({
    components: { UserBubble },
    setup: () => ({ u: utterance({ status: "recording…", text: "No dobra, to teraz przejdźmy do refaktoru", cost_usd: 0 }) }),
    template: `<div style="${feedStyle}"><UserBubble :utterance="u" /></div>`,
  }),
};

export const Delivered: StoryObj = {
  render: () => ({
    components: { UserBubble },
    setup: () => ({ u: utterance({}) }),
    template: `<div style="${feedStyle}"><UserBubble :utterance="u" /></div>`,
  }),
};

export const ClaudeSynthesizing: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({ role: "claude", status: "synthesizing (Grok TTS)…", text: "", cost_usd: 0 }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" /></div>`,
  }),
};

export const ClaudePlayed: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        text: "[altair] „Pipeline #48210 passed — 214 tests green.”",
        detail: "streaming from Grok TTS",
        cost_usd: 0.0038,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" /></div>`,
  }),
};


export const SubagentPortraitLuna: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        speaker: "researcher",
        voice: "luna",
        text: "Findings: three of the five endpoints lack rate limiting.",
        detail: "streaming from Grok TTS",
        cost_usd: 0.0034,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" /></div>`,
  }),
};

/** Chat-platform tints: the speaker's bubble carries its platform's brand
 *  color - Twitch purple, YouTube red - while plain subagents stay green. */
export const ChatTwitchPurple: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        speaker: "xfuroo",
        voice: "eve",
        text: "gg, the widget looks way better today",
        cost_usd: 0.0021,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" tint="purple" label="Twitch · xfuroo" /></div>`,
  }),
};

export const ChatModeratorNormal: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        speaker: "luna",
        voice: "luna",
        text: "Reading the chat: three greetings and one question about the widget.",
        cost_usd: 0.003,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" tint="normal" label="Luna - chat agent" /></div>`,
  }),
};

export const ChatYouTubeRed: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        speaker: "DevWatcher42",
        voice: "atlas",
        text: "first! greetings from the red side",
        cost_usd: 0.0021,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" tint="red" label="YouTube · DevWatcher42" /></div>`,
  }),
};

export const SubagentPortraitAltair: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        speaker: "reviewer",
        voice: "altair",
        text: "Review done - two blocking comments, rest is clean.",
        detail: "streaming from Grok TTS",
        cost_usd: 0.0029,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" /></div>`,
  }),
};

export const ClaudePlaying: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        text: "Playback in progress - you can pause me mid-sentence or skip the rest entirely.",
        detail: "streaming from Grok TTS",
        cost_usd: 0.0031,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" :playing="true" /></div>`,
  }),
};

export const ClaudePaused: StoryObj = {
  render: () => ({
    components: { AgentBubble },
    setup: () => ({
      u: utterance({
        role: "claude",
        status: "played",
        text: "Paused mid-utterance - resume picks up right where we stopped.",
        detail: "streaming from Grok TTS",
        cost_usd: 0.0031,
      }),
    }),
    template: `<div style="${feedStyle}"><AgentBubble :utterance="u" :playing="true" :paused="true" /></div>`,
  }),
};
