<script setup lang="ts">
import { groupAgents, moveProject, moveWithinProject, settledRows, type ProjectGroup } from "./agentOrder";
import type { SettledAgent, SettledAgents } from "../types";
import { computed, onBeforeUnmount, ref } from "vue";
import { conversationLabel } from "../conversationLabel";
import { chordLabel, projectHue, waitLabel } from "./tabDetails";
import { useKeyCapture } from "../composables/useKeyCapture";

export interface AgentMeta {
  label: string;
  online: boolean;
  activated_at: number;
  offline_since: number | null;
  manual_pos?: number | null;
  shortcut?: number | null; // the Tab N hotkey that reaches it (daemon-numbered)
  talk_key?: string | null; // its own global talk key, which replaces the Tab N one
  project?: string | null; // git repository (or folder) the session runs in
  branch?: string | null;
  waiting_since?: number | null; // epoch s; set while it is your move
  kept?: boolean; // ended, restored from Settled: stays in its project
}

const props = withDefaults(
  defineProps<{
    agents: Record<string, string>; // id -> human label (legacy daemons)
    meta?: Record<string, AgentMeta> | null; // id -> tab metadata (#11)
    active: string | null; // the agent receiving transcripts
    viewed: string | null; // the tab being displayed
    speaking: string[]; // agents currently playing audio
    thinking?: string[]; // agents currently working (live activity line)
    activity?: Record<string, string>; // live activity text per agent
    queued?: Record<string, number>; // waiting messages per agent
    muted?: string[]; // per-conversation mute (future daemon feature)
    settledOpen?: boolean; // initial Settled state; omit for the remembered one
    now?: number; // epoch s; omit to use the row clock (stories/tests pin it)
    tabKeys?: Record<number, string>; // Tab N hotkey -> its chord ("F16"), shown on the row
    // Give a conversation its own talk key ("" clears); resolves to the
    // daemon's refusal text, or null when it took the key.
    setTalkKey?: (name: string, chord: string) => Promise<string | null>;
    // Settled (hidden) conversations, newest first, capped, with the total.
    settledAgents?: SettledAgents | null;
  }>(),
  { thinking: () => [], activity: () => ({}), queued: () => ({}), muted: () => [], meta: null, settledOpen: undefined, settledAgents: null },
);

// Geometry knobs. Every heading and row sits on ONE grid - lead | text |
// meta - so badge, status glyph and chevron share a column, every text
// starts at the same x, and every count and wait time ends on the same
// right edge, at any column width. One row height for every state, so
// nothing shifts. Vertical rhythm in steps of 4px.
const GRID = {
  padX: 8, // row inset; the mic edge lives inside it
  lead: 16, // badge / status glyph / chevron column
  gap: 8, // between columns
  meta: 32, // right column: wait time on rows, counts on headings
  row: 48, // two-line row, every state
  head: 24, // project and Settled headings
  groupGap: 16, // space above a heading: a heading sits closer to its rows than to the group above
};
const gridVars = Object.fromEntries(Object.entries(GRID).map(([key, px]) => [`--${key}`, `${px}px`]));
// Waiting times are shown in whole minutes; a coarse clock is enough.
const CLOCK_TICK_MS = 30_000;
const clock = ref(Date.now() / 1000);
const clockTimer = setInterval(() => { clock.value = Date.now() / 1000; }, CLOCK_TICK_MS);
onBeforeUnmount(() => clearInterval(clockTimer));
// The row shows the real key (F16), falling back to "Tab N" when unbound.
const keyCap = (shortcut: number | null | undefined) => (shortcut ? chordLabel(props.tabKeys?.[shortcut]) || `Tab ${shortcut}` : "");
// A row's key: its own talk key, else its positional Tab N key.
const rowKey = (tab: Tab) =>
  chordLabel(tab.hidden ? tab.hidden.talk_key : props.meta?.[tab.name]?.talk_key) || keyCap(props.meta?.[tab.name]?.shortcut);
const waited = (name: string) => waitLabel(props.meta?.[name]?.waiting_since, props.now ?? clock.value);

