<script setup lang="ts">
import { computed } from "vue";
import { statusAllows } from "../machines/chat";
import type { Utterance } from "../types";
import Bubble from "./Bubble.vue";
import { formatCost, formatTime, statusChip } from "./bubbleStatus";

const props = withDefaults(
  defineProps<{ utterance: Utterance; playing?: boolean; paused?: boolean;
    /** Palette color for this speaker's bubbles (from status.speaker_colors).
     *  "normal" renders the main agent's own look, no guest surface. */
    tint?: "normal" | "green" | "purple" | "red";
    /** Free bubble title (from status.speaker_labels); overrides the
     *  default speaker + agent header. */
    label?: string }>(),
  { playing: false, paused: false, tint: "green", label: "" },
);
defineEmits<{ replay: [utterance: Utterance]; pause: [utterance: Utterance]; skip: [utterance: Utterance] }>();

const chip = computed(() => statusChip(props.utterance.status, "claude"));
const pending = computed(() => !props.utterance.text);
// The daemon speaks for itself sometimes (setup confirmations) — same
// pipeline, but the bubble must never attribute those words to Claude.
const fromDaemon = computed(() => props.utterance.role === "daemon");
// A subagent's speech (#22) stays in the parent conversation but is never
// attributed to the main agent: its own name, its own accent.
const speaker = computed(() => (props.utterance.speaker || "").trim());
const who = computed(() => {
  if (fromDaemon.value) return "NOISY STUDIO";
  if (speaker.value && props.label) return props.label.toUpperCase();
  const agent = (props.utterance.agent_label?.trim() || "Agent").toUpperCase();
  if (speaker.value) return `${speaker.value.toUpperCase()} · ${agent}`;
  return agent;
});
// Amber is reserved for the USER's side of the dialogue — a subagent stays
// in Claude's violet family and is distinguished by the header + avatar.
const accent = computed(() => (fromDaemon.value ? ("cyan" as const) : ("violet" as const)));
// Replay = re-entering synthesis; the machine knows which cards allow that
// (played or parked UNHEARD — mid-synthesis re-queues on its own, an
// errored card has nothing worth repeating).
const replayable = computed(
  () => statusAllows("claude", props.utterance.status, "REPLAY") && !!props.utterance.text,
);
</script>

<template>
  <Bubble
    side="right"
    :accent="accent"
    :who="who"
    :voice="utterance.voice"
    :text="utterance.text || 'rendering voice response…'"
    :status-kind="chip.kind"
    :status-label="chip.label"
    :time="formatTime(utterance.started_at)"
    :cost="formatCost(utterance.cost_usd)"
    :detail="utterance.detail"
    :pending="pending"
    :replayable="replayable"
    :playing="playing"
    :paused="paused"
    :variant="speaker && !fromDaemon && tint !== 'normal' ? 'guest' : 'agent'"
    :tint="tint === 'normal' ? 'green' : tint"
    @replay="$emit('replay', utterance)"
    @pause="$emit('pause', utterance)"
    @skip="$emit('skip', utterance)"
  />
</template>
