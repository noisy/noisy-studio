<script setup lang="ts">
// Option A - Calm rows: project / title / delegated work, one signal slot,
// Snooze and Settle on hover. The closest to T3 and to today's list.
import { computed } from "vue";
import ChildSummary from "./ChildSummary.vue";
import LabIcon from "./LabIcon.vue";
import SignalGlyph from "./SignalGlyph.vue";
import { cornerTime, hueOf, initialOf, type LabRow } from "./fixtures";

// Geometry knobs: every row is this tall in every state.
const ROW_PX = 58;
const LOGO_PX = 14;

const props = defineProps<{ row: LabRow }>();
defineEmits<{ snooze: [id: string]; settle: [id: string]; restore: [id: string] }>();

const settled = computed(() => props.row.section === "settled");
const style = computed(() => ({
  "--row": `${ROW_PX}px`, "--logo": `${LOGO_PX}px`,
  ...(hueOf(props.row) != null ? { "--hue": String(hueOf(props.row)) } : {}),
}));
</script>

<template>
  <div class="row" tabindex="0" :style="style"
    :class="{ viewing: row.viewed, forced: row.hover, settled, working: row.section === 'working' }">
    <span v-if="row.mic" class="micbar" title="Receiving your speech" />
    <div class="l1">
      <span class="logo" :class="{ legacy: !row.project }">{{ row.project ? initialOf(row) : "" }}</span>
      <span class="project clip" :class="{ none: !row.project }">{{ row.project ?? "No project" }}</span>
      <span class="time"><LabIcon v-if="row.snoozedUntil" name="snooze" :size="11" />{{ cornerTime(row) }}</span>
    </div>
    <div class="l2">
      <span class="title clip">{{ row.title }}</span>
      <SignalGlyph :row="row" />
    </div>
    <div class="l3">
      <ChildSummary v-if="row.children.length" :children="row.children" />
      <span v-else-if="row.working" class="activity clip">{{ row.activity }}</span>
      <template v-else-if="row.branch"><LabIcon name="branch" :size="11" /><span class="clip">{{ row.branch }}</span></template>
    </div>
    <div class="actions">
      <button v-if="settled" type="button" title="Restore to the list" @click.stop="$emit('restore', row.id)"><LabIcon name="restore" /></button>
      <template v-else>
        <button type="button" title="Snooze…" @click.stop="$emit('snooze', row.id)"><LabIcon name="snooze" /></button>
        <button type="button" title="Settle" @click.stop="$emit('settle', row.id)"><LabIcon name="settle" /></button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.row { position:relative; display:flex; flex-direction:column; justify-content:center; gap:2px; height:var(--row); padding:0 10px 0 12px; border:1px solid transparent; border-radius:8px; color:var(--ink); font:13px var(--sans); cursor:pointer; outline:none; }
.row:hover, .row.forced, .row:focus-visible { background:var(--surface-hover); }
.row.viewing { background:var(--surface-hover); border-color:var(--line-strong); }
.micbar { position:absolute; left:3px; top:12px; bottom:12px; width:2px; border-radius:1px; background:var(--green); }
.l1, .l2, .l3 { display:flex; align-items:center; gap:6px; min-width:0; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.l1 { height:14px; font-size:11px; color:var(--muted); }
.logo { flex:none; width:var(--logo); height:var(--logo); border-radius:4px; font:600 9px/var(--logo) var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.logo.legacy { background:transparent; border:1px dashed var(--line-strong); }
.project { flex:1; }
.project.none { font-style:italic; opacity:.7; }
.time { flex:none; display:inline-flex; align-items:center; gap:3px; min-width:28px; justify-content:flex-end; font-size:11px; font-variant-numeric:tabular-nums; color:var(--muted); }
.l2 { height:18px; }
.title { flex:1; font-weight:500; }
.l3 { height:14px; font:10.5px var(--mono); color:var(--muted); padding-left:1px; }
.activity { font-family:var(--sans); font-size:11px; color:var(--violet-dim); }
.settled .title, .settled .l3, .settled .project { opacity:.6; }
.settled .logo { filter:grayscale(1); opacity:.6; }
.working .title { color:color-mix(in srgb, var(--ink) 80%, var(--muted)); }
/* Hover actions: an opaque plate over the time, never a reflow. */
.actions { position:absolute; top:4px; right:6px; display:flex; gap:2px; padding-left:14px; background:linear-gradient(to right, transparent, var(--surface-hover) 14px); opacity:0; pointer-events:none; }
.row:hover .actions, .row.forced .actions, .row:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:grid; place-items:center; width:24px; height:22px; padding:0; border:0; border-radius:6px; background:transparent; color:var(--muted); }
.actions button:hover { color:var(--ink); background:var(--line); }
</style>