const emit = defineEmits<{
  select: [name: string];
  settle: [name: string]; // hide it from the list (the daemon's /dismiss-agent)
  restore: [name: string]; // bring a Settled one back to its project (/restore-agent)
  reorder: [names: string[]];
}>();

// Settled folds, closed by default; the reader's choice is remembered per
// browser.
const SETTLED_OPEN_KEY = "noisy.tabs.settledOpen";
function storedSettledOpen(): boolean {
  try { return localStorage.getItem(SETTLED_OPEN_KEY) === "1"; } catch { return false; }
}
const settledShown = ref(props.settledOpen ?? storedSettledOpen());
function toggleSettled() {
  settledShown.value = !settledShown.value;
  try { localStorage.setItem(SETTLED_OPEN_KEY, settledShown.value ? "1" : "0"); } catch { /* session only */ }
}

// `hidden`: a settled conversation, no longer in the agents table - the
// daemon's settled_agents entry carries what its row shows.
interface Tab { name: string; label: string; online: boolean; settled: boolean; hidden: SettledAgent | null }
type Item =
  | { kind: "tab"; key: string; tab: Tab }
  | { kind: "project"; key: string; project: string | null; waiting: number }
  | { kind: "settled"; key: string; count: number }
  | { kind: "older"; key: string; count: number };

// Grouping and ordering live in agentOrder.ts, next to the order the
// widget uses, so the two rules cannot drift apart unnoticed.
const groups = computed(() =>
  groupAgents(Object.keys(props.agents), props.meta ?? {}, {
    speaking: props.speaking, queued: props.queued,
    keepInSight: [props.viewed, props.active],
  }),
);
const tabOf = (name: string, settled: boolean, hidden: SettledAgent | null = null): Tab => ({
  name,
  label: conversationLabel(hidden?.label ?? props.meta?.[name]?.label ?? props.agents[name], name),
  online: hidden ? !hidden.ended : props.meta?.[name]?.online ?? true,
  settled,
  hidden,
});
// Settled: the ended sessions and the settled conversations, newest first.
const settled = computed(() => settledRows(groups.value.settled, props.meta ?? {}, props.settledAgents));
// What waits for you in a project: its queued messages, in amber.
const waitingIn = (group: ProjectGroup) => group.names.reduce((sum, name) => sum + (props.queued[name] ?? 0), 0);
// A daemon that knows no projects (legacy, or no repository at all) gets the
// plain list: a lone "No project" heading would say nothing.
const showProjectHeads = computed(() => groups.value.projects.some((group) => group.project !== null));
const tabCount = computed(() => Object.keys(props.agents).length + settled.value.total);
const items = computed<Item[]>(() => {
  const { rows: settledList, total, older } = settled.value;
  return [
    ...groups.value.projects.flatMap((group): Item[] => [
      ...(showProjectHeads.value
        ? [{ kind: "project", key: `p-${group.project ?? ""}`, project: group.project, waiting: waitingIn(group) } as Item]
        : []),
      ...group.names.map((name): Item => ({ kind: "tab", key: name, tab: tabOf(name, false) })),
    ]),
    ...(total ? [{ kind: "settled", key: "h-settled", count: total } as Item] : []),
    ...(settledShown.value
      ? [
          ...settledList.map((row): Item => ({ kind: "tab", key: row.name, tab: tabOf(row.name, true, row.hidden) })),
          ...(older ? [{ kind: "older", key: "settled-older", count: older } as Item] : []),
        ]
      : []),
  ];
});
// Settled rows sit outside their project, so their second line names it.
const whereLine = (tab: Tab) => {
  const where = tab.hidden ?? props.meta?.[tab.name];
  return (tab.settled ? [where?.project, where?.branch] : [where?.branch]).filter(Boolean).join(" · ");
};
// A settled (hidden) conversation is not in the list the daemon serves, so
// it cannot be opened: Restore brings it back first.
function onRowClick(tab: Tab) {
  if (!tab.hidden) emit("select", tab.name);
}
// The row's one hover action: Settle a listed row, Restore a Settled one.
function rowAction(tab: Tab) {
  if (tab.settled) emit("restore", tab.name);
  else emit("settle", tab.name);
}
const statusText = ({ name, online, hidden }: Tab) =>
  !online ? "Ended" : hidden ? "Settled" : props.muted.includes(name) ? "Muted" : props.speaking.includes(name) ? "Speaking"
    : props.thinking.includes(name) ? "Working" : "Ready";
