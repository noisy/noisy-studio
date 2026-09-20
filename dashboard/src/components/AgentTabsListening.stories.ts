import type { Meta, StoryObj } from "@storybook/vue3";
import { h } from "vue";
import "../styles/dashboard.css";

/**
 * DESIGN PROPOSAL — "not listening" (deaf) tab state. NOT wired into the app.
 *
 * The harness contract gives every conversation a status: live / idle /
 * deaf / ended. Today AgentTabs only knows online vs offline, and an idle
 * agent whose voice listener has expired looks identical to a listening
 * one — so the user talks into a tab nobody is hearing and gets no signal.
 * "deaf" is NOT "offline": the session is alive, it just is not listening
 * (its Stop-hook window ran out, or a restart cleared its listener), and
 * the honest fix is to type in the terminal or restart the session.
 *
 * These are four visual treatments of that state, plus the "what to do"
 * affordance, for Krzysztof to pick before anything is wired into
 * AgentTabs.vue. Each row pairs a LISTENING/idle tab with a DEAF one so the
 * contrast is visible. Rendered as static markup (the real component has no
 * deaf prop yet); the winning look becomes a `status` on the real tab.
 */

const meta: Meta = { title: "Lab/AgentTabsListening" };
export default meta;
type Story = StoryObj;

const wrap = (title: string, note: string, tabs: ReturnType<typeof h>) =>
  h("div", { style: "display:flex;flex-direction:column;gap:10px;max-width:520px" }, [
    h("div", { style: "font:600 13px var(--sans,system-ui);color:var(--ink,#111)" }, title),
    h("nav", {
      style: "display:flex;flex-wrap:wrap;gap:6px;padding:10px;background:var(--bg,#faf9f7);border:1px solid var(--line,#e6e3de)",
      "aria-label": "Conversations",
    }, tabs),
    h("div", { style: "font:12px var(--sans,system-ui);color:var(--muted,#8a857d)" }, note),
  ]);

const baseTab =
  "position:relative;display:inline-flex;align-items:center;gap:8px;font:13px var(--sans,system-ui);" +
  "border:1px solid transparent;background:transparent;padding:9px 12px;";
const dot = (color: string, extra = "") =>
  h("span", { style: `width:6px;height:6px;border-radius:50%;background:${color};${extra}` });

/** A: slashed ear in the fixed status slot + dashed underline. */
export const A_SlashedEar: Story = {
  render: () =>
    wrap(
      "A · Slashed-ear glyph + dashed underline",
      "A struck-through ear sits in the same fixed status slot as the other glyphs; a dashed underline (not a dashed border, which we reserve for ENDED) marks the tab as not hearing. Tooltip: “Not listening — type in the terminal or restart to wake”.",
      h("div", { style: "display:flex;gap:6px" }, [
        h("button", { style: baseTab + "color:var(--ink,#111)" }, [
          h("span", { style: "width:13px;height:13px;display:inline-flex;align-items:center;justify-content:center" },
            h("svg", { viewBox: "0 0 14 14", width: 13, height: 13 },
              h("path", { d: "M4 9a3 3 0 1 1 5-2", fill: "none", stroke: "var(--green,#3a8)", "stroke-width": 1.4, "stroke-linecap": "round" }))),
          h("span", "planner"),
        ]),
        h("button", { title: "Not listening — type in the terminal or restart to wake",
          style: baseTab + "color:var(--muted,#8a857d);border-bottom:1px dashed var(--red,#c0392b)" }, [
          h("span", { style: "width:13px;height:13px;display:inline-flex;align-items:center;justify-content:center" },
            h("svg", { viewBox: "0 0 14 14", width: 13, height: 13 }, [
              h("path", { d: "M4 9a3 3 0 1 1 5-2", fill: "none", stroke: "var(--red,#c0392b)", "stroke-width": 1.4, "stroke-linecap": "round" }),
              h("line", { x1: 2, y1: 12, x2: 12, y2: 2, stroke: "var(--red,#c0392b)", "stroke-width": 1.4, "stroke-linecap": "round" }),
            ])),
          h("span", "builder"),
        ]),
      ]),
    ),
};

