import type { Meta, StoryObj } from "@storybook/vue3";
import CharacterMock from "./marketing/CharacterMock.vue";

/* The character-settings shot: persona portrait + trait dials, no OS
 * chrome. Same deal as Synthetic Screenshots/App - the landing pages
 * frame captures themselves, so this story renders the bare panel at
 * 420x900 for scripts/marketing-shots.sh.
 */
const meta: Meta = {
  title: "Website/CharacterMarketing",
  parameters: { layout: "fullscreen" },
};
export default meta;

export const Panel: StoryObj = {
  render: () => ({
    components: { CharacterMock },
    template: `<CharacterMock />`,
  }),
};
