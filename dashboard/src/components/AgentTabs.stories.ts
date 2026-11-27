import type { Meta, StoryObj } from "@storybook/vue3";
import { h, ref } from "vue";
import AgentTabs from "./AgentTabs.vue";
import HudPanel from "./HudPanel.vue";
import { projectArgs, SETTLED_AGENTS } from "../storybook/agentTabs.fixture";
import "../styles/dashboard.css";

const meta: Meta<typeof AgentTabs> = {
  component: AgentTabs,
  title: "Dashboard/AgentTabs",
};
export default meta;

/** Old daemons and saved sessions may still send path-shaped labels (#107). */
export const UnsafeSavedNames: StoryObj<typeof AgentTabs> = {
  args: {
    agents: {
      "session-1": "/private/example/session-1",
      "session-2": "Release review",
      "session-3": "C:\\projects\\session-3",
    },
    active: "session-2", viewed: "session-2", speaking: [],
  },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};

/** The canonical tab-state matrix, rendered by the REAL component.
 *
 *  Rows: is this the selected row (highlighted, and here also the mic
 *  recipient: green bar in the inset) or a background one. Columns: the single
 *  status glyph, option-B priority ladder: MUTE (with or without a waiting
 *  count) > SPEAKING (green equalizer) > WAIT count (amber) > WORKING
 *  (violet) > idle (empty slot). WORK+3 shows the count outranking work, SPEAK+3 the
 *  count hidden while it speaks; ENDED shows the greyed row of a session
 *  that ended (it lives in Settled, opened here; hover offers Restore). Every
 *  live row offers Settle (beside its key cap) on hover/focus, the mic's too - settling the
 *  mic's row hands the mic to the next conversation. Liveness comes from
 *  the daemon's conversation registry, not heartbeats.
 */
export const StateMatrix: StoryObj<typeof AgentTabs> = {
  render: () => {
    const COLUMNS = [
      { key: "idle", label: "IDLE" },
      { key: "wait", label: "WAIT 3" },
      { key: "working", label: "WORKING" },
      { key: "work3", label: "WORK + 3" },
      { key: "speaking", label: "SPEAKING" },
      { key: "speak3", label: "SPEAK + 3" },
      { key: "muted", label: "MUTED" },
      { key: "mute3", label: "MUTE + 3" },
      { key: "offline", label: "ENDED" },
    ] as const;
    const ROWS = [
      { key: "sel", label: "SELECTED", selected: true },
      { key: "bg", label: "BACKGROUND", selected: false },
    ] as const;

    const cell = (row: (typeof ROWS)[number], col: (typeof COLUMNS)[number]) => {
      // Not ending in the label: an id-shaped label reads as "New conversation".
      const name = `${row.key}-${col.key}-cell`;
      const label = col.label.toLowerCase().replace(" + 3", "");
      return h(AgentTabs, {
        agents: { [name]: label },
        meta: {
          [name]: {
            label,
            online: col.key !== "offline",
            activated_at: 1,
            offline_since: col.key === "offline" ? 100 : null,
          },
        },
        active: row.selected ? name : null,
        viewed: row.selected ? name : null,
        speaking: col.key.startsWith("speak") ? [name] : [],
        thinking: col.key.startsWith("work") ? [name] : [],
        muted: col.key.startsWith("mute") ? [name] : [],
        queued: ["wait", "work3", "speak3", "mute3"].includes(col.key) ? { [name]: 3 } : {},
        settledOpen: true,
      });
    };

    const head =
      "font: 700 9px monospace; letter-spacing: 0.18em; color: #5d7f96; padding: 4px;";
    return () =>
      h(
        "div",
        {
          style:
            "display: grid; grid-template-columns: 100px repeat(9, 150px); gap: 10px 12px; align-items: end; background: #04101a; padding: 20px; justify-content: start;",
        },
        [
          h("div"),
          ...COLUMNS.map((c) => h("div", { style: head }, c.label)),
          ...ROWS.flatMap((row) => [
            h("div", { style: head }, row.label),
            ...COLUMNS.map((col) => h("div", cell(row, col))),
          ]),
        ],
      );
  },
};

/** The list in the dashboard's left column, beside the conversation frame,
 *  with the production layout styles. Click a row to move the microphone. */
export const ListBesideWindow: StoryObj<typeof AgentTabs> = {
  render: () => ({
    components: { AgentTabs, HudPanel },
    setup() {
      const active = ref('codex');
      const agents = { codex: 'Codex', review: 'Code review', docs: 'Documentation' };
      return { active, agents };
    },
    template: `<main class="hud" style="height:420px;min-height:0;padding:24px">
      <div class="cols" style="--left-column-width:268px">
        <div class="col-left"><AgentTabs class="convo-list" :agents="agents" :active="active" :viewed="active" :speaking="[]" @select="active = $event" /></div>
        <div class="col-mid">
          <HudPanel class="convo-panel" style="min-height:220px">
            <p>Switch conversations to move the microphone recipient.</p>
          </HudPanel>
        </div>
      </div>
    </main>`,
  }),
};

