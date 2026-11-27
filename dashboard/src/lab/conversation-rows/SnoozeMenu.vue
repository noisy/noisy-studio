<script setup lang="ts">
// The snooze choices, as an overlay: presets resolve to a visible wake
// time, Custom takes a duration or a date/time in one field.
import { ref } from "vue";

// The board's frozen clock is Friday 11:42; presets show their wake time.
const PRESETS = [
  { label: "1 hour", at: "12:42" },
  { label: "3 hours", at: "14:42" },
  { label: "This evening", at: "18:00" },
  { label: "Tomorrow morning", at: "Sat 09:00" },
];
const custom = ref("90m");
defineEmits<{ pick: [at: string] }>();
</script>

<template>
  <div class="menu" role="menu" @click.stop>
    <div class="head">Snooze until…</div>
    <button v-for="preset in PRESETS" :key="preset.label" type="button" role="menuitem" @click="$emit('pick', preset.at)">
      <span>{{ preset.label }}</span><span class="at">{{ preset.at }}</span>
    </button>
    <div class="rule" />
    <label class="custom">
      <span>Custom</span>
      <input v-model="custom" placeholder="45m, 2h, fri 9:00, 1 Dec 14:00" />
    </label>
    <div class="preview">→ wakes at <b>13:12</b> <button type="button" class="set" @click="$emit('pick', '13:12')">Set</button></div>
    <div class="foot">Comes back early if it speaks or queues a message.</div>
  </div>
</template>

<style scoped>
.menu { width:224px; padding:6px; border:1px solid var(--line-strong); border-radius:10px; background:var(--panel-solid); box-shadow:0 10px 28px rgba(0,0,0,.35); font:12px var(--sans); color:var(--ink); }
.head { padding:4px 8px 6px; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
button[role="menuitem"] { display:flex; justify-content:space-between; width:100%; padding:6px 8px; border:0; border-radius:6px; background:transparent; color:var(--ink); text-align:left; }
button[role="menuitem"]:hover, button[role="menuitem"]:first-of-type { background:var(--surface-hover); }
.at { color:var(--muted); font-variant-numeric:tabular-nums; }
.rule { height:1px; margin:5px 4px; background:var(--line); }
.custom { display:flex; align-items:center; gap:8px; padding:4px 8px; }
.custom input { flex:1; min-width:0; height:24px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--bg0); color:var(--ink); font:12px var(--sans); }
.preview { display:flex; align-items:center; gap:4px; padding:4px 8px; color:var(--muted); }
.preview b { color:var(--ink); font-weight:600; }
.set { margin-left:auto; height:22px; padding:0 10px; border:0; border-radius:6px; background:var(--amber); color:var(--bg0); font:600 11px var(--sans); }
.foot { padding:6px 8px 2px; font-size:10.5px; color:var(--muted); opacity:.8; }
</style>
