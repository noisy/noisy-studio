<script setup lang="ts">
import { computed } from "vue";
import { statusAllows } from "../machines/chat";
import type { Utterance } from "../types";
import Bubble from "./Bubble.vue";
import { formatCost, formatTime, statusChip } from "./bubbleStatus";

const props = defineProps<{ utterance: Utterance }>();
defineEmits<{ cancel: [utterance: Utterance] }>();

const chip = computed(() => statusChip(props.utterance.status, "user"));
const pending = computed(() => !props.utterance.text);
// Recall is offered exactly where the machine allows it: awaiting pickup.
const cancelable = computed(() => statusAllows("user", props.utterance.status, "CANCEL"));
</script>

<template>
  <Bubble
    side="left"
    accent="amber"
    who="YOU"
    :text="utterance.text || utterance.status"
    :status-kind="chip.kind"
    :status-label="chip.label"
    :time="formatTime(utterance.started_at)"
    :cost="formatCost(utterance.cost_usd)"
    :detail="[utterance.detail, utterance.delivery_detail].filter(Boolean).join(' · ')"
    :live="chip.kind === 'rec'"
    :pending="pending"
    :cancelable="cancelable"
    @cancel="$emit('cancel', utterance)"
  />
</template>
