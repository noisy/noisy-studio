import type { Meta, StoryObj } from "@storybook/vue3";
import { h, type Component } from "vue";
import ListBefore from "./ListBefore.vue";
import AgentTabs from "../../components/AgentTabs.vue";
import ListSections from "./ListSections.vue";
import { projectArgs } from "../../storybook/agentTabs.fixture";
import "../../styles/dashboard.css";

/** A visual design pass on the conversation list: the list as it was,
 *  beside two proposals, all fed the SAME data as Dashboard/AgentTabs
 *  (four projects, "No project", five ended sessions). Here the viewed row
 *  (Bug fixing) is not the mic row (noisy-studio · dashboard), so both
 *  marks show at once.
 *
 *  - Before: the list as patched piece by piece (624f22b).
 *  - A, Ledger: one lead / text / meta grid for headings and rows; quiet
 *    headings, bright titles; hover shows ONE action cluster (key + Settle)
 *    centred on the row's right end.
 *  - B, Sections: the same structure tidied; small-caps section labels with
 *    a hairline; everything hover adds lives on line 2.
 *
 *  A was chosen and IS the production AgentTabs now (this board renders
 *  the real component; Before and B are frozen copies). Why A: one grid
 *  aligns badge/glyph/chevron and every count/wait time at any width (B
 *  and Before leave a hole or a second right edge); a single centred hover
 *  cluster with full-size targets instead of two small stacked boxes; quiet
 *  headings so the titles carry the list; the mic bar sits in the inset,
 *  clear of the selection surface. B's caps and hairlines add noise and its
 *  line-2 Settle is a cramped 18px target.
 */
const meta: Meta = { title: "Lab/ConversationListDesign" };
export default meta;

const VARIANTS: { label: string; component: Component }[] = [
  { label: "BEFORE", component: ListBefore },
  { label: "A · LEDGER (CHOSEN)", component: AgentTabs },
  { label: "B · SECTIONS", component: ListSections },
];
const boardArgs = () => ({ ...projectArgs(true), viewed: "bugs" });
const caption = (text: string) =>
  h("div", { style: "font:700 9px var(--mono, monospace); letter-spacing:.18em; color:var(--muted); margin:0 0 10px 10px;" }, text);
const board = (columns: ReturnType<typeof h>[]) =>
  h("div", { style: "display:flex; gap:40px; align-items:flex-start; padding:24px; background:var(--bg0); min-height:100vh; box-sizing:border-box;" }, columns);

/** The three lists side by side at the default column width (268px). */
export const SideBySide: StoryObj = {
  render: () => () => board(VARIANTS.map(({ label, component }) =>
    h("div", { style: "width:268px; flex:none;" }, [caption(label), h(component, boardArgs())]))),
};

/** The column is resizable: each list at 220, 340 and 560px. */
export const Widths: StoryObj = {
  render: () => () => h("div", { style: "display:flex; flex-direction:column; gap:32px; padding:24px; background:var(--bg0);" },
    VARIANTS.map(({ label, component }) => h("div", {}, [
      caption(label),
      h("div", { style: "display:flex; gap:32px; align-items:flex-start;" }, [220, 340, 560].map((width) =>
        h("div", { style: `width:${width}px; flex:none; outline:1px dashed var(--line);` }, [h(component, { ...boardArgs(), settledOpen: false })]))),
    ]))),
};

/** Hover/focus on the waiting "QA docs" row (key cap + Settle shown), one
 *  story per list since only one row can hold focus. */
const focused = (index: number): StoryObj => ({
  render: () => () => board([h("div", { style: "width:268px; flex:none;" }, [caption(VARIANTS[index].label), h(VARIANTS[index].component, boardArgs())])]),
  play: async ({ canvasElement }) => {
    const qa = [...canvasElement.querySelectorAll<HTMLElement>("button.tab")].find((row) => row.textContent?.includes("QA docs"));
    qa?.querySelector<HTMLElement>(".settle")?.focus();
  },
});
export const FocusedBefore = focused(0);
export const FocusedLedger = focused(1);
export const FocusedSections = focused(2);
