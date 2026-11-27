<script setup lang="ts">
// The snooze choices, as an overlay under the manager row: presets show the
// wake time they resolve to; Custom takes "45m", "2h", "14:30", "fri 9:00"
// or "tomorrow" and previews its wake time before you set it.
import { computed, ref } from "vue";
import { clockLabel } from "./orgModel";
import { parseSnooze, snoozePresets } from "./snooze";

const props = defineProps<{ now: number }>();
defineEmits<{ pick: [until: number] }>();

const presets = computed(() => snoozePresets(props.now));
const custom = ref("");
const customAt = computed(() => (custom.value.trim() ? parseSnooze(custom.value, props.now) : null));
</script>

<template>
  <div class="menu" role="menu" @click.stop>
    <div class="head">Snooze until…</div>
    <button v-for="preset in presets" :key="preset.label" type="button" role="menuitem" @click="$emit('pick', preset.at)">
      <span>{{ preset.label }}</span><span class="at">{{ clockLabel(preset.at, now) }}</span>
    </button>
    <div class="rule" />
    <form class="custom" @submit.prevent="customAt != null && $emit('pick', customAt)">
      <input v-model="custom" aria-label="Custom snooze" placeholder="45m, 2h, 14:30, fri 9:00" />
      <button type="submit" class="set" :disabled="customAt == null">Set</button>
    </form>
    <div class="preview" :class="{ bad: custom.trim() && customAt == null }">
      <template v-if="customAt != null">wakes {{ clockLabel(customAt, now) }}</template>
      <template v-else-if="custom.trim()">not a time I understand</template>
      <template v-else>Comes back early if it speaks to you.</template>
    </div>
  </div>
</template>

<style scoped>
.menu { width:220px; padding:6px; border:1px solid var(--line-strong); border-radius:10px; background:var(--panel-solid); box-shadow:0 10px 28px rgba(0,0,0,.35); font:12px var(--sans); color:var(--ink); box-sizing:border-box; }
.head { padding:4px 8px 6px; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
button[role="menuitem"] { display:flex; justify-content:space-between; width:100%; padding:6px 8px; border:0; border-radius:6px; background:transparent; color:var(--ink); font:inherit; text-align:left; cursor:pointer; }
button[role="menuitem"]:hover, button[role="menuitem"]:focus-visible { background:var(--surface-hover); outline:none; }
.at { color:var(--muted); font-variant-numeric:tabular-nums; }
.rule { height:1px; margin:5px 4px; background:var(--line); }
.custom { display:flex; gap:6px; padding:2px 4px; }
.custom input { flex:1; min-width:0; height:24px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--bg0); color:var(--ink); font:12px var(--sans); }
.set { flex:none; height:24px; padding:0 10px; border:0; border-radius:6px; background:var(--amber); color:var(--bg0); font:600 11px var(--sans); cursor:pointer; }
.set:disabled { opacity:.4; cursor:default; }
/* One fixed line: hint, preview and error swap without resizing the menu. */
.preview { height:16px; padding:5px 8px 2px; font-size:10.5px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.preview.bad { color:var(--red); }
</style>
