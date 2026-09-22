import type { Meta, StoryObj } from "@storybook/vue3";
import VoicePersona from "./VoicePersona.vue";

const meta: Meta<typeof VoicePersona> = {
  component: VoicePersona,
  title: "Dashboard/VoicePersona",
  decorators: [() => ({ template: '<div style="width:300px;background:#04101a;padding:16px;"><story /></div>' })],
};
export default meta;

/** Idle portrait with the selector collapsed beneath. */
export const Idle: StoryObj<typeof VoicePersona> = {
  args: { voice: "leo", speaking: false },
};

/** ON AIR badge rides over the portrait while the agent speaks. */
export const Speaking: StoryObj<typeof VoicePersona> = {
  args: { voice: "lux", speaking: true },
};

/** A voice without a sprite falls back to the monogram hexagon. */
export const NoPortrait: StoryObj<typeof VoicePersona> = {
  args: { voice: "mystery", speaking: false },
};

export const Saving: StoryObj<typeof VoicePersona> = {
  args: { voice: "iris", pending: true },
};
export const SaveFailed: StoryObj<typeof VoicePersona> = {
  args: { voice: "leo", error: "Could not save character settings. Try again." },
};
