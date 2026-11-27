<script setup lang="ts">
// Header controls for sound in both directions (option C, picked
// 2026-11-27): YOU · INPUT holds the live mic meter and ONE mic slot,
// AGENTS · OUTPUT holds mute-all. The frames say which way sound goes, so
// two red mutes side by side cannot be confused.
//
// The mic slot's job follows the turn mode: Auto -> Mute mic; Push to talk
// -> Hold to talk (muting means nothing there: nothing is captured unless
// you hold). A mute left over from Auto shows in the same slot as "Mic
// muted" and a click unmutes, so it is never a dead end.
import { computed } from "vue";
import Oscilloscope from "./Oscilloscope.vue";
import type { DaemonStatus } from "../types";

const props = defineProps<{ status: DaemonStatus | null; offline: boolean; level: number }>();
const emit = defineEmits<{ toggleMute: []; toggleAgentsMute: []; pttStart: []; pttStop: [] }>();

// Geometry knobs. Each button keeps one width in every state, so a mode or
// mute change never moves its neighbours (the fixed-slot rule).
const METER_PX = 84;
const MIC_SLOT_PX = 136;
const AGENTS_SLOT_PX = 148;

type MicSlot = "offline" | "muted" | "mute" | "talk" | "held";
const ptt = computed(() => props.status?.detection_mode === "ptt");
const slot = computed<MicSlot>(() => {
  if (props.offline) return "offline";
  if (props.status?.muted) return "muted";
  if (!ptt.value) return "mute";
  return props.status?.ptt_held ? "held" : "talk";
});
const toggleKey = computed(() => props.status?.ptt_toggle_key?.toUpperCase() ?? "");
const micLabel = computed(() => ({ offline: "Mic offline", muted: "Mic muted", mute: "Mute mic", talk: "Hold to talk", held: "◉ On air" })[slot.value]);
const micHint = computed(() => ({
  offline: "Waiting for the voice service",
  muted: "Microphone muted - click to unmute",
  mute: "Listening - click to pause",
  talk: "Hold here, or hold Space",
  held: toggleKey.value ? `Live - ${toggleKey.value} or tap here to end` : "Release to send",
})[slot.value]);
const agentsMuted = computed(() => !!props.status?.voice_muted);
const meterLevel = computed(() => (props.offline || props.status?.muted ? 0 : props.level));

// One button, two behaviours: a click toggles the mute; in push to talk a
// press holds the mic open until release (pointer capture keeps it held
// even when the pointer slides off).
const holds = computed(() => slot.value === "talk" || slot.value === "held");
function onClick() {
  if (!holds.value) emit("toggleMute");
}
function onPointerDown(event: PointerEvent) {
  if (!holds.value) return;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  emit("pttStart");
}
// Release ALWAYS ends a hold, even if the slot changed under the finger
// (mic muted, mode switched): a swallowed release would leave the mic open
// while the parent keeps renewing the hold. Stopping is idempotent.
function onPointerUp() {
  emit("pttStop");
}
</script>

<template>
  <div class="voice" :style="{ '--meter': METER_PX + 'px', '--mic-slot': MIC_SLOT_PX + 'px', '--agents-slot': AGENTS_SLOT_PX + 'px' }">
    <fieldset class="group">
      <legend>You · input</legend>
      <span class="meter" aria-hidden="true"><Oscilloscope :level="meterLevel" /></span>
      <button
        type="button"
        class="slot mic"
        :class="slot"
        :disabled="offline"
        :aria-pressed="slot === 'muted' || slot === 'held'"
        :title="micHint"
        @click="onClick"
        @pointerdown="onPointerDown"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      ><span class="slot-label">{{ micLabel }}</span></button>
    </fieldset>
    <fieldset class="group">
      <legend>Agents · output</legend>
      <button
        type="button"
        class="slot agents"
        :class="{ muted: agentsMuted }"
        :disabled="offline"
        :aria-pressed="agentsMuted"
        :title="agentsMuted ? 'Agents muted - click to resume playback' : 'Mute playback and keep replies for later'"
        @click="emit('toggleAgentsMute')"
      ><span class="slot-label">{{ agentsMuted ? "Agents muted" : "Mute all agents" }}</span></button>
    </fieldset>
  </div>
</template>

<style scoped>
.voice { display:flex; align-items:center; gap:8px; }
.group { display:flex; align-items:center; gap:6px; margin:0; padding:2px 6px 6px; border:1px solid var(--line); border-radius:10px; min-width:0; }
legend { padding:0 4px; font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.meter { width:var(--meter); height:30px; flex:none; }
.meter :deep(canvas) { height:100%; min-height:0; }
.slot { height:40px; padding:0 12px; font:500 13px var(--sans); color:var(--ink); background:var(--surface-hover); border:1px solid var(--line-strong); white-space:nowrap; }
.slot:hover:not(:disabled) { border-color:var(--cyan); }
.mic { width:var(--mic-slot); }
.agents { width:var(--agents-slot); }
.slot-label { font-weight:600; }
/* Red = muting, amber = on air: the dashboard's colour meanings. Only the
   label pulses, on the shared mute cadence. */
.muted { color:var(--red); border-color:var(--red); }
.muted .slot-label { animation:mute-blink 1.6s step-end infinite; }
.held { color:var(--amber); border-color:var(--amber); }
.talk, .held { touch-action:none; user-select:none; }
@keyframes mute-blink { 50% { opacity:.55; } }
@media (max-width:760px) { .meter { display:none; } }
/* Phone width: the groups share the row and the buttons fill them. Widths
   still never depend on state, so nothing moves on a mute. */
@media (max-width:600px) { .voice { flex:1 1 100%; } .group { flex:1; } .slot { width:100%; } }
</style>
