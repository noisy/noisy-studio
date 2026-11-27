<script setup lang="ts">
import { sectionAgents } from "./agentOrder";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { interpolateRecipientWeights } from "./recipientTransition";
import { conversationLabel } from "../conversationLabel";

export interface AgentMeta {
  label: string;
  online: boolean;
  activated_at: number;
  offline_since: number | null;
  manual_pos?: number | null;
}

const props = withDefaults(
  defineProps<{
    agents: Record<string, string>; // id -> human label (legacy daemons)
    meta?: Record<string, AgentMeta> | null; // id -> tab metadata (#11)
    active: string | null; // the agent receiving transcripts
    viewed: string | null; // the tab being displayed
    speaking: string[]; // agents currently playing audio
    thinking?: string[]; // agents currently working (live activity line)
    working?: string[]; // agents working long enough to leave the top section
    activity?: Record<string, string>; // live activity text per agent
    queued?: Record<string, number>; // waiting messages per agent
    muted?: string[]; // per-conversation mute (future daemon feature)
    workingOpen?: boolean; // initial Working state; omit for the remembered one
    settledOpen?: boolean; // initial Settled state; omit for the remembered one
  }>(),
  { thinking: () => [], working: () => [], activity: () => ({}), queued: () => ({}), muted: () => [], meta: null, workingOpen: undefined, settledOpen: undefined },
);

// Geometry knob: one row height for every state, so nothing shifts.
const ROW_PX = 34;

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
  dismiss: [name: string];
  reorder: [names: string[]];
}>();

// Both lower sections fold. Working starts open, Settled closed; the
// reader's choice is remembered per browser.
type Foldable = "working" | "settled";
const OPEN_KEYS: Record<Foldable, string> = { working: "noisy.tabs.workingOpen", settled: "noisy.tabs.settledOpen" };
const OPEN_BY_DEFAULT: Record<Foldable, boolean> = { working: true, settled: false };
function storedOpen(section: Foldable): boolean {
  try {
    const saved = localStorage.getItem(OPEN_KEYS[section]);
    return saved === null ? OPEN_BY_DEFAULT[section] : saved === "1";
  } catch { return OPEN_BY_DEFAULT[section]; }
}
const open = ref<Record<Foldable, boolean>>({
  working: props.workingOpen ?? storedOpen("working"),
  settled: props.settledOpen ?? storedOpen("settled"),
});
function toggle(section: Foldable) {
  open.value[section] = !open.value[section];
  try { localStorage.setItem(OPEN_KEYS[section], open.value[section] ? "1" : "0"); } catch { /* session only */ }
}

type Section = "yourTurn" | "working" | "settled";
interface Tab { name: string; label: string; online: boolean; section: Section }
type Item =
  | { kind: "tab"; key: string; tab: Tab }
  | { kind: "heading"; key: string; section: "working" | "settled"; count: number };

// Ordering and sectioning live in agentOrder.ts, next to the order the
// widget uses, so the two rules cannot drift apart unnoticed.
const sections = computed(() =>
  sectionAgents(Object.keys(props.agents), props.meta ?? {}, {
    working: props.working, speaking: props.speaking, queued: props.queued,
    keepInSight: [props.viewed, props.active],
  }),
);
const tabOf = (name: string, section: Section): Tab => ({
  name,
  label: conversationLabel(props.meta?.[name]?.label ?? props.agents[name], name),
  online: props.meta?.[name]?.online ?? true,
  section,
});
const tabCount = computed(() => Object.keys(props.agents).length);
const items = computed<Item[]>(() => {
  const { yourTurn, working, settled } = sections.value;
  const rows = (names: string[], section: Section): Item[] =>
    names.map((name) => ({ kind: "tab", key: name, tab: tabOf(name, section) }));
  return [
    ...rows(yourTurn, "yourTurn"),
    ...(working.length ? [{ kind: "heading", key: "h-working", section: "working", count: working.length } as Item] : []),
    // Folded Working still shows the row you look at or talk to.
    ...rows(open.value.working ? working : working.filter((name) => name === props.viewed || name === props.active), "working"),
    ...(settled.length ? [{ kind: "heading", key: "h-settled", section: "settled", count: settled.length } as Item] : []),
    ...(open.value.settled ? rows(settled, "settled") : []),
  ];
});

// Drag & drop within a section only: a section is state, not a choice.
const dragging = ref<string | null>(null);
function onDrop(target: Tab) {
  const name = dragging.value;
  dragging.value = null;
  if (!name || name === target.name) return;
  const names = [...sections.value[target.section]];
  const from = names.indexOf(name);
  if (from === -1) return; // cross-section drop
  names.splice(from, 1);
  names.splice(names.indexOf(target.name) + (from <= names.indexOf(target.name) ? 1 : 0), 0, name);
  emit("reorder", names);
}
</script>

