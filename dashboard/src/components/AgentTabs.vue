<script setup lang="ts">
import { orderAgents } from "./agentOrder";
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
    queued?: Record<string, number>; // waiting messages per agent
    muted?: string[]; // per-conversation mute (future daemon feature)
  }>(),
  { thinking: () => [], queued: () => ({}), muted: () => [], meta: null },
);

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

interface Tab {
  name: string;
  label: string;
  online: boolean;
  activatedAt: number;
  offlineSince: number;
  manualPos: number | null;
}

// Ordering lives in agentOrder.ts so the widget's avatars come out in the
// SAME order as these tabs - two surfaces the user sees at once must not
// disagree about which conversation is third.
const tabs = computed<Tab[]>(() => {
  const meta = props.meta ?? {};
  return orderAgents(Object.keys(props.agents), meta).map((name) => ({
    name,
      label: conversationLabel(meta[name]?.label ?? props.agents[name], name),
    online: meta[name]?.online ?? true,
    activatedAt: meta[name]?.activated_at ?? 0,
    offlineSince: meta[name]?.offline_since ?? 0,
    manualPos: meta[name]?.manual_pos ?? null,
  }));
});
const groups = computed(() => ({
  actives: tabs.value.filter((t) => t.online),
  offline: tabs.value.filter((t) => !t.online),
}));

// Drag & drop within a group only: dropping an active tab onto an offline
// one (or vice versa) is ignored — group membership is liveness, not choice.
const dragging = ref<string | null>(null);
function onDrop(target: Tab) {
  const name = dragging.value;
  dragging.value = null;
  if (!name || name === target.name) return;
  const group = target.online ? groups.value.actives : groups.value.offline;
  const names = group.map((t) => t.name);
  const from = names.indexOf(name);
  if (from === -1) return; // cross-group drop
  names.splice(from, 1);
  names.splice(names.indexOf(target.name) + (from <= names.indexOf(target.name) ? 1 : 0), 0, name);
  emit("reorder", names);
}
</script>

<template>
  <nav v-if="tabs.length" ref="tabStrip" class="tabs" aria-label="Conversations">
    <button
      v-for="tab in tabs"
      :key="tab.name"
      draggable="true"
      :aria-pressed="tab.name === viewed"
      :title="[tab.label, tab.name === active ? 'Receiving your speech' : '', !tab.online ? 'Offline' : muted.includes(tab.name) ? 'Muted' : speaking.includes(tab.name) ? 'Speaking' : thinking.includes(tab.name) ? 'Working' : 'Ready'].filter(Boolean).join(' · ')"
      :class="{
        viewing: tab.name === viewed,
        speaking: speaking.includes(tab.name),
        offline: !tab.online,
        dragging: tab.name === dragging,
      }"
      @click="$emit('select', tab.name)"
      @dragstart="dragging = tab.name"
      @dragend="dragging = null"
      @dragover.prevent
      @drop.prevent="onDrop(tab)"
    >
      <!-- ONE status glyph, fixed slot, priority ladder (option B):
           MUTE (with or without a count) > SPEAKING (green equalizer) >
           WAIT count (amber — messages waiting to be heard beat the mere
           "working" pulse) > WORKING (violet) > idle dot. "Who gets the
           mic" needs no glyph — that's the selected (fused, taller) tab. -->
      <span class="statusslot">
        <template v-if="muted.includes(tab.name)">
          <span v-if="(queued[tab.name] ?? 0) > 0" class="mutecount" :title="`Muted — ${queued[tab.name]} waiting`">
            {{ queued[tab.name] }}
          </span>
          <svg v-else class="mutespk" viewBox="0 0 14 14" title="Muted" aria-label="muted">
            <path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" />
            <line x1="10" y1="5" x2="13" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
            <line x1="13" y1="5" x2="10" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          </svg>
        </template>
        <span v-else-if="speaking.includes(tab.name)" class="eq" aria-label="speaking">
          <i /><i /><i />
        </span>
        <span v-else-if="(queued[tab.name] ?? 0) > 0" class="waitcount" :title="`${queued[tab.name]} waiting`">
          {{ queued[tab.name] }}
        </span>
        <span v-else-if="thinking.includes(tab.name)" class="dot think" title="Working" />
        <span v-else class="dot" />
      </span>
      <span class="tab-label">{{ tab.label }}</span>
      <span class="mic-recipient" :style="{ '--mic-weight': recipientWeights[tab.name] ?? 0 }" :aria-hidden="tab.name !== active" title="Receiving your speech">Mic</span>
      <!-- Close, on every tab, like a browser: it hides the conversation,
           it does not end the session. Closing the mic's tab hands the mic
           to the next one (the daemon decides and says so). A real flex
           slot at the end, always present, so it can never sit on top of
           the Mic badge and the tab's width never shifts on hover. -->
      <span
        class="dismiss"
        role="button" tabindex="0" @keydown.enter.stop.prevent="$emit('dismiss', tab.name)" @keydown.space.stop.prevent="$emit('dismiss', tab.name)"
        title="Close this conversation"
        @click.stop="$emit('dismiss', tab.name)"
        >✕</span
      >
    </button>
  </nav>
</template>

<style scoped>

.tabs { display:flex; flex-wrap:wrap; gap:6px; }
button { position:relative; display:inline-flex; align-items:center; gap:8px; font:13px var(--sans); color:var(--muted); border:1px solid transparent; background:transparent; padding:9px 12px; min-width:0; max-width:100%; }
/* Explicit, complementary widths avoid max-width's content-size plateau. */
.mic-recipient { font-size:10px; color:var(--green); flex:none; width:calc(3ch * var(--mic-weight)); margin-left:calc(-8px * (1 - var(--mic-weight))); overflow:hidden; white-space:nowrap; opacity:var(--mic-weight); }
.tab-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:220px; }
button:hover { color:var(--ink); background:var(--surface-hover); }
button.viewing { background:var(--surface-hover); border-color:var(--line-strong); color:var(--ink); }
button.offline { border-style:dashed; }
button.dragging { opacity:.5; }
.statusslot { display:inline-flex; justify-content:center; align-items:center; width:13px; height:13px; flex:none; }
.dot { width:6px; height:6px; background:var(--muted); border-radius:50%; }
.think { background:var(--violet); }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:13px; animation-delay:.2s; }
.waitcount { color:var(--amber); font-size:11px; }
.mutecount, .mutespk { color:var(--red); }
.mutespk { width:14px; height:14px; }
.dismiss { flex:none; width:16px; margin-left:2px; text-align:center; padding:2px 0; color:var(--muted); line-height:1; }
.dismiss:hover, .dismiss:focus-visible { color:var(--red); }
@keyframes eq { 50% { transform:scaleY(.5); } }

</style>
