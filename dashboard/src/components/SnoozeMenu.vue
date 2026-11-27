<script setup lang="ts">
// The snooze choices for one conversation, each with the time it comes
// back. The caller places the menu (it overlays, never pushes) and closes it.
import { computed } from "vue";
import { snoozeOptions, wakeLabel } from "./snoozeTimes";

const props = defineProps<{ now: number }>(); // epoch s: when the menu opened
defineEmits<{ pick: [until: number] }>();

const options = computed(() => {
  const now = new Date(props.now * 1000);
  return snoozeOptions(now).map((option) => ({ ...option, wake: wakeLabel(option.until, now) }));
});
</script>

<template>
  <div class="snooze-menu" role="menu" aria-label="Snooze until">
    <p class="snooze-title">Snooze until</p>
    <button
      v-for="option in options" :key="option.label"
      type="button" role="menuitem" class="snooze-item" @click="$emit('pick', option.until)"
    ><span>{{ option.label }}</span><time>{{ option.wake }}</time></button>
  </div>
</template>

<style scoped>
.snooze-menu { min-width:170px; padding:6px; display:flex; flex-direction:column; gap:2px; background:var(--panel-solid); border:1px solid var(--line-strong); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.35); }
.snooze-title { margin:2px 6px 4px; font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
.snooze-item { display:flex; justify-content:space-between; gap:12px; padding:4px 6px; border:0; border-radius:6px; background:none; color:var(--ink); font:11px/16px var(--sans); text-align:left; cursor:pointer; }
.snooze-item:hover, .snooze-item:focus-visible { background:var(--surface-hover); }
.snooze-item time { color:var(--muted); font-variant-numeric:tabular-nums; }
</style>