<template>
  <nav v-if="tabCount" ref="tabStrip" class="tabs" aria-label="Conversations" :style="{ '--tab-row': ROW_PX + 'px' }">
    <template v-for="item in items" :key="item.key">
      <button
        v-if="item.kind === 'heading'"
        type="button" class="section toggle" :aria-expanded="open[item.section]" @click="toggle(item.section)"
      ><span class="chev" :class="{ open: open[item.section] }" aria-hidden="true">▸</span> {{ item.section === 'working' ? 'Working' : 'Settled' }} <b>{{ item.count }}</b></button>
      <button
        v-else
        class="tab"
        draggable="true"
        :aria-pressed="item.tab.name === viewed"
        :title="[item.tab.label, item.tab.name === active ? 'Receiving your speech' : '', !item.tab.online ? 'Offline' : muted.includes(item.tab.name) ? 'Muted' : speaking.includes(item.tab.name) ? 'Speaking' : thinking.includes(item.tab.name) ? 'Working' : 'Ready', activity[item.tab.name] ?? ''].filter(Boolean).join(' · ')"
        :class="{
          viewing: item.tab.name === viewed,
          speaking: speaking.includes(item.tab.name),
          offline: !item.tab.online,
          working: item.tab.section === 'working',
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
        <span class="tab-label">{{ item.tab.label }}</span>
        <span v-if="item.tab.section === 'working' && activity[item.tab.name]" class="activity">{{ activity[item.tab.name] }}</span>
        <span class="mic-recipient" :style="{ '--mic-weight': recipientWeights[item.tab.name] ?? 0 }" :aria-hidden="item.tab.name !== active" title="Receiving your speech">Mic</span>
        <!-- Close, on every row, like a browser tab: it hides the
             conversation, it does not end the session. Closing the mic's
             row hands the mic to the next one (the daemon decides and says
             so). A real flex slot, always reserved, revealed on hover or
             focus - the row never shifts. -->
        <span
          class="dismiss"
          role="button" tabindex="0" @keydown.enter.stop.prevent="$emit('dismiss', item.tab.name)" @keydown.space.stop.prevent="$emit('dismiss', item.tab.name)"
          title="Close this conversation"
          @click.stop="$emit('dismiss', item.tab.name)"
          >✕</span
        >
      </button>
    </template>
  </nav>
</template>

<style scoped>

.tabs { display:flex; flex-direction:column; gap:2px; padding:2px; }
.tab { position:relative; flex:none; display:flex; align-items:center; gap:8px; width:100%; height:var(--tab-row); padding:0 10px; font:13px var(--sans); text-align:left; color:var(--muted); border:1px solid transparent; border-radius:8px; background:transparent; min-width:0; }
.tab:hover { color:var(--ink); background:var(--surface-hover); }
.tab.viewing { background:var(--surface-hover); border-color:var(--line-strong); color:var(--ink); }
.tab.offline { border-style:dashed; }
.tab.offline .tab-label { opacity:.7; }
.tab.working:not(.viewing) .tab-label { color:color-mix(in srgb, var(--muted) 85%, transparent); }
.tab.dragging { opacity:.5; }
.tab:focus-visible { outline-offset:-2px; }
/* Explicit, complementary widths avoid max-width's content-size plateau. */
.mic-recipient { font-size:10px; color:var(--green); flex:none; width:calc(3ch * var(--mic-weight)); margin-left:calc(-8px * (1 - var(--mic-weight))); overflow:hidden; white-space:nowrap; opacity:var(--mic-weight); }
.tab-label { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.activity { flex:none; max-width:84px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:10px; color:var(--violet-dim); }
.statusslot { display:inline-flex; justify-content:center; align-items:center; width:13px; height:13px; flex:none; }
.dot { width:6px; height:6px; background:var(--muted); border-radius:50%; }
.think { background:var(--violet); }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:13px; animation-delay:.2s; }
.waitcount { color:var(--amber); font-size:11px; }
.mutecount, .mutespk { color:var(--red); }
.mutespk { width:14px; height:14px; }
.dismiss { flex:none; width:16px; text-align:center; padding:2px 0; color:var(--muted); line-height:1; opacity:0; }
.tab:hover .dismiss, .tab:focus-within .dismiss, .tab.viewing .dismiss { opacity:1; }
.dismiss:hover, .dismiss:focus-visible { color:var(--red); }
.section { display:flex; align-items:center; gap:6px; margin:14px 10px 4px; padding:0; border:0; background:none; font:10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); text-align:left; }
.section b { font-weight:500; color:var(--ink); letter-spacing:0; }
.toggle { cursor:pointer; }
.toggle:hover { color:var(--ink); }
.chev { display:inline-block; font-size:12px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }
@keyframes eq { 50% { transform:scaleY(.5); } }

</style>
