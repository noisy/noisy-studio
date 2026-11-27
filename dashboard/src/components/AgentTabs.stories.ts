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
 *  Rows: is this the selected row (highlighted) or a background one. Columns: the single status glyph,
 *  option-B priority ladder: MUTE (with or without a waiting count) >
 *  SPEAKING (green equalizer) > WORKING (violet pulse) > WAIT count
 *  (amber) > idle dot. WORK+3 / SPEAK+3 prove the count stays hidden
 *  while the agent is busy; ENDED shows the greyed tab of a session that
 *  ended (it lives in the Settled section, opened here). Every row carries
 *  a close ✕ (shown on hover/focus), the SELECTED one too - closing the
 *  mic's tab hands the mic to the next conversation. Liveness comes from
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

/** Slow motion makes conservation of the row's width easy to inspect. */
export const SlowMicrophoneTransfer: StoryObj<typeof AgentTabs> = {
  ...ListBesideWindow,
  decorators: [() => ({ template: '<div style="--mic-transition-duration-ms:1800"><story /></div>' })],
};

/** The sections, T3-style: your turn on top (no heading), Working below
 *  (after 10 s of sustained work, with what the agent is doing), Settled
 *  (ended sessions) collapsed at the bottom. */
const SECTION_AGENTS: Record<string, string> = {
  dash: 'noisy-studio · dashboard', bucky: 'Bucky', qa: 'QA docs', diet: 'fitatu',
  bugs: 'Bug fixing', release: 'release 3.0.0', mobile: 'mobile TestFlight',
  cta: 'website CTA', grok: 'grok harness', deck: 'presentation', i152: 'issue 152 live', i172: 'issue 172 review',
};
const ENDED = ['cta', 'grok', 'deck', 'i152', 'i172'];
const sectionsArgs = (settledOpen: boolean) => ({
  agents: SECTION_AGENTS,
  meta: Object.fromEntries(Object.entries(SECTION_AGENTS).map(([id, label], i) => [id, {
    label, online: !ENDED.includes(id), activated_at: i, offline_since: ENDED.includes(id) ? 100 - i : null,
  }])),
  active: 'dash', viewed: 'dash', speaking: ['qa'], queued: { bucky: 2 },
  thinking: ['bugs', 'release', 'mobile'], working: ['bugs', 'release', 'mobile'],
  activity: { bugs: 'Bash · pytest', release: 'Thinking…', mobile: 'Edit · App.swift' },
  settledOpen,
});
export const Sections: StoryObj<typeof AgentTabs> = {
  args: sectionsArgs(false),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
export const SectionsSettledOpen: StoryObj<typeof AgentTabs> = {
  args: sectionsArgs(true),
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
/** Working folded: only its heading stays (plus the viewed/mic row, if it
 *  is working). */
export const SectionsWorkingFolded: StoryObj<typeof AgentTabs> = {
  args: { ...sectionsArgs(false), workingOpen: false },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
};
