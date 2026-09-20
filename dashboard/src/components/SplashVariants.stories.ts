import type { Meta, StoryObj } from "@storybook/vue3";
import Splash from "./Splash.vue";

/* The splash looks that were NOT chosen (#96), kept next to the shipped one
 * for comparison. Round 1: A Mark won on idea, lost on balance (B had no
 * logo, C's name sat oddly, D's ring hid behind the name - those three are
 * gone). Round 2 iterated on A; F Row was picked. */
const meta: Meta<typeof Splash> = { component: Splash, title: "Lab/SplashVariants" };
export default meta;

const at = (look: "mark" | "spaced" | "edge" | "icon-only"): StoryObj<typeof Splash> => ({
  args: { look },
  render: (args) => ({
    components: { Splash },
    setup: () => ({ args }),
    template: `<div style="padding:24px;background:#0b0c0e;display:inline-block;border-radius:12px"><Splash v-bind="args" style="border-radius:10px;box-shadow:0 12px 40px rgba(0,0,0,.6)" /></div>`,
  }),
});

export const A_Mark = at("mark");
export const E_Spaced = at("spaced");
export const G_EdgeLine = at("edge");
export const H_IconOnly = at("icon-only");
