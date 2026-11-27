import type { Meta, StoryObj } from "@storybook/vue3";
import DictationBubble from "./DictationBubble.vue";

/* Dictate anywhere: the bubble the desktop shell opens next to the text
 * cursor. Rendered in a frame the size of the shell's window (380x140), on
 * a busy backdrop standing in for the app underneath. States: listening
 * before and after the first words, a long dictation scrolled to its newest
 * words, opened above the cursor, pasting, pasted, not pasted. */
const meta: Meta<typeof DictationBubble> = { component: DictationBubble, title: "Widget/DictationBubble" };
export default meta;

const LONG = "So the plan for today is to finish the dictation overlay, then check how it behaves next to the cursor in a terminal, "
  + "in a browser text area and in the editor, and make sure it never runs off the screen when the cursor is near the bottom edge "
  + "of the display or right next to the Dock, which is exactly where it tends to be.";

const story = (args: object): StoryObj<typeof DictationBubble> => ({
  args: { text: "", phase: "listening", placement: "below", ...args },
  render: (a) => ({
    components: { DictationBubble },
    setup: () => ({ a }),
    template: `<div style="width:380px;height:140px;background:repeating-linear-gradient(45deg,#2a2d33 0 12px,#24262b 12px 24px)"><DictationBubble v-bind="a" /></div>`,
  }),
});

export const Listening = story({});
export const FirstWords = story({ text: "git commit with the message" });
export const LongScrollsToNewest = story({ text: LONG });
export const OpenedAboveTheCursor = story({ text: "fix the flaky test", placement: "above" });
export const Pasting = story({ text: "fix the flaky test", phase: "inserting" });
export const Pasted = story({ text: "fix the flaky test", phase: "inserted" });
export const NotPasted = story({ text: "fix the flaky test", phase: "failed" });
