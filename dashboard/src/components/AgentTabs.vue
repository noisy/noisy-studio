<script setup lang="ts">
import { groupAgents, moveWithinProject, type ProjectGroup } from "./agentOrder";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { interpolateRecipientWeights } from "./recipientTransition";
import { conversationLabel } from "../conversationLabel";
import { projectHue, waitLabel } from "./tabDetails";

export interface AgentMeta {
  label: string;
  online: boolean;
  activated_at: number;
  offline_since: number | null;
  manual_pos?: number | null;
  shortcut?: number | null; // the Tab N hotkey that reaches it (daemon-numbered)
  project?: string | null; // git repository (or folder) the session runs in
  branch?: string | null;
  waiting_since?: number | null; // epoch s; set while it is your move
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
  }>(),
  { thinking: () => [], activity: () => ({}), queued: () => ({}), muted: () => [], meta: null, settledOpen: undefined },
);

// Geometry knobs: one row height for every state, so nothing shifts. Two
// lines: the conversation, then where it runs (branch).
const ROW_PX = 40;
const PROJECT_HEAD_PX = 24;
// Waiting times are shown in whole minutes; a coarse clock is enough.
const CLOCK_TICK_MS = 30_000;
const clock = ref(Date.now() / 1000);
const clockTimer = setInterval(() => { clock.value = Date.now() / 1000; }, CLOCK_TICK_MS);
onBeforeUnmount(() => clearInterval(clockTimer));
const waited = (name: string) => waitLabel(props.meta?.[name]?.waiting_since, props.now ?? clock.value);

// One clock redistributes the existing Mic space, including interrupted moves.
const tabStrip = ref<HTMLElement | null>(null);
const recipientWeights = ref<Record<string, number>>(props.active ? { [props.active]: 1 } : {});
let recipientFrame = 0;
watch(() => props.active, (recipient) => {
  cancelAnimationFrame(recipientFrame);
  const from = { ...recipientWeights.value };
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    recipientWeights.value = recipient ? { [recipient]: 1 } : {};
    return;
  }
  const duration = Number(tabStrip.value && getComputedStyle(tabStrip.value).getPropertyValue('--mic-transition-duration-ms')) || 220;
  const started = performance.now();
  const animate = (now: number) => {
    const progress = Math.min(1, (now - started) / duration);
    recipientWeights.value = interpolateRecipientWeights(from, recipient, progress);
    if (progress < 1) recipientFrame = requestAnimationFrame(animate);
    else recipientWeights.value = recipient ? { [recipient]: 1 } : {};
  };
  recipientFrame = requestAnimationFrame(animate);
});
onBeforeUnmount(() => cancelAnimationFrame(recipientFrame));

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

// Grouping and ordering live in agentOrder.ts, next to the order the
// widget uses, so the two rules cannot drift apart unnoticed.
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
// What waits for you in a project: its queued messages, in amber.
const waitingIn = (group: ProjectGroup) => group.names.reduce((sum, name) => sum + (props.queued[name] ?? 0), 0);
// A daemon that knows no projects (legacy, or no repository at all) gets the
// plain list: a lone "No project" heading would say nothing.
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
// Settled rows sit outside their project, so their second line names it.
const whereLine = (tab: Tab) => {
  const meta = props.meta?.[tab.name];
  return (tab.settled ? [meta?.project, meta?.branch] : [meta?.branch]).filter(Boolean).join(" · ");
};
const statusText = (name: string, online: boolean) =>
  !online ? "Ended" : props.muted.includes(name) ? "Muted" : props.speaking.includes(name) ? "Speaking"
    : props.thinking.includes(name) ? "Working" : "Ready";

// Drag & drop within a project only: a project is where the session runs,
// not a choice. Settled rows do not drag (their order is when they ended).
const dragging = ref<string | null>(null);
function onDrop(target: Tab) {
  const name = dragging.value;
  dragging.value = null;
  if (!name || target.settled) return;
  const order = moveWithinProject(Object.keys(props.agents), props.meta ?? {}, name, target.name);
  if (order) emit("reorder", order);
}
</script>

