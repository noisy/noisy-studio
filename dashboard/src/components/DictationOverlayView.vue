<script setup lang="ts">
/* /dictate - the page inside the desktop shell's dictation window.
 *
 * Fed by the daemon's state stream (pushed on every change, so the words
 * follow the live transcription), with no polling and nothing else: the
 * window exists for a few seconds at a time. The shell decides where the
 * window goes and tells the page which side of the cursor it is on through
 * the URL hash (#below / #above). */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { openStateStream, type StateSnapshot, type StreamHandle } from "../api/stateStream";
import DictationBubble from "./DictationBubble.vue";
import { dictationView } from "./dictationOverlay";

const snapshot = ref<StateSnapshot | null>(null);
const view = computed(() => dictationView(snapshot.value?.status ?? null, snapshot.value?.utterances ?? []));

const placementFromHash = () => (window.location.hash === "#above" ? "above" : "below");
const placement = ref<"below" | "above">(placementFromHash());
const onHash = () => (placement.value = placementFromHash());

let stream: StreamHandle | null = null;
onMounted(() => {
  // The window is transparent; only the bubble paints.
  document.body.classList.add("dictation-overlay");
  window.addEventListener("hashchange", onHash);
  stream = openStateStream((next) => (snapshot.value = next), () => {});
});
onUnmounted(() => {
  window.removeEventListener("hashchange", onHash);
  stream?.close();
});
</script>

<template>
  <DictationBubble :text="view.text" :phase="view.phase" :placement="placement" />
</template>

<style>
html:has(body.dictation-overlay), body.dictation-overlay, body.dictation-overlay #app { background: transparent; }
</style>
