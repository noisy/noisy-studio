import type { Meta, StoryObj } from "@storybook/vue3";
import { h, ref } from "vue";
import AgentTabs from "./AgentTabs.vue";
import HudPanel from "./HudPanel.vue";
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
 *  recipient: green edge) or a background one. Columns: the single
 *  status glyph, option-B priority ladder: MUTE (with or without a waiting
 *  count) > SPEAKING (green equalizer) > WAIT count (amber) > WORKING
 *  (violet) > idle dot. WORK+3 shows the count outranking work, SPEAK+3 the
 *  count hidden while it speaks; ENDED shows the greyed row of a session
 *  that ended (it lives in Settled, opened here; hover offers Remove). Every
 *  live row offers Settle on hover/focus, the mic's too - settling the
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
 *  violet glyph on a row, not a place. Ended sessions fold into Settled. */
const PROJECT_AGENTS: Record<string, string> = {
  dash: 'noisy-studio · dashboard', bucky: 'Bucky', qa: 'QA docs', diet: 'fitatu',
  bugs: 'Bug fixing', release: 'release 3.0.0', mobile: 'mobile TestFlight',
  cta: 'website CTA', grok: 'grok harness', deck: 'presentation', i152: 'issue 152 live', i172: 'issue 172 review',
};
const ENDED = ['cta', 'grok', 'deck', 'i152', 'i172'];
// Tab N hotkeys come from the daemon's stable order, not the grouping.
const SHORTCUTS: Record<string, number> = { dash: 1, bugs: 2, qa: 3, bucky: 4 };
// Project and branch come from the session's directory (no setup); legacy
// and Codex sessions may have neither, so 'diet' lands in "No project".
const NOW = 1_800_000_000;
const WORKSPACE: Record<string, { project: string; branch: string | null }> = {
  dash: { project: 'noisy-studio', branch: 'main' }, bucky: { project: 'bucky', branch: 'feat/voice-tiles' },
  qa: { project: 'noisy-studio', branch: 'docs/qa' }, bugs: { project: 'noisy-studio', branch: 'fix/hold-release' },
  release: { project: 'noisy-studio', branch: 'release/3.0.0' }, mobile: { project: 'noisy-mobile', branch: 'main' },
  cta: { project: 'website', branch: 'main' }, grok: { project: 'noisy-studio', branch: 'grok-harness' },
  deck: { project: 'Downloads', branch: null }, i152: { project: 'noisy-studio', branch: 'issue-152' }, i172: { project: 'noisy-studio', branch: 'issue-172' },
};
const WAITING_SINCE: Record<string, number> = { dash: NOW - 30, bucky: NOW - 4 * 60, qa: NOW - 2 * 3600 };
const projectArgs = (settledOpen: boolean) => ({
  agents: PROJECT_AGENTS,
  meta: Object.fromEntries(Object.entries(PROJECT_AGENTS).map(([id, label], i) => [id, {
    label, online: !ENDED.includes(id), activated_at: i, offline_since: ENDED.includes(id) ? 100 - i : null,
    shortcut: SHORTCUTS[id] ?? null,
    project: WORKSPACE[id]?.project ?? null, branch: WORKSPACE[id]?.branch ?? null,
    waiting_since: WAITING_SINCE[id] ?? null,
  }])),
  active: 'dash', viewed: 'dash', speaking: ['qa'], queued: { bucky: 2, release: 1 },
  thinking: ['bugs', 'release', 'mobile'],
  activity: { bugs: 'Bash · pytest', release: 'Thinking…', mobile: 'Edit · App.swift' },
  settledOpen,
  now: NOW,
  // The rows show the real hotkey; unbound ones fall back to "Tab N".
  tabKeys: { 1: 'F16', 2: 'F17', 3: 'ctrl+alt+3' },
});
/** Hover a row to see its talk key; right-click it to give it another one
 *  (F16-F19 here). Idle rows have an empty status slot. */
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
/** Settle, shown on hover or keyboard focus over the end of the branch
 *  line: the title, wait time and hotkey stay where they are. Here
 *  the mic row is focused. Settled rows offer Remove instead (no Restore:
 *  the daemon cannot un-hide a conversation on request yet). */
export const SettleOnFocus: StoryObj<typeof AgentTabs> = {
  args: projectArgs(true),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('button.tab.mic .settle')?.focus();
  },
};