// The hover actions cover the wait time, so the tooltip carries it.
const rowTitle = (tab: Tab) => [
  tab.label, tab.name === props.active ? "Receiving your speech" : "", statusText(tab),
  props.activity[tab.name] ?? "", waited(tab.name) ? `Waiting for you ${waited(tab.name)}` : "",
].filter(Boolean).join(" · ");

// Drag & drop within a project only: a project is where the session runs,
// not a choice. Settled rows do not drag (their order is when they ended).
const dragging = ref<string | null>(null);
// A project heading drags its whole project (onto another heading).
const draggingProject = ref<{ project: string | null } | null>(null);
function onProjectDrop(target: string | null) {
  const from = draggingProject.value;
  draggingProject.value = null;
  if (!from) return;
  const order = moveProject(Object.keys(props.agents), props.meta ?? {}, from.project, target);
  if (order) emit("reorder", order);
}
function onDrop(target: Tab) {
  const name = dragging.value;
  dragging.value = null;
  if (!name || target.settled) return;
  const order = moveWithinProject(Object.keys(props.agents), props.meta ?? {}, name, target.name);
  if (order) emit("reorder", order);
}

// Right-click a row: give it its own global talk key, captured the same
// way Settings captures hotkeys (press the chord; Delete clears).
const keyMenu = ref<{ name: string; x: number; y: number; problem: string | null } | null>(null);
function openKeyMenu(name: string, event: MouseEvent) {
  const nav = (event.currentTarget as HTMLElement).closest("nav")!.getBoundingClientRect();
  keyMenu.value = { name, x: event.clientX - nav.left, y: event.clientY - nav.top, problem: null };
}
function closeKeyMenu() {
  capture.stop();
  keyMenu.value = null;
}
async function applyTalkKey(name: string, chord: string) {
  const problem = (await props.setTalkKey?.(name, chord)) ?? null;
  if (problem && keyMenu.value?.name === name) keyMenu.value = { ...keyMenu.value, problem };
  else if (!problem) keyMenu.value = null;
}
const capture = useKeyCapture((name, result) => {
  if (result.kind === "chord") void applyTalkKey(name, result.chord);
  else if (result.kind === "clear") void applyTalkKey(name, "");
});
</script>

