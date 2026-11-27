<script setup lang="ts">
// Variant B, "Sections": the current structure tidied - small-caps section
// labels with a hairline, and everything hover adds lives on line 2, so the
// title line never changes.
import { assignShortcut, groupAgents, moveWithinProject, type ProjectGroup } from "../../components/agentOrder";
import { computed, onBeforeUnmount, ref } from "vue";
import { conversationLabel } from "../../conversationLabel";
import { chordLabel, projectHue, waitLabel } from "../../components/tabDetails";
import type { AgentMeta } from "../../components/AgentTabs.vue";

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
  }>(),
  { thinking: () => [], activity: () => ({}), queued: () => ({}), muted: () => [], meta: null, settledOpen: undefined },
);

// Geometry: every heading and row sits on one grid, so badge, status glyph,
// chevron and every text start share their x, and every count and wait time
// shares the right edge. Vertical rhythm is in steps of 4px.
const GRID = {
  padX: 8, // row inset; the mic edge lives inside it
  lead: 16, // badge / status glyph / chevron column
  gap: 8, // between columns
  meta: 36, // right column: wait time (line 1), key cap (line 2) on rows
  row: 44, // two-line row, every state
  head: 28, // project and Settled headings
  groupGap: 8, // space above a project heading
};
const gridVars = Object.fromEntries(Object.entries(GRID).map(([key, px]) => [`--${key}`, `${px}px`]));
// Waiting times are shown in whole minutes; a coarse clock is enough.
const CLOCK_TICK_MS = 30_000;
const clock = ref(Date.now() / 1000);
const clockTimer = setInterval(() => { clock.value = Date.now() / 1000; }, CLOCK_TICK_MS);
onBeforeUnmount(() => clearInterval(clockTimer));
// The row shows the real key (F16), falling back to "Tab N" when unbound.
const keyCap = (shortcut: number | null | undefined) => (shortcut ? chordLabel(props.tabKeys?.[shortcut]) || `Tab ${shortcut}` : "");
const waited = (name: string) => waitLabel(props.meta?.[name]?.waiting_since, props.now ?? clock.value);

