<script setup lang="ts">
// Stroke icons for the org tree; 16-unit grid, currentColor.
const PATHS = {
  snooze: "M8 4.2a4.8 4.8 0 1 0 0 9.6a4.8 4.8 0 1 0 0-9.6Z M8 6.6V9l1.7 1.1 M2.6 4.4 4.6 2.7 M13.4 4.4 11.4 2.7",
  settle: "M8 2.6a5.4 5.4 0 1 0 0 10.8a5.4 5.4 0 1 0 0-10.8Z M5.6 8.1l1.7 1.7 3.2-3.4",
  restore: "M6 3.5 3 6.5l3 3 M3 6.5h6.2a3.3 3.3 0 0 1 0 6.6H7.5",
  mic: "M8 2.4a2 2 0 0 0-2 2v3.4a2 2 0 0 0 4 0V4.4a2 2 0 0 0-2-2Z M4.6 7.6a3.4 3.4 0 0 0 6.8 0 M8 11v2.4",
  chevron: "M5 6.5l3 3 3-3",
  pause: "M6 4v8 M10 4v8",
  play: "M5.5 3.8v8.4l6.5-4.2Z",
  stop: "M4.5 4.5h7v7h-7Z",
  focus: "M8 2.5v2.4 M8 11.1v2.4 M2.5 8h2.4 M11.1 8h2.4 M8 5.2a2.8 2.8 0 1 0 0 5.6a2.8 2.8 0 1 0 0-5.6Z",
  review: "M1.8 8s2.3-4.2 6.2-4.2S14.2 8 14.2 8s-2.3 4.2-6.2 4.2S1.8 8 1.8 8Z M8 6.4a1.6 1.6 0 1 0 0 3.2a1.6 1.6 0 1 0 0-3.2Z",
  agents: "M5.5 4.2a1.7 1.7 0 1 0 0 3.4a1.7 1.7 0 1 0 0-3.4Z M10.8 5a1.4 1.4 0 1 0 0 2.8a1.4 1.4 0 1 0 0-2.8Z M2.4 12.4c.4-2 1.6-3 3.1-3s2.7 1 3.1 3 M8.9 10.2c.5-.6 1.1-.9 1.9-.9 1.3 0 2.2.8 2.6 2.4",
  cap: "M2.8 11a5.4 5.4 0 1 1 10.4 0 M8 10.2l2.6-3.4",
} as const;
export type LabIconName = keyof typeof PATHS;
defineProps<{ name: LabIconName; size?: number }>();
</script>

<template>
  <svg :width="size ?? 14" :height="size ?? 14" viewBox="0 0 16 16" fill="none" stroke="currentColor"
    stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="PATHS[name]" />
  </svg>
</template>