<template>
  <nav v-if="tabCount" class="tabs" aria-label="Conversations" :style="gridVars">
    <template v-for="item in items" :key="item.key">
      <!-- A project heading: badge, name, and how many messages wait for
           you there (amber, in the meta column). Drag it onto another
           heading to move the whole project. -->
      <div
        v-if="item.kind === 'project'" class="head project-head" :class="{ unknown: !item.project, dragging: draggingProject?.project === item.project }"
        draggable="true" title="Drag onto another project to move it"
        @dragstart="draggingProject = { project: item.project }" @dragend="draggingProject = null"
        @dragover.prevent @drop.prevent="onProjectDrop(item.project)"
      >
        <span class="lead"><span class="badge" :style="item.project ? { '--hue': projectHue(item.project) } : undefined" aria-hidden="true">{{ item.project ? item.project.charAt(0).toUpperCase() : '?' }}</span></span>
        <span class="project-name clip">{{ item.project ?? 'No project' }}</span>
        <span class="meta project-waiting" :title="item.waiting ? `${item.waiting} waiting for you` : undefined">{{ item.waiting || '' }}</span>
      </div>
      <button
        v-else-if="item.kind === 'settled'"
        type="button" class="head section toggle" :aria-expanded="settledShown" @click="toggleSettled"
      ><span class="lead chev" :class="{ open: settledShown }" aria-hidden="true">▸</span> <span class="project-name">Settled</span> <b class="meta">{{ item.count }}</b></button>
      <!-- The daemon sends the newest settled conversations only. -->
      <p v-else-if="item.kind === 'older'" class="older">+{{ item.count }} older</p>
      <button
        v-else
        class="tab"
        :draggable="!item.tab.settled"
        :aria-pressed="item.tab.name === viewed"
        :title="rowTitle(item.tab)"
        :class="{
          viewing: item.tab.name === viewed,
          mic: item.tab.name === active,
          speaking: speaking.includes(item.tab.name),
          offline: !item.tab.online,
          dragging: item.tab.name === dragging,
          single: !whereLine(item.tab),
          hidden: !!item.tab.hidden,
        }"
        @click="onRowClick(item.tab)"
        @dragstart="dragging = item.tab.name"
        @dragend="dragging = null"
        @dragover.prevent
        @drop.prevent="onDrop(item.tab)"
        @contextmenu.prevent="!item.tab.settled && openKeyMenu(item.tab.name, $event)"
      >
        <!-- ONE status glyph, fixed slot, priority ladder (option B):
             MUTE (with or without a count) > SPEAKING (green equalizer) >
             WAIT count (amber - messages waiting to be heard beat the mere
             "working" pulse) > WORKING (violet). Idle: an empty slot (a grey
             dot read like a bullet point). The mic needs no glyph: it is
             the green edge. -->
        <span class="lead statusslot">
          <template v-if="muted.includes(item.tab.name)">
            <span v-if="(queued[item.tab.name] ?? 0) > 0" class="mutecount" :title="`Muted — ${queued[item.tab.name]} waiting`">{{ queued[item.tab.name] }}</span>
            <svg v-else class="mutespk" viewBox="0 0 14 14" aria-label="muted">
              <path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" />
              <line x1="10" y1="5" x2="13" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
              <line x1="13" y1="5" x2="10" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
            </svg>
          </template>
          <span v-else-if="speaking.includes(item.tab.name)" class="eq" aria-label="speaking"><i /><i /><i /></span>
          <span v-else-if="(queued[item.tab.name] ?? 0) > 0" class="waitcount" :title="`${queued[item.tab.name]} waiting`">{{ queued[item.tab.name] }}</span>
          <span v-else-if="thinking.includes(item.tab.name)" class="dot think" title="Working" />
        </span>
        <span class="tab-label">{{ item.tab.label }}</span>
        <span class="meta waited">{{ waited(item.tab.name) }}</span>
        <span v-if="whereLine(item.tab)" class="where">
          <svg class="branch-icon" viewBox="0 0 16 16" aria-hidden="true"><circle cx="4.5" cy="3.5" r="1.6" /><circle cx="4.5" cy="12.5" r="1.6" /><circle cx="11.5" cy="5.5" r="1.6" /><path d="M4.5 5.1v5.8M11.5 7.1c0 2.4-2.2 3-5.4 4" /></svg>
          <span class="clip">{{ whereLine(item.tab) }}</span>
        </span>
        <!-- Hover/focus actions, one cluster on the title line, ending on
             the wait time's right edge: the Tab hotkey as a key cap with the
             real chord (the user knows their keys, so it stays hidden at
             rest) and "✓ Settle" - plain text in the wait time's own font,
             which it replaces while hovered. Settle hides
             the conversation, it does not end the session; it comes back
             when its session speaks. Settling the mic's row hands the mic to
             the next one (the daemon decides and says so). On a Settled row
             the same action is Restore: back to its project, an ended one as
             an ended row (there is no Remove: a removed row would only come
             back as a settled one). -->
        <span class="actions">
          <kbd class="shortcut" :class="{ none: !rowKey(item.tab) }" :title="rowKey(item.tab) ? `Hotkey ${rowKey(item.tab)} talks to this conversation · right-click to change` : 'Right-click to give it a talk key'">{{ rowKey(item.tab) }}</kbd>
          <span
            class="settle"
            role="button" tabindex="0" @keydown.enter.stop.prevent="rowAction(item.tab)" @keydown.space.stop.prevent="rowAction(item.tab)"
            :title="item.tab.settled ? 'Restore: back to its project' : 'Settle: hide it until its session speaks again'"
            @click.stop="rowAction(item.tab)"
            ><svg class="action-icon" viewBox="0 0 12 12" aria-hidden="true"><path v-if="item.tab.settled" d="M2.5 4.5h5a2.5 2.5 0 0 1 0 5H5M2.5 4.5 4.5 2.5M2.5 4.5l2 2" /><path v-else d="M2.5 6.2 5 8.6l4.5-5" /></svg>{{ item.tab.settled ? 'Restore' : 'Settle' }}</span>
        </span>
      </button>
    </template>
    <div v-if="keyMenu" class="keymenu-scrim" @click="closeKeyMenu" @contextmenu.prevent="closeKeyMenu" />
    <div v-if="keyMenu" class="keymenu" role="menu" aria-label="Talk key" :style="{ left: keyMenu.x + 'px', top: keyMenu.y + 'px' }" >
      <p class="keymenu-title">Talk key</p>
      <button type="button" role="menuitem" class="keymenu-item" @click="capture.start(keyMenu.name)">
        <kbd class="shortcut">{{ capture.capturing.value === keyMenu.name ? "…" : rowKey(tabOf(keyMenu.name, false)) || "none" }}</kbd>
        <span>{{ capture.capturing.value === keyMenu.name ? "Press a key · Delete clears" : "Set a key…" }}</span>
      </button>
      <button v-if="meta?.[keyMenu.name]?.talk_key" type="button" role="menuitem" class="keymenu-item" @click="applyTalkKey(keyMenu.name, '')"><span>Remove its own key</span></button>
      <p v-if="keyMenu.problem" class="keymenu-problem" role="alert">{{ keyMenu.problem }}</p>
    </div>
  </nav>