<template>
  <nav v-if="tabCount" ref="tabStrip" class="tabs" aria-label="Conversations" :style="{ '--tab-row': ROW_PX + 'px', '--project-head': PROJECT_HEAD_PX + 'px' }">
    <template v-for="item in items" :key="item.key">
      <!-- A project heading: badge, name, and how many messages wait for
           you there (amber, reserved slot). Not a control. -->
      <div v-if="item.kind === 'project'" class="project-head" :class="{ unknown: !item.project }">
        <span class="badge" :style="item.project ? { '--hue': projectHue(item.project) } : undefined" aria-hidden="true">{{ item.project ? item.project.charAt(0).toUpperCase() : '?' }}</span>
        <span class="project-name clip">{{ item.project ?? 'No project' }}</span>
        <span class="project-waiting" :title="item.waiting ? `${item.waiting} waiting for you` : undefined">{{ item.waiting || '' }}</span>
      </div>
      <button
        v-else-if="item.kind === 'settled'"
        type="button" class="section toggle" :aria-expanded="settledShown" @click="toggleSettled"
      ><span class="chev" :class="{ open: settledShown }" aria-hidden="true">▸</span> Settled <b>{{ item.count }}</b></button>
      <button
        v-else
        class="tab"
        :draggable="!item.tab.settled"
        :aria-pressed="item.tab.name === viewed"
        :title="[item.tab.label, item.tab.name === active ? 'Receiving your speech' : '', statusText(item.tab.name, item.tab.online), activity[item.tab.name] ?? ''].filter(Boolean).join(' · ')"
        :class="{
          viewing: item.tab.name === viewed,
          mic: item.tab.name === active,
          speaking: speaking.includes(item.tab.name),
          offline: !item.tab.online,
          dragging: item.tab.name === dragging,
        }"
        @click="$emit('select', item.tab.name)"
        @dragstart="dragging = item.tab.name"
        @dragend="dragging = null"
        @dragover.prevent
        @drop.prevent="onDrop(item.tab)"
      >
        <!-- ONE status glyph, fixed slot, priority ladder (option B):
             MUTE (with or without a count) > SPEAKING (green equalizer) >
             WAIT count (amber - messages waiting to be heard beat the mere
             "working" pulse) > WORKING (violet) > idle dot. "Who gets the
             mic" needs no glyph - that's the Mic badge. -->
        <span class="statusslot">
          <template v-if="muted.includes(item.tab.name)">
            <span v-if="(queued[item.tab.name] ?? 0) > 0" class="mutecount" :title="`Muted — ${queued[item.tab.name]} waiting`">
              {{ queued[item.tab.name] }}
            </span>
            <svg v-else class="mutespk" viewBox="0 0 14 14" title="Muted" aria-label="muted">
              <path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" />
              <line x1="10" y1="5" x2="13" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
              <line x1="13" y1="5" x2="10" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
            </svg>
          </template>
          <span v-else-if="speaking.includes(item.tab.name)" class="eq" aria-label="speaking">
            <i /><i /><i />
          </span>
          <span v-else-if="(queued[item.tab.name] ?? 0) > 0" class="waitcount" :title="`${queued[item.tab.name]} waiting`">
            {{ queued[item.tab.name] }}
          </span>
          <span v-else-if="thinking.includes(item.tab.name)" class="dot think" title="Working" />
          <span v-else class="dot" />
        </span>
        <span class="lines">
          <span class="line main">
            <span class="tab-label">{{ item.tab.label }}</span>
            <span class="waited" :title="waited(item.tab.name) ? 'Waiting for you' : undefined">{{ waited(item.tab.name) }}</span>
            <span class="mic-recipient" :style="{ '--mic-weight': recipientWeights[item.tab.name] ?? 0 }" :aria-hidden="item.tab.name !== active" title="Receiving your speech">Mic</span>
            <!-- Tab N hotkey number, from the daemon's stable order: a
                 reserved slot, empty when none. -->
            <kbd class="shortcut" :title="meta?.[item.tab.name]?.shortcut ? `Tab ${meta[item.tab.name].shortcut} hotkey` : undefined">{{ meta?.[item.tab.name]?.shortcut ?? '' }}</kbd>
          </span>
          <span class="line where clip">{{ whereLine(item.tab) }}</span>
        </span>
        <!-- Settle: hides the conversation, it does not end the session;
             it comes back when its session speaks. Settling the mic's row
             hands the mic to the next one (the daemon decides and says so).
             Shown on hover or focus, laid over the end of line 2, so the
             title, wait time, Mic and number never move. Settled rows have
             no action: the daemon cannot bring a hidden one back yet. -->
        <span
          v-if="!item.tab.settled"
          class="settle"
          role="button" tabindex="0" @keydown.enter.stop.prevent="$emit('settle', item.tab.name)" @keydown.space.stop.prevent="$emit('settle', item.tab.name)"
          title="Settle: hide it until its session speaks again"
          @click.stop="$emit('settle', item.tab.name)"
          >Settle</span
        >
      </button>
    </template>
  </nav>
