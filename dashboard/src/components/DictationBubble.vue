<script setup lang="ts">
/* The live dictation bubble (dictate anywhere), shown by the desktop shell
 * next to the text cursor while a dictation records.
 *
 * Presentational: the words and the phase come in as props. The shell's
 * window has a fixed size, so the bubble fills its width at most, grows
 * with the words up to the window's height, then scrolls - always pinned
 * to the newest words. `placement` says which side of the cursor the
 * window opened on: "below" hangs the bubble from the top edge, "above"
 * stands it on the bottom edge, so it always touches the cursor's line. */
import { computed, nextTick, onMounted, ref, watch } from "vue";
import type { DictationPhase } from "./dictationOverlay";

const PAD_PX = 10;
const RADIUS_PX = 12;
const LABEL_SLOT_PX = 76; // fits the longest label, so a phase change never shifts the row
const SHADOW_ROOM_PX = 6;  // the window clips at its edges; leave the shadow room to show

const props = withDefaults(
  defineProps<{ text: string; phase: DictationPhase; placement?: "below" | "above" }>(),
  { placement: "below" },
);

const LABELS: Record<DictationPhase, string> = {
  listening: "Listening",
  inserting: "Pasting…",
  inserted: "Pasted",
  failed: "Not pasted",
};
const label = computed(() => LABELS[props.phase]);
const geometry = {
  "--pad": `${PAD_PX}px`, "--radius": `${RADIUS_PX}px`,
  "--label-slot": `${LABEL_SLOT_PX}px`, "--shadow-room": `${SHADOW_ROOM_PX}px`,
};

const body = ref<HTMLElement | null>(null);
const pinToNewest = async () => {
  await nextTick();
  if (body.value) body.value.scrollTop = body.value.scrollHeight;
};
watch(() => props.text, pinToNewest);
onMounted(pinToNewest);
</script>

<template>
  <div class="dictation-frame" :class="placement" :style="geometry">
    <section class="bubble" :class="phase" role="status" aria-live="polite">
      <header class="head">
        <span class="dot" aria-hidden="true"></span>
        <span class="label">{{ label }}</span>
      </header>
      <p ref="body" class="words">
        <template v-if="text">{{ text }}</template>
        <span v-else class="hint">Speak, then press the key again to paste.</span>
      </p>
    </section>
  </div>
</template>

<style scoped>
.dictation-frame { display: flex; flex-direction: column; height: 100%; min-height: 0; padding: var(--shadow-room); box-sizing: border-box; font-family: var(--sans); }
.dictation-frame.below { justify-content: flex-start; }
.dictation-frame.above { justify-content: flex-end; }
.bubble { display: flex; flex-direction: column; gap: 6px; max-width: 100%; max-height: 100%; min-height: 0; width: fit-content; min-width: 180px;
  box-sizing: border-box; padding: var(--pad); border-radius: var(--radius); border: 1px solid var(--line-strong);
  background: var(--panel-solid); color: var(--ink); box-shadow: 0 4px 14px #0006; }
.head { display: flex; align-items: center; gap: 6px; flex: none; font-size: 10px; letter-spacing: .04em; text-transform: uppercase; }
.dot { width: 7px; height: 7px; border-radius: 50%; flex: none; background: var(--cyan); }
.label { min-width: var(--label-slot); color: var(--cyan); }
/* Only the label and the dot pulse; the plate stays solid. */
.listening .dot, .listening .label { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .5; } }
.inserting .dot { background: var(--cyan-dim); }
.inserting .label { color: var(--muted); }
.inserted .dot { background: var(--green); }
.inserted .label { color: var(--green); }
.failed .dot { background: var(--red); }
.failed .label { color: var(--red); }
.words { margin: 0; min-height: 0; overflow-y: auto; font-size: 14px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; scrollbar-width: thin; }
.hint { color: var(--muted); }
</style>
