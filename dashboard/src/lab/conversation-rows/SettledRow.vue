<script setup lang="ts">
// A settled or ended conversation: one quiet line under Settled, with its
// project, and Restore laid over its corner on hover.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { hueOf, initialOf, type ManagerConversation, type Project } from "./orgModel";
import { waitLabel } from "../../components/tabDetails";

// Geometry knobs.
const ROW_PX = 26;

const props = defineProps<{ project: Project; manager: ManagerConversation; now: number; forced?: boolean }>();
defineEmits<{ select: []; restore: [] }>();

const hue = computed(() => hueOf(props.project));
const since = computed(() => waitLabel(props.manager.endedAt ?? null, props.now));
</script>

<template>
  <div class="settled" role="button" tabindex="0" :class="{ forced }" :title="`${manager.title} · ${manager.status === 'ended' ? 'ended' : 'settled'} ${since} ago`"
    :style="{ '--row': `${ROW_PX}px`, ...(hue != null ? { '--hue': String(hue) } : {}) }"
    @click="$emit('select')" @keydown.enter.self="$emit('select')">
    <span class="tile" :class="{ legacy: !project.name }">{{ initialOf(project) }}</span>
    <span class="title clip">{{ manager.title }}<span class="project"> · {{ project.name ?? "No project" }}</span></span>
    <span class="since">{{ since }}</span>
    <div class="actions">
      <button type="button" @click.stop="$emit('restore')"><LabIcon name="restore" :size="12" />Restore</button>
    </div>
  </div>
</template>

<style scoped>
.settled { position:relative; display:flex; align-items:center; gap:8px; height:var(--row); padding:0 8px 0 7px; border-radius:7px; font:12px var(--sans); color:var(--muted); cursor:pointer; outline:none; }
.settled:hover, .settled.forced, .settled:focus-visible { background:var(--surface-hover); color:var(--ink); }
.tile { flex:none; width:16px; height:16px; border-radius:4px; font:600 9.5px/16px var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); filter:grayscale(1); opacity:.6; }
.tile.legacy { color:var(--muted); background:var(--line); }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.title { flex:1; }
.project { opacity:.7; }
.since { flex:none; min-width:26px; text-align:right; font-size:11px; font-variant-numeric:tabular-nums; }
.actions { position:absolute; top:3px; right:6px; bottom:3px; display:flex; padding-left:18px; background:linear-gradient(to right, transparent, var(--surface-hover) 18px); opacity:0; pointer-events:none; }
.settled:hover .actions, .settled.forced .actions, .settled:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:inline-flex; align-items:center; gap:4px; height:20px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); color:var(--ink); font:10.5px var(--sans); cursor:pointer; }
.actions button:hover { border-color:var(--muted); }
</style>