</template>

<style scoped>
.tabs {
  position:relative; display:flex; flex-direction:column; gap:2px; padding:2px;
  /* Row surfaces are opaque so the hover actions can fade over the text. */
  --row-hover: color-mix(in srgb, var(--surface-hover) 55%, var(--bg0));
  --row-selected: var(--surface-hover);
  --faint: color-mix(in srgb, var(--muted) 72%, var(--bg0));
}

/* The shared grid: lead | text | meta. */
.head, .tab { display:grid; grid-template-columns:var(--lead) minmax(0,1fr) var(--meta); column-gap:var(--gap); padding:0 var(--padX); box-sizing:border-box; width:100%; min-width:0; }
.lead { display:flex; align-items:center; justify-content:center; width:var(--lead); }
.meta { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }

/* Headings: quieter than the rows they hold. */
.head { height:var(--head); align-items:center; margin-top:var(--groupGap); font:600 11px/1 var(--sans); letter-spacing:.02em; color:var(--muted); }
.head:first-child { margin-top:2px; }
.badge { width:14px; height:14px; border-radius:4px; font:700 9px/14px var(--sans); letter-spacing:0; text-align:center; color:#fff; background:hsl(var(--hue, 0) 45% 42%); }
.unknown .badge { background:var(--surface-hover); color:var(--muted); }
.project-waiting { font-weight:600; color:var(--amber); }
.section { border:0; border-top:1px solid var(--line); border-radius:0; background:none; text-align:left; cursor:pointer; height:calc(var(--head) + 4px); padding-top:4px; }
.section b { font-weight:600; color:var(--faint); }
.section:hover { color:var(--ink); }
.chev { font-size:10px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }

/* Rows: two lines, title over where-it-runs. */
.tab { position:relative; flex:none; height:var(--row); grid-template-rows:18px 15px; row-gap:3px; align-content:center; font:13px/18px var(--sans); text-align:left; color:var(--ink); border:0; border-radius:6px; background:transparent; }
.tab.single { grid-template-rows:18px; }
.tab:hover, .tab:focus-within { background:var(--row-hover); }
.tab.viewing { background:var(--row-selected); }
.tab:focus-visible { outline-offset:-2px; }
/* The mic recipient: a short green bar in the row's inset, clear of the
   rounded corners, independent of the selection surface. */
.tab.mic::before { content:""; position:absolute; left:2px; top:12px; bottom:12px; width:3px; border-radius:2px; background:var(--green); }
.tab.offline .tab-label, .tab.offline .where { color:var(--faint); }
.tab.dragging { opacity:.5; }
.tab.hidden { cursor:default; }
/* "+N older": a quiet line on the text column, under the last Settled row. */
.older { margin:2px 0 0; padding:0 var(--padX) 0 calc(var(--padX) + var(--lead) + var(--gap)); font:11px/20px var(--sans); color:var(--faint); }
.statusslot { grid-row:1; grid-column:1; height:18px; }
.tab-label { grid-row:1; grid-column:2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.waited { grid-row:1; grid-column:3; font-size:11px; color:var(--amber); }
.where { grid-row:2; grid-column:2 / 4; display:flex; align-items:center; gap:5px; min-width:0; font:11px/15px var(--mono, monospace); color:var(--muted); }
.branch-icon { flex:none; width:11px; height:11px; fill:none; stroke:currentColor; stroke-width:1.4; stroke-linecap:round; }

/* Status glyphs, one slot. */
.dot { width:6px; height:6px; border-radius:50%; }
.think { background:var(--violet); }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:13px; animation-delay:.2s; }
.waitcount, .mutecount { font:600 11px var(--sans); font-variant-numeric:tabular-nums; }
.waitcount { color:var(--amber); }
.mutecount, .mutespk { color:var(--red); }
.mutespk { width:13px; height:13px; }

/* Hover / focus actions: ONE cluster on the title line, laid over its end
   on the z-axis and ending on the wait time's right edge. The wait time
   hides while it shows (the tooltip keeps it). Settle always sits at the
   same x; the key cap reserves its width. */
.actions { grid-row:1; grid-column:2 / 4; justify-self:end; z-index:1; height:18px; display:flex; align-items:center; gap:8px; padding-left:20px; background:linear-gradient(to right, transparent, var(--row-hover) 18px); opacity:0; pointer-events:none; }
.tab.viewing .actions { background:linear-gradient(to right, transparent, var(--row-selected) 18px); }
.tab:hover .actions, .tab:focus-within .actions { opacity:1; pointer-events:auto; }
.tab:hover .waited, .tab:focus-within .waited { visibility:hidden; }
.shortcut { flex:none; min-width:34px; height:18px; padding:0 5px; box-sizing:border-box; font:10px/14px var(--mono, monospace); color:var(--muted); text-align:center; background:var(--panel-solid); border:1px solid var(--line-strong); border-bottom-width:2px; border-radius:4px; }
.shortcut.none { visibility:hidden; }
/* Settle / Restore: text, not a button box - the wait time's font and
   size, quieter at rest, cyan (the chrome colour) when pointed at. */
.settle { display:inline-flex; align-items:center; gap:3px; font-size:11px; line-height:18px; color:var(--muted); white-space:nowrap; cursor:pointer; }
.settle:hover, .settle:focus-visible { color:var(--cyan); }
.settle:focus-visible { outline:1px solid var(--cyan); outline-offset:1px; border-radius:2px; }
.action-icon { width:11px; height:11px; fill:none; stroke:currentColor; stroke-width:1.5; stroke-linecap:round; stroke-linejoin:round; }

/* Right-click: assign a Tab key. */
.project-head { cursor:grab; }
.project-head.dragging { opacity:.5; }
.keymenu-scrim { position:fixed; inset:0; z-index:9; }
.keymenu { position:absolute; z-index:10; min-width:150px; padding:6px; display:flex; flex-direction:column; gap:2px; background:var(--panel-solid); border:1px solid var(--line-strong); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.35); }
.keymenu-title { margin:2px 6px 4px; font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
.keymenu-item { display:flex; align-items:center; gap:8px; padding:4px 6px; border:0; border-radius:6px; background:none; color:var(--ink); font:11px var(--sans); text-align:left; }
.keymenu-item:hover:not(:disabled), .keymenu-item:focus-visible { background:var(--surface-hover); }
.keymenu-item:disabled { opacity:.45; }
.keymenu-item span { color:var(--muted); }
.keymenu-problem { margin:4px 6px 2px; max-width:220px; font-size:10px; line-height:1.35; color:var(--amber); }
@keyframes eq { 50% { transform:scaleY(.5); } }
</style>