</template>

<style scoped>

.tabs { display:flex; flex-direction:column; gap:2px; padding:2px; }
.tab { position:relative; flex:none; display:flex; align-items:center; gap:8px; width:100%; height:var(--tab-row); padding:0 10px; font:13px var(--sans); text-align:left; color:var(--muted); border:1px solid transparent; border-radius:8px; background:transparent; min-width:0; box-sizing:border-box; }
.tab:hover { color:var(--ink); background:var(--surface-hover); }
.tab.viewing { background:var(--surface-hover); border-color:var(--line-strong); color:var(--ink); }
/* The mic recipient: an inset green edge (a shadow, no size change) on top
   of the Mic label, so it reads at a glance even in a long list. */
.tab.mic { box-shadow:inset 2px 0 0 var(--green); }
.tab.offline { border-style:dashed; }
.tab.offline .tab-label { opacity:.7; }
.tab.dragging { opacity:.5; }
.tab:focus-visible { outline-offset:-2px; }
/* Explicit, complementary widths avoid max-width's content-size plateau. */
.mic-recipient { font-size:10px; color:var(--green); flex:none; width:calc(3ch * var(--mic-weight)); margin-left:calc(-6px * (1 - var(--mic-weight))); overflow:hidden; white-space:nowrap; opacity:var(--mic-weight); }
.lines { flex:1; min-width:0; display:flex; flex-direction:column; justify-content:center; gap:1px; }
.line { display:flex; align-items:center; gap:6px; min-width:0; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.where { display:block; height:13px; font:10px var(--mono, monospace); color:var(--muted); }
.waited { flex:none; min-width:22px; text-align:right; font-size:10px; color:var(--amber); }
.tab-label { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.shortcut { flex:none; width:14px; font:10px var(--mono, monospace); color:var(--muted); text-align:center; background:none; border:0; padding:0; }
.statusslot { display:inline-flex; justify-content:center; align-items:center; width:13px; height:13px; flex:none; align-self:flex-start; margin-top:6px; }
.dot { width:6px; height:6px; background:var(--muted); border-radius:50%; }
.think { background:var(--violet); }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:13px; animation-delay:.2s; }
.waitcount { color:var(--amber); font-size:11px; }
.mutecount, .mutespk { color:var(--red); }
.mutespk { width:14px; height:14px; }
/* Over the end of line 2 (the branch), on the z-axis: nothing reflows. */
.settle { position:absolute; right:8px; bottom:3px; height:15px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); box-shadow:-12px 0 8px -2px var(--surface-hover); color:var(--ink); font:10px/13px var(--sans); box-sizing:border-box; opacity:0; pointer-events:none; }
.tab:hover .settle, .tab:focus-within .settle { opacity:1; pointer-events:auto; }
.settle:hover, .settle:focus-visible { border-color:var(--muted); }
/* Project heading: badge + name + amber waiting count in a reserved slot. */
.project-head { display:flex; align-items:center; gap:8px; height:var(--project-head); margin-top:10px; padding:0 10px; font:600 11px var(--sans); color:var(--ink); }
.project-head:first-child { margin-top:2px; }
.project-head.unknown { color:var(--muted); }
.badge { flex:none; width:13px; height:13px; border-radius:3px; font-size:8px; font-weight:600; line-height:13px; text-align:center; color:#fff; background:hsl(var(--hue, 0) 45% 42%); }
.unknown .badge { background:var(--surface-hover); color:var(--muted); }
.project-name { flex:1; }
.project-waiting { flex:none; min-width:18px; text-align:right; font-size:11px; color:var(--amber); }
.section { display:flex; align-items:center; gap:6px; margin:14px 10px 4px; padding:0; border:0; background:none; font:10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); text-align:left; }
.section b { font-weight:500; color:var(--ink); letter-spacing:0; }
.toggle { cursor:pointer; }
.toggle:hover { color:var(--ink); }
.chev { display:inline-block; font-size:12px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }
@keyframes eq { 50% { transform:scaleY(.5); } }

</style>
