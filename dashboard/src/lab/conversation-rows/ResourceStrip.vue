<script setup lang="ts">
// A project's resources in one 14 px line: what runs on the machine, and
// how much of the plan's window the project used today (with its cap as a
// tick). Over the cap the meter turns amber: a decision waits for you.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { isOverCap, percent, type ProjectUsage } from "./orgModel";

// Geometry knobs.
const METER_PX = 44;
const RUNNING_SLOT_PX = 74;

const props = defineProps<{ running: number; usage: ProjectUsage | null }>();

const over = computed(() => isOverCap(props.usage));
// "Claude · 5 h" -> "5h": the strip names only the window's length.
const windowShort = computed(() => props.usage?.window.split("·").pop()!.replace(/\s/g, "") ?? "");
const fill = computed(() => Math.min(1, props.usage?.share ?? 0));
const usageTitle = computed(() => {
  const usage = props.usage;
  if (!usage) return "No usage data for this project";
  const cap = usage.cap != null ? `, cap ${percent(usage.cap)}` : "";
  return `${percent(usage.share)} of the ${usage.window} window today${cap}`;
});
</script>

<template>
  <div class="strip" :style="{ '--meter': `${METER_PX}px`, '--running-slot': `${RUNNING_SLOT_PX}px` }">
    <span class="running" :class="{ busy: running > 0 }" :title="`${running} agents running`">
      <LabIcon name="agents" :size="11" />{{ running > 0 ? `${running} running` : "idle" }}
    </span>
    <span v-if="usage" class="usage" :class="{ over }" :title="usageTitle">
      <span class="meter">
        <span class="fill" :style="{ width: `${fill * 100}%` }" />
        <span v-if="usage.cap != null" class="cap" :style="{ left: `${usage.cap * 100}%` }" />
      </span>
      <span class="share">{{ percent(usage.share) }}</span><span class="window">{{ over ? "over cap" : `of ${windowShort}` }}</span>
    </span>
    <span v-else class="usage none" :title="usageTitle">no usage data</span>
  </div>
</template>

<style scoped>
.strip { display:flex; align-items:center; gap:10px; height:14px; font:10.5px var(--sans); color:var(--muted); font-variant-numeric:tabular-nums; }
.running { flex:none; display:inline-flex; align-items:center; gap:4px; min-width:var(--running-slot); }
.running.busy { color:var(--violet-dim); }
.usage { display:inline-flex; align-items:center; gap:5px; }
.meter { position:relative; flex:none; width:var(--meter); height:4px; border-radius:2px; background:var(--line); }
.fill { position:absolute; inset:0 auto 0 0; border-radius:2px; background:var(--muted); }
.cap { position:absolute; top:-2px; width:1px; height:8px; background:var(--ink); }
.share { min-width:3ch; text-align:right; color:var(--ink); }
.over .fill { background:var(--amber); }
.over .share, .over .window { color:var(--amber); font-weight:600; }
.none { font-style:italic; opacity:.7; }
</style>