/** The list grouped by project, as the daemon derives it from each
 *  session's repository (worktrees fold into the main repo). Projects keep
 *  their order whatever their conversations do; the amber number in a
 *  project heading counts the messages waiting for you there. Working is the
 *  violet glyph on a row, not a place. Ended sessions fold into Settled.
 *
 *  Layout: every heading and row sits on one lead | text | meta grid, so
 *  badges, glyphs and the Settled chevron share a column and every count and
 *  wait time ends on the same right edge (see Lab/ConversationListDesign). */
/** Hover a row to see its talk key and Settle, as one cluster over the
 *  row's right end; right-click it to capture its own talk key (any chord).
 *  Idle rows have an empty status slot. */
export const Projects: StoryObj<typeof AgentTabs> = {
  args: projectArgs(false),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
export const ProjectsSettledOpen: StoryObj<typeof AgentTabs> = {
  args: projectArgs(true),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** An ended session you are looking at (or that still has messages for
 *  you) stays in its project: a folded Settled never hides it. */
export const EndedButViewed: StoryObj<typeof AgentTabs> = {
  args: { ...projectArgs(false), viewed: 'i152', queued: { bucky: 2, release: 1, cta: 1 } },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** "✓ Settle", shown on hover or keyboard focus beside the key cap: plain
 *  text in the wait time's own font and slot (title line, right edge), which
 *  it replaces while shown - the tooltip keeps the wait time; nothing else
 *  moves. Muted at rest, cyan when pointed at. Here the mic row is focused.
 *  Settled rows offer "Restore" the same way. */
export const SettleOnFocus: StoryObj<typeof AgentTabs> = {
  args: projectArgs(true),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('button.tab.mic .settle')?.focus();
  },
};
/** Settled, opened: the ended sessions and the conversations you settled
 *  (one snoozed, with its wake time on the second line), newest first. The heading counts all of them; the daemon sends only the
 *  newest settled ones, so the rest is "+N older". Every Settled row offers
 *  Restore (focused here), which puts it back in its project - an ended one
 *  as an ended row. A settled row opens only once restored. */
export const SettledWithRestore: StoryObj<typeof AgentTabs> = {
  args: { ...projectArgs(true), settledAgents: SETTLED_AGENTS },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('button.tab.hidden .settle')?.focus();
  },
};
/** The clock beside Settle opens the snooze menu: 1, 3 or 6 hours,
 *  Tomorrow or Next week (09:00 local), each with the time it comes back.
 *  Snoozing settles the conversation; it returns to its project at that
 *  time, or earlier when its session speaks. In Settled, a snoozed row says
 *  "snoozed until ..." (see SettledWithRestore). */
export const SnoozeMenuOpen: StoryObj<typeof AgentTabs> = {
  args: projectArgs(false),
  decorators: [() => ({ template: '<div style="width:268px;padding-bottom:180px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('button.tab.mic .snooze')?.click();
  },
};
/** A folded project (click its heading; drag still moves it): the heading
 *  sums up what waits there - the amber count beside the name, and in the
 *  meta column how long its longest-waiting row has waited, in the rows'
 *  own format. Here "bucky" is folded with 2 messages waiting for 4m. */
export const FoldedProjectWaiting: StoryObj<typeof AgentTabs> = {
  args: { ...projectArgs(false), foldedProjects: ['bucky'] },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** A folded project never hides what needs you: the mic row (dashboard)
 *  and the speaking row (QA docs) stay under the folded "noisy-studio"
 *  heading, as would the row you are looking at; the rest fold away, and
 *  the heading still sums up the waiting messages (1, for 2h). */
export const FoldedProjectKeepsMic: StoryObj<typeof AgentTabs> = {
  args: { ...projectArgs(false), foldedProjects: ['noisy-studio'] },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** The viewed row (highlighted surface) is not the mic row (green bar in
 *  the inset): the two marks never fight, and either can sit on any row. */
export const ViewedIsNotMic: StoryObj<typeof AgentTabs> = {
  args: { ...projectArgs(false), viewed: 'bugs' },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** The narrowest column (220px) and a wide one (560px): titles and branches
 *  truncate, counts and wait times keep the right edge. */
export const Narrow: StoryObj<typeof AgentTabs> = {
  args: projectArgs(false),
  decorators: [() => ({ template: '<div style="width:220px"><story /></div>' })],
};
export const Wide: StoryObj<typeof AgentTabs> = {
  args: projectArgs(false),
  decorators: [() => ({ template: '<div style="width:560px"><story /></div>' })],
};
