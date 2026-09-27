<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(
  defineProps<{ weekly?: boolean; lastUsed?: number }>(),
  { weekly: false, lastUsed: 76 },
);
// Illustrative five-minute samples: nulls represent collection gaps, never zero usage.
const samples = [
  12,
  12,
  18,
  21,
  21,
  28,
  32,
  32,
  41,
  47,
  53,
  61,
  72,
  83,
  92,
  null,
  4,
  7,
  12,
  18,
  18,
  null,
  null,
  null,
  33,
  40,
  46,
  49,
  55,
  61,
  68,
  76,
  null,
  null,
  null,
];
const segments = computed(() => {
  const result: string[] = [];
  let current: string[] = [];
  samples.forEach((used, index) => {
    if (used === null) {
      if (current.length) result.push(current.join(" "));
      current = [];
    } else
      current.push(
        `${44 + index * 19},${190 - (index >= 16 ? (used * props.lastUsed) / 76 : used) * 1.55}`,
      );
  });
  if (current.length) result.push(current.join(" "));
  return result;
});
</script>
<template>
  <div class="history-chart">
    <svg
      viewBox="0 0 720 235"
      role="img"
      :aria-label="
        weekly
          ? 'Illustrative weekly used quota history, with a reset and missing samples'
          : 'Illustrative five-hour used quota history, with a reset and missing samples'
      "
    >
      <g class="grid">
        <line
          v-for="y in [35, 112, 190]"
          :key="y"
          x1="44"
          :y1="y"
          x2="690"
          :y2="y"
        />
      </g>
      <g class="axis">
        <text x="3" y="39">100%</text>
        <text x="8" y="116">50%</text>
        <text x="16" y="194">0%</text>
        <text x="44" y="222">09:00</text>
        <text x="240" y="222">09:50</text>
        <text x="470" y="222">10:50</text>
        <text x="647" y="222">11:50</text>
      </g>
      <rect x="432" y="35" width="63" height="155" class="gap" />
      <text x="440" y="56" class="annotation">No data</text>
      <rect x="642" y="35" width="48" height="155" class="gap" />
      <text x="645" y="79" class="annotation">Stale</text>
      <line x1="338" y1="25" x2="338" y2="190" class="reset" />
      <text x="345" y="26" class="annotation">Window reset</text>
      <polyline
        v-for="(segment, index) in segments"
        :key="index"
        :points="segment"
        class="trace"
      />
    </svg>
    <p>
      Example samples every 5 minutes · gaps stay
      empty · resets start a new window
    </p>
  </div>
</template>
<style scoped>
.history-chart svg {
  width: 100%;
  display: block;
  min-height: 180px;
}
.grid {
  stroke: var(--line);
  stroke-width: 1;
}
.axis,
.annotation {
  fill: var(--muted);
  font: 10px var(--mono);
}
.trace {
  fill: none;
  stroke: var(--brand-accent);
  stroke-width: 2.5;
  stroke-linejoin: round;
}
.gap {
  fill: var(--surface-hover);
}
.reset {
  stroke: var(--warning);
  stroke-dasharray: 4 4;
}
.history-chart p {
  color: var(--muted);
  font-size: 11px;
  margin-top: 4px;
}
</style>