/** B: dimmed tab with a small red "deaf" pill. */
export const B_DeafPill: Story = {
  render: () =>
    wrap(
      "B · Dimmed tab + red “not listening” pill",
      "The tab dims and grows a small red pill that names the state in words. Most explicit, most intrusive; the pill can read “not listening” or carry a verb like “restart to wake”.",
      h("div", { style: "display:flex;gap:6px" }, [
        h("button", { style: baseTab + "color:var(--ink,#111)" }, [dot("var(--muted,#8a857d)"), h("span", "planner")]),
        h("button", { style: baseTab + "color:var(--muted,#8a857d);opacity:.7" }, [
          dot("var(--red,#c0392b)"),
          h("span", "builder"),
          h("span", { style: "font:10px var(--sans,system-ui);color:var(--red,#c0392b);border:1px solid var(--red,#c0392b);border-radius:8px;padding:1px 6px" }, "not listening"),
        ]),
      ]),
    ),
};

/** C: a live "ear" that hollows out; hover reveals a Wake affordance. */
export const C_HollowEar: Story = {
  render: () =>
    wrap(
      "C · Live ear → hollow ear, with a hover “Wake” affordance",
      "A filled ear pulses while listening and goes hollow-grey when deaf — quiet, no color alarm. Hovering the deaf tab reveals a “Wake” control (restart / focus-terminal) in the slot the dismiss ✕ uses on ENDED tabs.",
      h("div", { style: "display:flex;gap:6px" }, [
        h("button", { style: baseTab + "color:var(--ink,#111)" }, [
          h("span", { style: "width:8px;height:8px;border-radius:50% 50% 50% 0;background:var(--green,#3a8)" }),
          h("span", "planner"),
        ]),
        h("button", { title: "Not listening — click Wake to restart", style: baseTab + "color:var(--muted,#8a857d);padding-right:52px" }, [
          h("span", { style: "width:8px;height:8px;border-radius:50% 50% 50% 0;border:1.4px solid var(--muted,#8a857d);background:transparent" }),
          h("span", "builder"),
          h("span", { style: "position:absolute;right:6px;font:10px var(--sans,system-ui);color:var(--amber,#b8860b);border:1px solid var(--amber,#b8860b);border-radius:8px;padding:1px 6px" }, "Wake"),
        ]),
      ]),
    ),
};

/** D: struck-through mic in the fixed slot (mirrors the MUTED glyph). */
export const D_StruckMic: Story = {
  render: () =>
    wrap(
      "D · Struck-through mic in the fixed status slot",
      "Reuses the existing muted-speaker language, mirrored to the input side: a small mic with a slash. Reads as “your voice can’t get in here” and stays inside the one fixed glyph slot, so tab width never shifts. Closest to the current visual grammar.",
      h("div", { style: "display:flex;gap:6px" }, [
        h("button", { style: baseTab + "color:var(--ink,#111)" }, [dot("var(--muted,#8a857d)"), h("span", "planner")]),
        h("button", { title: "Not listening — type in the terminal or restart", style: baseTab + "color:var(--muted,#8a857d)" }, [
          h("span", { style: "width:13px;height:13px;display:inline-flex;align-items:center;justify-content:center" },
            h("svg", { viewBox: "0 0 14 14", width: 14, height: 14 }, [
              h("rect", { x: 5.2, y: 2, width: 3.6, height: 6.4, rx: 1.8, fill: "var(--red,#c0392b)" }),
              h("path", { d: "M3.6 7.2a3.4 3.4 0 0 0 6.8 0", fill: "none", stroke: "var(--red,#c0392b)", "stroke-width": 1.2 }),
              h("line", { x1: 2, y1: 12, x2: 12, y2: 2, stroke: "var(--red,#c0392b)", "stroke-width": 1.4, "stroke-linecap": "round" }),
            ])),
          h("span", "builder"),
        ]),
      ]),
    ),
};

/** All four side by side, for the pick. */
export const Compare: Story = {
  render: () =>
    h("div", { style: "display:flex;flex-direction:column;gap:22px" },
      [A_SlashedEar, B_DeafPill, C_HollowEar, D_StruckMic].map((s: any) => s.render())),
};
