<script setup lang="ts">
import { computed } from "vue";
import { statusAllows, statusToState } from "../machines/chat";
import type { Utterance } from "../types";
import { conversationCard } from "../conversationCard";
import Bubble from "./Bubble.vue";
import { formatCost, formatTime } from "./bubbleStatus";

const props = defineProps<{ utterance: Utterance }>();
defineEmits<{ cancel: [utterance: Utterance] }>();

const card = computed(() => conversationCard(props.utterance));
const notice = computed(() => {
  const state = statusToState("user", props.utterance.status);
  if (state !== "unavailable") return "";
  const detail = props.utterance.delivery_detail || "";
  // Historical cards can contain developer-facing connection diagnostics.
  if (/registration|register|endpoint|socket|inbox|hook/i.test(detail)) {
    return "Open this conversation in your agent and type and send any message—for example, ‘hello’—to reconnect voice delivery. No special command is needed.";
  }
  return detail || "Open this conversation in your agent and type and send any message to reconnect voice delivery. No special command is needed.";
});
const pending = computed(() => !props.utterance.text);
// Recall is offered exactly where the machine allows it: awaiting pickup.
const cancelable = computed(() => statusAllows("user", props.utterance.status, "CANCEL"));
</script>

<template>
  <Bubble
    side="left"
    accent="amber"
    who="YOU"
    :text="card.text"
    :status-kind="card.statusKind"
    :status-label="card.statusLabel"
    :time="formatTime(utterance.started_at)"
    :cost="formatCost(utterance.cost_usd)"
    :notice="notice"
    :detail="[utterance.detail, notice ? '' : utterance.delivery_detail].filter(Boolean).join(' · ')"
    :live="card.statusKind === 'rec'"
    :pending="pending"
    :cancelable="cancelable"
    @cancel="$emit('cancel', utterance)"
  />
</template>
