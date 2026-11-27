<script setup lang="ts">
// Stroke icons for the lab rows; 16-unit grid, currentColor.
const PATHS = {
  snooze: "M8 4.2a4.8 4.8 0 1 0 0 9.6a4.8 4.8 0 1 0 0-9.6Z M8 6.6V9l1.7 1.1 M2.6 4.4 4.6 2.7 M13.4 4.4 11.4 2.7",
  settle: "M8 2.6a5.4 5.4 0 1 0 0 10.8a5.4 5.4 0 1 0 0-10.8Z M5.6 8.1l1.7 1.7 3.2-3.4",
  restore: "M6 3.5 3 6.5l3 3 M3 6.5h6.2a3.3 3.3 0 0 1 0 6.6H7.5",
  branch: "M5 4.9v6.2 M6.3 3.6a1.3 1.3 0 1 1-2.6 0a1.3 1.3 0 1 1 2.6 0Z M6.3 12.4a1.3 1.3 0 1 1-2.6 0a1.3 1.3 0 1 1 2.6 0Z M12.3 4.6a1.3 1.3 0 1 1-2.6 0a1.3 1.3 0 1 1 2.6 0Z M11 5.9c0 2.6-6 2.3-6 5.2",
  mic: "M8 2.4a2 2 0 0 0-2 2v3.4a2 2 0 0 0 4 0V4.4a2 2 0 0 0-2-2Z M4.6 7.6a3.4 3.4 0 0 0 6.8 0 M8 11v2.4",
  chevron: "M5 6.5l3 3 3-3",
  delegate: "M4 2.6v8.2a1.8 1.8 0 0 0 1.8 1.8h6.4 M4 5.8a1.8 1.8 0 0 0 1.8 1.8h6.4 M10.4 5.8l1.8 1.8-1.8 1.8 M10.4 10.8l1.8 1.8-1.8 1.8",
} as const;
defineProps<{ name: keyof typeof PATHS; size?: number }>();
</script>

<template>
  <svg :width="size ?? 14" :height="size ?? 14" viewBox="0 0 16 16" fill="none" stroke="currentColor"
    stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="PATHS[name]" />
  </svg>
</template>
