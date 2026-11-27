<script setup lang="ts">
// One delegated agent: a glyph slot, its task, and a status slot. Hover
// lays the CEO's controls over the status slot: pause/resume and stop for
// running work, Review for finished work, Stop for blocked work.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { agentStatus, tokensLabel, type DelegatedAgent } from "./orgModel";

// Geometry knobs.
const ROW_PX = 22;
const STATUS_SLOT_PX = 46;

const props = defineProps<{ agent: DelegatedAgent; forced?: boolean }>();
defineEmits<{ pause: []; resume: []; stop: []; review: [] }>();

const status = computed(() => agentStatus(props.agent));
const tooltip = computed(() =>
  [props.agent.title, props.agent.who, props.agent.note, props.agent.worktree && `worktree ${props.agent.worktree}`,
    props.agent.tokens != null && `${tokensLabel(props.agent.tokens)} tokens today`].filter(Boolean).join(" · "),
);
const controllable = computed(() => props.agent.state !== "done");
</script>

<template>
  <div class="agent" :class="[agent.state, { forced }]" :title="tooltip" :style="{ '--row': `${ROW_PX}px`, '--status-slot': `${STATUS_SLOT_PX}px` }">
    <span class="glyph" :aria-label="agent.state">
      <span v-if="agent.state === 'working'" class="spin" />
      <span v-else-if="agent.state === 'pending'" class="ring" />
      <template v-else-if="agent.state === 'blocked'">!</template>
      <template v-else-if="agent.state === 'review'">●</template>
      <LabIcon v-else-if="agent.state === 'paused'" name="pause" :size="10" />
      <template v-else>✓</template>
    </span>
    <span class="title clip">{{ agent.title }}</span>
    <span class="status">{{ status }}</span>
    <div v-if="controllable" class="actions">
      <button v-if="agent.state === 'review'" type="button" class="word" @click.stop="$emit('review')"><LabIcon name="review" :size="11" />Review</button>
      <button v-if="agent.state === 'working' || agent.state === 'pending'" type="button" title="Pause" aria-label="Pause" @click.stop="$emit('pause')"><LabIcon name="pause" :size="11" /></button>
      <button v-if="agent.state === 'paused'" type="button" title="Resume" aria-label="Resume" @click.stop="$emit('resume')"><LabIcon name="play" :size="11" /></button>
      <button type="button" title="Stop" aria-label="Stop" @click.stop="$emit('stop')"><LabIcon name="stop" :size="11" /></button>
    </div>
  </div>
</template>

<style scoped>
.agent { position:relative; display:flex; align-items:center; gap:6px; height:var(--row); padding:0 8px 0 6px; border-radius:6px; font:11.5px var(--sans); color:var(--muted); }
.agent:hover, .agent.forced { background:var(--surface-hover); color:var(--ink); }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.glyph { flex:none; display:grid; place-items:center; width:12px; font-size:10px; font-weight:700; }
.title { flex:1; }
.status { flex:none; min-width:var(--status-slot); text-align:right; font-size:10.5px; font-variant-numeric:tabular-nums; }
.working .glyph, .working .status { color:var(--violet); }
.working .status { color:var(--violet-dim); }
.blocked .glyph, .review .glyph, .blocked .status, .review .status { color:var(--amber); font-weight:600; }
.done, .paused, .pending { opacity:.75; }
.spin { width:8px; height:8px; border:1.5px solid color-mix(in srgb, var(--violet) 30%, transparent); border-top-color:var(--violet); border-radius:50%; animation:spin 1s linear infinite; }
.ring { width:7px; height:7px; border:1.5px solid var(--line-strong); border-radius:50%; }
.actions { position:absolute; top:2px; right:4px; bottom:2px; display:flex; gap:3px; padding-left:14px; background:linear-gradient(to right, transparent, var(--surface-hover) 14px); opacity:0; pointer-events:none; }
.agent:hover .actions, .agent.forced .actions, .agent:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:inline-flex; align-items:center; justify-content:center; gap:3px; min-width:18px; height:18px; padding:0 3px; border:1px solid var(--line-strong); border-radius:5px; background:var(--panel-solid); color:var(--ink); font:10.5px var(--sans); cursor:pointer; }
.actions button.word { padding:0 6px; }
.actions button:hover { border-color:var(--muted); }
@keyframes spin { to { transform:rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation:none; } }
</style>