const emit = defineEmits<{
  select: [name: string];
  settle: [name: string]; // hide it from the list (the daemon's /dismiss-agent)
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

interface Tab { name: string; label: string; online: boolean; settled: boolean }
type Item =
  | { kind: "tab"; key: string; tab: Tab }
  | { kind: "project"; key: string; project: string | null; waiting: number }
  | { kind: "settled"; key: string; count: number };

const groups = computed(() =>
  groupAgents(Object.keys(props.agents), props.meta ?? {}, {
    speaking: props.speaking, queued: props.queued,
    keepInSight: [props.viewed, props.active],
  }),
);
const tabOf = (name: string, settled: boolean): Tab => ({
  name,
  label: conversationLabel(props.meta?.[name]?.label ?? props.agents[name], name),
  online: props.meta?.[name]?.online ?? true,
  settled,
});
const waitingIn = (group: ProjectGroup) => group.names.reduce((sum, name) => sum + (props.queued[name] ?? 0), 0);
const showProjectHeads = computed(() => groups.value.projects.some((group) => group.project !== null));
const tabCount = computed(() => Object.keys(props.agents).length);
const items = computed<Item[]>(() => {
  const { projects, settled } = groups.value;
  const rows = (names: string[], isSettled: boolean): Item[] =>
    names.map((name) => ({ kind: "tab", key: name, tab: tabOf(name, isSettled) }));
  return [
    ...projects.flatMap((group): Item[] => [
      ...(showProjectHeads.value
        ? [{ kind: "project", key: `p-${group.project ?? ""}`, project: group.project, waiting: waitingIn(group) } as Item]
        : []),
      ...rows(group.names, false),
    ]),
    ...(settled.length ? [{ kind: "settled", key: "h-settled", count: settled.length } as Item] : []),
    ...(settledShown.value ? rows(settled, true) : []),
  ];
});
const whereLine = (tab: Tab) => {
  const meta = props.meta?.[tab.name];
  return (tab.settled ? [meta?.project, meta?.branch] : [meta?.branch]).filter(Boolean).join(" · ");
};
const statusText = (name: string, online: boolean) =>
  !online ? "Ended" : props.muted.includes(name) ? "Muted" : props.speaking.includes(name) ? "Speaking"
    : props.thinking.includes(name) ? "Working" : "Ready";
const rowTitle = (tab: Tab) => [
  tab.label, tab.name === props.active ? "Receiving your speech" : "", statusText(tab.name, tab.online),
  props.activity[tab.name] ?? "",
].filter(Boolean).join(" · ");

const dragging = ref<string | null>(null);
function onDrop(target: Tab) {
  const name = dragging.value;
  dragging.value = null;
  if (!name || target.settled) return;
  const order = moveWithinProject(Object.keys(props.agents), props.meta ?? {}, name, target.name);
  if (order) emit("reorder", order);
}

const TAB_SLOTS = [1, 2, 3, 4];
const keyMenu = ref<{ name: string; x: number; y: number } | null>(null);
function openKeyMenu(name: string, event: MouseEvent) {
  const nav = (event.currentTarget as HTMLElement).closest("nav")!.getBoundingClientRect();
  keyMenu.value = { name, x: event.clientX - nav.left, y: event.clientY - nav.top };
}
function assignKey(slot: number) {
  const menu = keyMenu.value;
  keyMenu.value = null;
  if (!menu) return;
  const order = assignShortcut(Object.keys(props.agents), props.meta ?? {}, menu.name, slot);
  if (order) emit("reorder", order);
}
</script>

<template>
  <nav v-if="tabCount" class="tabs" aria-label="Conversations" :style="gridVars">
    <template v-for="item in items" :key="item.key">
      <div v-if="item.kind === 'project'" class="head project-head" :class="{ unknown: !item.project }">
        <span class="lead"><span class="badge" :style="item.project ? { '--hue': projectHue(item.project) } : undefined" aria-hidden="true">{{ item.project ? item.project.charAt(0).toUpperCase() : '?' }}</span></span>
        <span class="head-text"><span class="project-name clip">{{ item.project ?? 'No project' }}</span><i class="rule" /></span>
        <span class="meta project-waiting" :title="item.waiting ? `${item.waiting} waiting for you` : undefined">{{ item.waiting || '' }}</span>
      </div>
      <button
        v-else-if="item.kind === 'settled'"
        type="button" class="head section toggle" :aria-expanded="settledShown" @click="toggleSettled"
      ><span class="lead chev" :class="{ open: settledShown }" aria-hidden="true">▸</span> <span class="head-text"><span class="project-name">Settled</span><i class="rule" /></span> <b class="meta">{{ item.count }}</b></button>
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
        }"
        @click="$emit('select', item.tab.name)"
        @dragstart="dragging = item.tab.name"
        @dragend="dragging = null"
        @dragover.prevent
        @drop.prevent="onDrop(item.tab)"
        @contextmenu.prevent="!item.tab.settled && openKeyMenu(item.tab.name, $event)"
      >
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
        <kbd class="shortcut" :class="{ none: !meta?.[item.tab.name]?.shortcut }" :title="meta?.[item.tab.name]?.shortcut ? `Hotkey: Tab ${meta[item.tab.name].shortcut} talks to this conversation` : undefined">{{ keyCap(meta?.[item.tab.name]?.shortcut) }}</kbd>
        <span
            class="settle"
            role="button" tabindex="0" @keydown.enter.stop.prevent="$emit('settle', item.tab.name)" @keydown.space.stop.prevent="$emit('settle', item.tab.name)"
            :title="item.tab.settled ? 'Remove: drop this ended conversation from the list' : 'Settle: hide it until its session speaks again'"
            @click.stop="$emit('settle', item.tab.name)"
            >{{ item.tab.settled ? 'Remove' : 'Settle' }}</span>
      </button>
    </template>
    <div v-if="keyMenu" class="keymenu-scrim" @click="keyMenu = null" @contextmenu.prevent="keyMenu = null" />
    <div v-if="keyMenu" class="keymenu" role="menu" aria-label="Talk key" :style="{ left: keyMenu.x + 'px', top: keyMenu.y + 'px' }" @keydown.escape="keyMenu = null">
      <p class="keymenu-title">Talk to it with</p>
      <button
        v-for="slot in TAB_SLOTS" :key="slot" type="button" role="menuitem" class="keymenu-item"
        :aria-checked="meta?.[keyMenu.name]?.shortcut === slot"
        :disabled="!assignShortcut(Object.keys(agents), meta ?? {}, keyMenu.name, slot)"
        @click="assignKey(slot)"
      ><kbd class="shortcut">{{ keyCap(slot) }}</kbd><span v-if="meta?.[keyMenu.name]?.shortcut === slot">current</span></button>
    </div>
  </nav>
</template>

<style scoped>
.tabs {
  position:relative; display:flex; flex-direction:column; gap:1px; padding:2px;
  --row-hover: color-mix(in srgb, var(--surface-hover) 55%, var(--bg0));
  --row-selected: var(--surface-hover);
  --faint: color-mix(in srgb, var(--muted) 72%, var(--bg0));
}

.head, .tab { display:grid; grid-template-columns:var(--lead) minmax(0,1fr) var(--meta); column-gap:var(--gap); padding:0 var(--padX); box-sizing:border-box; width:100%; min-width:0; }
.lead { display:flex; align-items:center; justify-content:center; width:var(--lead); }
.meta { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }

