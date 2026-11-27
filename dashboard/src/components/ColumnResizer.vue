<script setup lang="ts">
/* The draggable edge between the conversation list and the conversation.
 * Drag, or focus it and use the arrow keys; double-click restores the
 * default. Pure input: the parent owns the width. */
import { COLUMN_WIDTH_LIMITS } from "../composables/useColumnWidth";

const props = defineProps<{ width: number }>();
const emit = defineEmits<{ resize: [px: number]; reset: [] }>();

function startDrag(event: PointerEvent) {
  const handle = event.currentTarget as HTMLElement;
  const startX = event.clientX;
  const startWidth = props.width;
  handle.setPointerCapture(event.pointerId);
  const move = (e: PointerEvent) => emit("resize", startWidth + e.clientX - startX);
  const stop = () => {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", stop);
    document.body.classList.remove("resizing-column");
  };
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", stop);
  document.body.classList.add("resizing-column");
}

function onKey(event: KeyboardEvent) {
  const delta = event.key === "ArrowLeft" ? -COLUMN_WIDTH_LIMITS.step : event.key === "ArrowRight" ? COLUMN_WIDTH_LIMITS.step : 0;
  if (!delta) return;
  event.preventDefault();
  emit("resize", props.width + delta);
}
</script>

<template>
  <div
    class="column-resizer"
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize the conversation list"
    :aria-valuenow="width"
    :aria-valuemin="COLUMN_WIDTH_LIMITS.min"
    :aria-valuemax="COLUMN_WIDTH_LIMITS.max"
    tabindex="0"
    title="Drag to resize · double-click to reset"
    @pointerdown.prevent="startDrag"
    @keydown="onKey"
    @dblclick="emit('reset')"
  />
</template>

<style scoped>
/* A wide invisible grab area centred on the gap; a thin line shows on hover. */
.column-resizer { position:absolute; top:0; bottom:0; left:calc(var(--left-column-width) + 2px); width:16px; cursor:col-resize; touch-action:none; z-index:2; }
.column-resizer::after { content:""; position:absolute; top:0; bottom:0; left:7px; width:2px; border-radius:1px; background:transparent; transition:background .12s; }
.column-resizer:hover::after, .column-resizer:focus-visible::after { background:var(--line-strong); }
.column-resizer:focus-visible { outline:none; }
</style>
