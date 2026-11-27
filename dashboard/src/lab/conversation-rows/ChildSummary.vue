<script setup lang="ts">
// Delegated work in one line: "2 running · 1 to review". The parts that
// need you are amber; running work is violet; finished work is quiet.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import type { ChildState, LabChild } from "./fixtures";

const props = defineProps<{ children: LabChild[] }>();
const LABELS: [ChildState, string][] = [["working", "running"], ["blocked", "blocked"], ["review", "to review"], ["done", "done"]];
const parts = computed(() =>
  LABELS.map(([state, label]) => ({ state, count: props.children.filter((child) => child.state === state).length, label }))
    .filter((part) => part.count > 0),
);
</script>

<template>
  <span class="summary">
    <LabIcon name="delegate" :size="11" />
    <span class="clip">
      <template v-for="(part, index) in parts" :key="part.state">
        <span v-if="index" class="sep"> · </span><span :class="part.state">{{ part.count }} {{ part.label }}</span>
      </template>
    </span>
  </span>
</template>

<style scoped>
.summary { display:flex; align-items:center; gap:5px; min-width:0; font:11px var(--sans); color:var(--muted); }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.working { color:var(--violet-dim); }
.blocked, .review { color:var(--amber); font-weight:600; }
.done { opacity:.75; }
.sep { opacity:.6; }
</style>
