<script setup lang="ts">
import { computed } from "vue";
import type { DaemonStatus, Utterance } from "../../types";
import { conversationLabel } from "../../conversationLabel";
import { orderAgents } from "../agentOrder";
import { useTaskProgress } from "../../composables/useTaskProgress";
import { readyForReview } from "./types";
import ThreadProgress from "./ThreadProgress.vue";
import ReviewItem from "./ReviewItem.vue";
const props = defineProps<{
  agent?: string;
  status: DaemonStatus | null;
  offline: boolean;
  utterances: Utterance[];
}>();
defineEmits<{
  reviewOpen: [open: boolean];
  startPtt: [];
  stopPtt: [];
}>();
const { snapshot, error, refresh } = useTaskProgress();
const threads = computed(() =>
  orderAgents(
    props.agent ? [props.agent] : Object.keys(props.status?.agent_labels ?? {}),
    props.status?.agents_meta,
  ).map((agent) => ({
    agent,
    label: conversationLabel(props.status?.agent_labels[agent], agent),
    tasks: Object.values(snapshot.value.threads[agent] ?? {}),
  })),
);
const ready = computed(() =>
  threads.value.flatMap((thread) =>
    thread.tasks.filter(readyForReview).map((task) => ({ thread, task })),
  ),
);
</script>
<template>
  <section class="task-panel live-task-progress" :class="{ scoped: agent }" :aria-label="agent ? 'Conversation progress' : 'Ready for review'">
    <header v-if="!agent || ready.length">
      <h2>Ready for review</h2>
      <span v-if="!agent">{{ ready.length }}</span>
    </header>
    <p v-if="error" role="status" class="quiet">
      {{ error }} <button @click="refresh">Retry</button>
    </p>
    <p v-else-if="!agent && !ready.length" class="quiet">
      No results waiting for review.
    </p>
    <div class="ready-list">
      <ReviewItem v-for="result in ready"
        :key="JSON.stringify([result.thread.agent, result.task.report.task_id, result.task.report.revision])"
        :agent="result.thread.agent" :task="result.task" :offline="offline"
        :thread-label="agent ? undefined : result.thread.label" @reviewed="refresh" />
    </div>
    <ThreadProgress v-if="agent" :tasks="Object.values(snapshot.threads[agent] ?? {})" />
  </section>
</template>
<style scoped>
.task-panel {
  padding: 8px 12px;
  border: 1px solid var(--line, #363a43);
  border-radius: 8px;
  color: var(--ink, #e4e7ee);
  background: var(--panel, #202329);
  font: 11px var(--sans, system-ui);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 9px;
}
h2 {
  font-size: 11px;
  margin: 0;
}
header > span,
a,
button {
  color: var(--brand-accent, #a8c8ef);
}
a { text-decoration:none; font-size:9px; white-space:nowrap; }
button {
  border: 0;
  background: none;
  font: inherit;
  font-size: 9px;
  cursor: pointer;
  padding: 3px;
  white-space: nowrap;
}
.quiet {
  font-size: 9px;
  line-height: 1.5;
  color: var(--muted, #9ba5b5);
}
small {
  font-size: 8px;
  color: var(--muted, #9ba5b5);
}
.ready-list {
  max-height: 180px;
  overflow: auto;
}
.scoped {
  padding:0 0 12px;
  border:0;
  border-bottom:1px solid var(--line);
  border-radius:0;
  background:none;
  margin-bottom:12px;
  min-width:0;
}
.scoped .ready-list { max-height:none; overflow:visible; }
button:focus-visible {
  outline: 2px solid var(--brand-accent, #a8c8ef);
  outline-offset: 2px;
}
</style>
