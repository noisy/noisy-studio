<script setup lang="ts">
import type { Utterance } from "../types";
import AgentBubble from "./AgentBubble.vue";
import UserBubble from "./UserBubble.vue";

withDefaults(defineProps<{ utterance: Utterance; playing?: boolean; paused?: boolean; tint?: "normal" | "green" | "purple" | "red"; label?: string }>(), {
  tint: "green",
  label: "",
  playing: false,
  paused: false,
});
defineEmits<{
  replay: [utterance: Utterance];
  cancel: [utterance: Utterance];
  pause: [utterance: Utterance];
  skip: [utterance: Utterance];
}>();

function sysTime(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  return [d.getHours(), d.getMinutes()].map((n) => String(n).padStart(2, "0")).join(":");
}
</script>

<template>
  <!-- System rows: small inline annotations (mic switched, …) that sit in
       the timeline so oddities right below them explain themselves —
       informative, never an alarm. -->
  <div v-if="utterance.role === 'system'" class="sysrow">
    <span>{{ utterance.text }}<template v-if="utterance.detail"> · {{ utterance.detail }}</template> · {{ sysTime(utterance.committed_at) }}</span>
  </div>
  <UserBubble
    v-else-if="utterance.role === 'user'"
    :utterance="utterance"
    @cancel="$emit('cancel', $event)"
  />
  <AgentBubble
    :tint="tint"
    :label="label"
    v-else
    :utterance="utterance"
    :playing="playing"
    :paused="paused"
    @replay="$emit('replay', $event)"
    @pause="$emit('pause', $event)"
    @skip="$emit('skip', $event)"
  />
</template>

<style scoped>
.sysrow {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  letter-spacing: normal;
  color: var(--muted);
  text-transform: none;
}
.sysrow::before,
.sysrow::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line), transparent);
}
</style>
