<script setup lang="ts">
// Option B - Manager desk: one card per manager, in hotkey order, never
// re-sorted by state. Line 2 says what it needs from you; the card's bottom
// edge is a segmented bar of its delegated work. Settled rows shrink to one line.
import { computed } from "vue";
import ChildSummary from "./ChildSummary.vue";
import LabIcon from "./LabIcon.vue";
import { CHILD_TONE, cornerTime, hueOf, initialOf, statusLine, type LabRow } from "./fixtures";

// Geometry knobs.
const CARD_PX = 74;
const SETTLED_PX = 32;
const TILE_PX = 14;

const props = defineProps<{ row: LabRow }>();
defineEmits<{ snooze: [id: string]; settle: [id: string]; restore: [id: string] }>();

const settled = computed(() => props.row.section === "settled");
const status = computed(() => statusLine(props.row));
const style = computed(() => ({
  "--card": `${settled.value ? SETTLED_PX : CARD_PX}px`, "--tile": `${TILE_PX}px`,
  ...(hueOf(props.row) != null ? { "--hue": String(hueOf(props.row)) } : {}),
}));
</script>

<template>
  <div class="card" tabindex="0" :style="style"
    :class="{ viewing: row.viewed, forced: row.hover, settled, mic: row.mic, working: row.working }">
    <div class="l1">
      <kbd class="key" :class="{ empty: !row.shortcut }">{{ row.shortcut ?? "" }}</kbd>
      <span v-if="settled" class="tile" :class="{ legacy: !row.project }">{{ row.project ? initialOf(row) : "" }}</span>
      <span class="title clip">{{ row.title }}</span>
      <span class="micslot"><span v-if="row.mic" class="micchip"><LabIcon name="mic" :size="10" />MIC</span></span>
      <span class="time"><LabIcon v-if="row.snoozedUntil" name="snooze" :size="11" />{{ cornerTime(row) }}</span>
    </div>
    <template v-if="!settled">
      <div class="l2" :class="status.tone">
        <span class="glyph">
          <span v-if="row.speaking" class="eq"><i /><i /><i /></span>
          <svg v-else-if="row.muted" class="mute" viewBox="0 0 14 14"><path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" /><path d="M10 5 13 9 M13 5 10 9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" /></svg>
          <span v-else class="pip" />
        </span>
        <span class="clip">{{ status.text }}</span>
      </div>
      <div class="l3">
        <span class="tile" :class="{ legacy: !row.project }">{{ row.project ? initialOf(row) : "" }}</span>
        <span class="project clip" :class="{ none: !row.project }">{{ row.project ?? "No project" }}</span>
        <template v-if="row.children.length"><span class="dot">·</span><ChildSummary :children="row.children" /></template>
        <template v-else-if="row.branch"><span class="dot">·</span><span class="branch clip">{{ row.branch }}</span></template>
      </div>
      <!-- Delegated work at a glance: one segment per child, in its colour. -->
      <div v-if="row.children.length" class="bar">
        <i v-for="child in row.children" :key="child.id" :class="CHILD_TONE[child.state]" />
      </div>
    </template>
    <div class="actions">
      <button v-if="settled" type="button" title="Restore to the desk" @click.stop="$emit('restore', row.id)"><LabIcon name="restore" /></button>
      <template v-else>
        <button type="button" title="Snooze…" @click.stop="$emit('snooze', row.id)"><LabIcon name="snooze" /></button>
        <button type="button" title="Settle" @click.stop="$emit('settle', row.id)"><LabIcon name="settle" /></button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.card { position:relative; display:flex; flex-direction:column; justify-content:center; gap:3px; height:var(--card); padding:0 10px 0 8px; border:1px solid var(--line); border-radius:10px; background:var(--bg1); color:var(--ink); font:13px var(--sans); cursor:pointer; outline:none; overflow:hidden; }
.card:hover, .card.forced, .card:focus-visible { background:var(--surface-hover); }
.card.viewing { background:var(--surface-hover); border-color:var(--line-strong); }
.card.mic { border-color:color-mix(in srgb, var(--green) 70%, transparent); box-shadow:inset 3px 0 0 var(--green); }
.card.settled { border-color:transparent; background:transparent; }
.card.settled:hover, .card.settled.forced { background:var(--surface-hover); }
.l1, .l2, .l3 { display:flex; align-items:center; gap:6px; min-width:0; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.key { flex:none; width:16px; height:16px; border:1px solid var(--line-strong); border-radius:4px; font:600 10px/14px var(--mono); text-align:center; color:var(--muted); background:transparent; }
.key.empty { visibility:hidden; } /* slot kept, nothing drawn */
.title { flex:1; font-size:14px; font-weight:600; }
.working .title { color:color-mix(in srgb, var(--ink) 78%, var(--muted)); }
.micslot { flex:none; width:36px; display:flex; justify-content:flex-end; }
.micchip { display:inline-flex; align-items:center; gap:2px; height:15px; padding:0 4px; border-radius:4px; font:700 9px/15px var(--sans); letter-spacing:.06em; color:var(--green); background:color-mix(in srgb, var(--green) 14%, transparent); }
.time { flex:none; display:inline-flex; align-items:center; gap:3px; min-width:26px; justify-content:flex-end; font-size:11px; font-variant-numeric:tabular-nums; color:var(--muted); }
.l2 { height:16px; padding-left:22px; font-size:12px; }
.l2.ink { color:var(--ink); } .l2.green { color:var(--green); } .l2.amber { color:var(--amber); }
.l2.violet { color:var(--violet-dim); } .l2.red { color:var(--red); } .l2.muted { color:var(--muted); }
.glyph { flex:none; width:12px; display:flex; justify-content:center; }
.pip { width:6px; height:6px; border-radius:50%; background:currentColor; }
.violet .pip { animation:pulse 1.6s ease-in-out infinite; }
.eq { display:flex; gap:2px; align-items:center; height:11px; }
.eq i { width:2px; height:8px; border-radius:1px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:11px; animation-delay:.2s; }
.mute { width:12px; height:12px; }
.l3 { height:14px; padding-left:22px; font-size:11px; color:var(--muted); }
.tile { flex:none; width:var(--tile); height:var(--tile); border-radius:4px; font:600 9px/var(--tile) var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.tile.legacy { background:transparent; border:1px dashed var(--line-strong); }
.project { flex:0 1 auto; max-width:45%; }
.project.none { font-style:italic; opacity:.7; }
.dot { opacity:.5; }
.branch { font:10.5px var(--mono); }
.settled .title { font-size:12px; font-weight:500; opacity:.6; }
.settled .tile { filter:grayscale(1); opacity:.6; }
.bar { position:absolute; left:30px; right:10px; bottom:5px; display:flex; gap:2px; height:2px; }
.bar i { flex:1; border-radius:1px; }
.bar .violet { background:var(--violet); } .bar .amber { background:var(--amber); } .bar .muted { background:var(--line-strong); }
.actions { position:absolute; top:6px; right:6px; display:flex; gap:2px; padding-left:16px; background:linear-gradient(to right, transparent, var(--surface-hover) 16px); opacity:0; pointer-events:none; }
.settled .actions { top:4px; }
.card:hover .actions, .card.forced .actions, .card:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:grid; place-items:center; width:24px; height:22px; padding:0; border:0; border-radius:6px; background:transparent; color:var(--muted); }
.actions button:hover { color:var(--ink); background:var(--line); }
@keyframes eq { 50% { transform:scaleY(.5); } }
@keyframes pulse { 50% { opacity:.5; } }
</style>
