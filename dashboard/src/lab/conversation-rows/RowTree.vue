<script setup lang="ts">
// Option C - Org tree: the manager is a tile + two lines; its delegated work
// hangs underneath as indented one-line children, always visible. Status
// lives on the tile (ring + corner badges) like presence on a chat avatar.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { cornerTime, hueOf, initialOf, type LabChild, type LabRow } from "./fixtures";

// Geometry knobs.
const MANAGER_PX = 48;
const CHILD_PX = 22;
const TILE_PX = 28;
// Children shown before the rest folds into "+N more"; done work folds first.
const VISIBLE_CHILDREN = 3;

const props = defineProps<{ row: LabRow }>();
defineEmits<{ snooze: [id: string]; settle: [id: string]; restore: [id: string] }>();

const settled = computed(() => props.row.section === "settled");
const ring = computed(() => (props.row.speaking ? "green" : props.row.working ? "violet" : null));
// Open work first, then finished; settled managers show no children.
const ordered = computed<LabChild[]>(() =>
  settled.value ? [] : [...props.row.children].sort((a, b) => Number(a.state === "done") - Number(b.state === "done")),
);
const shown = computed(() => ordered.value.slice(0, VISIBLE_CHILDREN));
const hidden = computed(() => ordered.value.length - shown.value.length);
const style = computed(() => ({
  "--manager": `${MANAGER_PX}px`, "--child": `${CHILD_PX}px`, "--tile": `${TILE_PX}px`,
  ...(hueOf(props.row) != null ? { "--hue": String(hueOf(props.row)) } : {}),
}));
const childRight = (child: LabChild) =>
  child.state === "review" ? "review" : child.state === "blocked" ? "blocked" : child.state === "done" ? "done" : child.progress ?? "";
</script>

<template>
  <div class="group" :style="style" :class="{ settled }">
    <div class="manager" tabindex="0" :class="{ viewing: row.viewed, forced: row.hover, working: row.working }">
      <span class="tile" :class="[ring && `ring-${ring}`, { legacy: !row.project }]">
        {{ initialOf(row) }}
        <span v-if="(row.queued ?? 0) > 0 && !row.muted" class="badge count">{{ row.queued }}</span>
        <span v-if="row.muted" class="badge mute" title="Muted">
          <svg viewBox="0 0 14 14"><path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" /><path d="M10 5 13 9 M13 5 10 9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
        </span>
        <span v-if="row.mic" class="badge mic" title="Receiving your speech"><LabIcon name="mic" :size="9" /></span>
      </span>
      <div class="text">
        <div class="l1">
          <span class="title clip">{{ row.title }}</span>
          <span class="time"><LabIcon v-if="row.snoozedUntil" name="snooze" :size="11" />{{ cornerTime(row) }}</span>
        </div>
        <div class="l2 clip">
          <span :class="{ none: !row.project }">{{ row.project ?? "No project" }}</span>
          <template v-if="row.working"> · <span class="activity">{{ row.activity }}</span></template>
          <template v-else-if="row.branch"> / <span class="branch">{{ row.branch }}</span></template>
        </div>
      </div>
      <div class="actions">
        <button v-if="settled" type="button" @click.stop="$emit('restore', row.id)"><LabIcon name="restore" :size="12" />Restore</button>
        <template v-else>
          <button type="button" @click.stop="$emit('snooze', row.id)"><LabIcon name="snooze" :size="12" />Snooze</button>
          <button type="button" @click.stop="$emit('settle', row.id)"><LabIcon name="settle" :size="12" />Settle</button>
        </template>
      </div>
    </div>
    <div v-for="child in shown" :key="child.id" class="child" :class="child.state" :title="`${child.title} · ${child.who}${child.note ? ' · ' + child.note : ''}`">
      <span class="cglyph">
        <span v-if="child.state === 'working'" class="spin" />
        <span v-else-if="child.state === 'blocked'">!</span>
        <span v-else-if="child.state === 'review'">●</span>
        <span v-else>✓</span>
      </span>
      <span class="ctitle clip">{{ child.title }}</span>
      <span class="cright">{{ childRight(child) }}</span>
    </div>
    <div v-if="hidden" class="child more"><span class="cglyph" /><span class="ctitle">+{{ hidden }} more</span></div>
  </div>
</template>

