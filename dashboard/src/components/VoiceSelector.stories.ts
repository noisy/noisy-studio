import type { Meta, StoryObj } from "@storybook/vue3";
import VoiceSelector from "./VoiceSelector.vue";

const meta: Meta<typeof VoiceSelector> = {
  component: VoiceSelector,
  title: "Dashboard/VoiceSelector",
  decorators: [() => ({ template: '<div style="width:300px;background:#04101a;padding:16px;"><story /></div>' })],
};
export default meta;

/** Collapsed: the VOICE label, current pick and gender in one row —
 *  click to unfold the full grid. */
export const Collapsed: StoryObj<typeof VoiceSelector> = {
  args: { voice: "carina" },
};

/** No voice picked yet (fresh daemon). */
export const NoVoice: StoryObj<typeof VoiceSelector> = {
  args: { voice: "" },
};
