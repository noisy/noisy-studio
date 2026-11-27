<script setup lang="ts">
// The one status glyph of options A and B. Always the same box, so a state
// change never moves the text beside it. Idle draws nothing.
import { computed } from "vue";
import { signalOf, type LabRow } from "./fixtures";

const props = defineProps<{ row: LabRow }>();
const signal = computed(() => signalOf(props.row));
</script>

<template>
  <span class="signal" :data-signal="signal ?? 'none'">
    <svg v-if="signal === 'muted'" class="mute" viewBox="0 0 14 14" aria-label="muted">
      <path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" />
      <path d="M10 5 13 9 M13 5 10 9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    </svg>
    <span v-else-if="signal === 'speaking'" class="eq" aria-label="speaking"><i /><i /><i /></span>
    <span v-else-if="signal === 'queued'" class="count" :aria-label="`${row.queued} waiting`">{{ row.queued }}</span>
    <span v-else-if="signal === 'working'" class="dots" aria-label="working"><i /><i /><i /></span>
  </span>
</template>

<style scoped>
.signal { flex:none; display:inline-flex; align-items:center; justify-content:flex-end; width:var(--signal-w, 22px); height:16px; }
.mute { width:14px; height:14px; color:var(--red); }
.eq { display:flex; gap:2px; align-items:center; height:12px; }
.eq i { width:2px; height:9px; border-radius:1px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:12px; animation-delay:.2s; }
.eq i:nth-child(3) { animation-delay:.4s; }
.count { min-width:18px; height:16px; padding:0 5px; border-radius:8px; font:600 10px/16px var(--sans); text-align:center; color:var(--bg0); background:var(--amber); }
.dots { display:flex; gap:3px; }
.dots i { width:4px; height:4px; border-radius:50%; background:var(--violet); animation:dot 1.4s ease-in-out infinite; }
.dots i:nth-child(2) { animation-delay:.2s; }
.dots i:nth-child(3) { animation-delay:.4s; }
@keyframes eq { 50% { transform:scaleY(.5); } }
@keyframes dot { 0%, 100% { opacity:.35; } 40% { opacity:1; } }
</style>