/* Section labels: small caps, a hairline running to the count. */
.head { height:var(--head); align-items:center; margin-top:var(--groupGap); font:600 10px/1 var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.head:first-child { margin-top:2px; }
.head-text { display:flex; align-items:center; gap:8px; min-width:0; }
.rule { flex:1 0 12px; height:1px; background:var(--line); }
.badge { width:12px; height:12px; border-radius:3px; font:700 8px/12px var(--sans); letter-spacing:0; text-align:center; color:#fff; background:hsl(var(--hue, 0) 45% 42%); }
.unknown .badge { background:var(--surface-hover); color:var(--muted); }
.project-waiting { font-weight:600; color:var(--amber); letter-spacing:0; }
.section { border:0; background:none; text-align:left; cursor:pointer; }
.section b { font-weight:600; color:var(--faint); letter-spacing:0; }
.section:hover { color:var(--ink); }
.chev { font-size:10px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }

.tab { position:relative; flex:none; height:var(--row); grid-template-rows:17px 15px; row-gap:2px; align-content:center; font:13px/17px var(--sans); text-align:left; color:var(--ink); border:0; border-radius:4px; background:transparent; }
.tab.single { grid-template-rows:17px; }
.tab:hover, .tab:focus-within { background:var(--row-hover); }
.tab.viewing { background:var(--row-selected); box-shadow:inset 0 0 0 1px var(--line-strong); }
.tab:focus-visible { outline-offset:-2px; }
/* The mic recipient: a full-height green edge. */
.tab.mic::before { content:""; position:absolute; left:0; top:0; bottom:0; width:2px; border-radius:4px 0 0 4px; background:var(--green); }
.tab.offline .tab-label, .tab.offline .where { color:var(--faint); }
.tab.dragging { opacity:.5; }
.statusslot { grid-row:1; grid-column:1; height:17px; }
.tab-label { grid-row:1; grid-column:2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.waited { grid-row:1; grid-column:3; font-size:11px; color:var(--amber); }
.where { grid-row:2; grid-column:2; display:flex; align-items:center; gap:5px; min-width:0; font:10.5px/15px var(--mono, monospace); color:var(--muted); }
.branch-icon { flex:none; width:11px; height:11px; fill:none; stroke:currentColor; stroke-width:1.4; stroke-linecap:round; }

.dot { width:6px; height:6px; border-radius:50%; }
.think { background:var(--violet); }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:13px; animation-delay:.2s; }
.waitcount, .mutecount { font:600 11px var(--sans); font-variant-numeric:tabular-nums; }
.waitcount { color:var(--amber); }
.mutecount, .mutespk { color:var(--red); }
.mutespk { width:13px; height:13px; }

/* Hover lives on line 2 only: the key cap in the reserved meta cell, Settle
   laid over the end of the branch. Line 1 never changes. */
.shortcut { grid-row:2; grid-column:3; justify-self:end; align-self:center; min-width:34px; height:16px; padding:0 4px; box-sizing:border-box; font:9px/13px var(--mono, monospace); color:var(--muted); text-align:center; background:var(--panel-solid); border:1px solid var(--line-strong); border-bottom-width:2px; border-radius:4px; opacity:0; }
.shortcut.none { visibility:hidden; }
.tab:hover .shortcut, .tab:focus-within .shortcut { opacity:1; }
.settle { position:absolute; right:calc(var(--padX) + var(--meta) + var(--gap)); bottom:5px; height:18px; padding:0 8px; box-sizing:border-box; border:1px solid var(--line-strong); border-radius:4px; background:var(--panel-solid); box-shadow:-14px 0 8px -2px var(--row-hover); color:var(--ink); font:10.5px/16px var(--sans); opacity:0; pointer-events:none; }
.tab.viewing .settle { box-shadow:-14px 0 8px -2px var(--row-selected); }
.tab:hover .settle, .tab:focus-within .settle { opacity:1; pointer-events:auto; }
.settle:hover, .settle:focus-visible { border-color:var(--muted); }
.keymenu .shortcut { opacity:1; }

.keymenu-scrim { position:fixed; inset:0; z-index:9; }
.keymenu { position:absolute; z-index:10; min-width:150px; padding:6px; display:flex; flex-direction:column; gap:2px; background:var(--panel-solid); border:1px solid var(--line-strong); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.35); }
.keymenu-title { margin:2px 6px 4px; font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
.keymenu-item { display:flex; align-items:center; gap:8px; padding:4px 6px; border:0; border-radius:6px; background:none; color:var(--ink); font:11px var(--sans); text-align:left; }
.keymenu-item:hover:not(:disabled), .keymenu-item:focus-visible { background:var(--surface-hover); }
.keymenu-item:disabled { opacity:.45; }
.keymenu-item span { color:var(--muted); }
@keyframes eq { 50% { transform:scaleY(.5); } }
</style>
