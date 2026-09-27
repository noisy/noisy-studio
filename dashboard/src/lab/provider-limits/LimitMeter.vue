<script setup lang="ts">
import type { LimitWindow } from './fixtures';
const props = defineProps<{ window: LimitWindow; amber: number; red: number }>();
function tone() { return props.window.state !== 'fresh' ? 'muted' : (props.window.used ?? 0) >= props.red ? 'red' : (props.window.used ?? 0) >= props.amber ? 'warning' : 'brand-accent'; }
</script>
<template>
  <div class="limit-meter" :style="{ '--meter-color': `var(--${tone()})` }">
    <div class="meter-heading"><span>{{ window.name }}</span><strong>{{ window.used === undefined ? (window.state === 'unsupported' ? 'Unavailable' : 'Unknown') : `${window.used}% used` }}<small v-if="window.state === 'stale'"> · last known</small></strong></div>
    <div class="meter-track" :class="{ unavailable: window.used === undefined, stale: window.state === 'stale' }" :role="window.used === undefined ? undefined : 'meter'" :aria-label="`${window.name} ${window.state === 'stale' ? 'last known ' : ''}usage`" :aria-valuenow="window.used" :aria-valuemin="0" :aria-valuemax="100"><i v-if="window.used !== undefined" :style="{ width: `${window.used}%` }" /></div>
    <div class="meter-meta"><span>{{ window.note }}</span><span v-if="window.state === 'fresh'">Resets in {{ window.reset }}</span><span v-else-if="window.state === 'stale'">Reset estimate in {{ window.reset }}</span><span v-else>Reset {{ window.reset.toLowerCase() }}</span></div>
  </div>
</template>
<style scoped>
.limit-meter{min-width:0}.meter-heading,.meter-meta{display:flex;justify-content:space-between;gap:12px}.meter-heading{font-size:13px;line-height:1.5}.meter-heading strong{color:var(--meter-color);white-space:nowrap;font-weight:600}.meter-heading small{font-size:11px}.meter-track{height:5px;border-radius:8px;background:var(--line);margin:9px 0}.meter-track i{display:block;height:100%;border-radius:inherit;background:var(--meter-color)}.meter-track.stale i{background:repeating-linear-gradient(110deg,var(--muted),var(--muted) 4px,var(--line) 4px,var(--line) 8px)}.meter-track.unavailable{background:repeating-linear-gradient(90deg,var(--line),var(--line) 4px,transparent 4px,transparent 8px)}.meter-meta{font-size:10px;color:var(--muted);line-height:1.5;flex-wrap:wrap}
</style>