<style scoped>
.group { display:flex; flex-direction:column; }
.manager { position:relative; display:flex; align-items:center; gap:10px; height:var(--manager); padding:0 10px 0 8px; border:1px solid transparent; border-radius:8px; color:var(--ink); font:13px var(--sans); cursor:pointer; outline:none; }
.manager:hover, .manager.forced, .manager:focus-visible { background:var(--surface-hover); }
.manager.viewing { background:var(--surface-hover); border-color:var(--line-strong); }
.tile { position:relative; flex:none; width:var(--tile); height:var(--tile); border-radius:8px; font:600 13px/var(--tile) var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.tile.legacy { color:var(--muted); background:var(--line); }
.tile.ring-violet { box-shadow:0 0 0 2px var(--bg0), 0 0 0 4px var(--violet); animation:ring 1.6s ease-in-out infinite; }
.tile.ring-green { box-shadow:0 0 0 2px var(--bg0), 0 0 0 4px var(--green); }
.badge { position:absolute; display:grid; place-items:center; height:14px; min-width:14px; border-radius:7px; box-shadow:0 0 0 2px var(--bg0); font:700 9px/14px var(--sans); }
.badge.count { top:-5px; right:-6px; padding:0 3px; color:var(--bg0); background:var(--amber); }
.badge.mute { bottom:-5px; right:-6px; color:#fff; background:var(--red); }
.badge.mute svg { width:10px; height:10px; }
.badge.mic { bottom:-5px; left:-6px; color:var(--bg0); background:var(--green); }
.text { flex:1; min-width:0; display:flex; flex-direction:column; gap:1px; }
.l1 { display:flex; align-items:center; gap:6px; min-width:0; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.title { flex:1; font-weight:600; }
.working .title { color:color-mix(in srgb, var(--ink) 78%, var(--muted)); }
.time { flex:none; display:inline-flex; align-items:center; gap:3px; min-width:26px; justify-content:flex-end; font-size:11px; font-variant-numeric:tabular-nums; color:var(--muted); }
.l2 { font-size:11px; color:var(--muted); }
.l2 .none { font-style:italic; opacity:.7; }
.branch { font:10.5px var(--mono); }
.activity { color:var(--violet-dim); }
.settled .title, .settled .l2 { opacity:.6; }
.settled .tile { filter:grayscale(1); opacity:.6; }
/* Children: indented under the tile, joined by a tree line. */
.child { position:relative; display:flex; align-items:center; gap:6px; height:var(--child); margin-left:22px; padding:0 10px 0 16px; border-radius:6px; font:11.5px var(--sans); color:var(--muted); cursor:pointer; }
.child::before { content:""; position:absolute; left:0; top:0; bottom:0; border-left:1px solid var(--line-strong); }
.child:last-child::before { bottom:50%; }
.child::after { content:""; position:absolute; left:0; top:50%; width:10px; border-top:1px solid var(--line-strong); }
.child:hover { background:var(--surface-hover); color:var(--ink); }
.cglyph { flex:none; width:12px; text-align:center; font-size:10px; font-weight:700; }
.working .cglyph { color:var(--violet); }
.blocked .cglyph, .review .cglyph { color:var(--amber); }
.done .cglyph, .more .cglyph { color:var(--muted); opacity:.7; }
.spin { display:inline-block; width:8px; height:8px; border:1.5px solid color-mix(in srgb, var(--violet) 30%, transparent); border-top-color:var(--violet); border-radius:50%; animation:spin 1s linear infinite; }
.ctitle { flex:1; }
.done .ctitle, .more .ctitle { opacity:.7; }
.cright { flex:none; font-size:10.5px; font-variant-numeric:tabular-nums; }
.working .cright { color:var(--violet-dim); }
.blocked .cright, .review .cright { color:var(--amber); font-weight:600; }
.done .cright { opacity:.6; }
/* Over line 2 (project/branch), so the title and wait time stay readable. */
.actions { position:absolute; bottom:4px; right:6px; display:flex; gap:4px; padding-left:18px; background:linear-gradient(to right, transparent, var(--surface-hover) 18px); opacity:0; pointer-events:none; }
.manager:hover .actions, .manager.forced .actions, .manager:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:inline-flex; align-items:center; gap:4px; height:20px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); color:var(--ink); font:10.5px var(--sans); }
.actions button:hover { border-color:var(--muted); }
@keyframes ring { 50% { box-shadow:0 0 0 2px var(--bg0), 0 0 0 4px color-mix(in srgb, var(--violet) 45%, transparent); } }
@keyframes spin { to { transform:rotate(360deg); } }
</style>
