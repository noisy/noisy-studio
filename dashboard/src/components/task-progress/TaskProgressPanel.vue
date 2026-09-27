<script setup lang="ts">
import { computed, onBeforeUnmount } from "vue";
import type { DaemonStatus, Utterance } from "../../types";
import { conversationLabel } from "../../conversationLabel";
import { orderAgents } from "../agentOrder";
import { useTaskProgress } from "../../composables/useTaskProgress";
import { readyForReview } from "./types";
import TaskTitle from "./TaskTitle.vue";
import TaskReview from "./TaskReview.vue";
import type { ReviewTarget } from "./types";
import { ref } from "vue";
const props = defineProps<{
  status: DaemonStatus | null;
  offline: boolean;
  utterances: Utterance[];
}>();
const emit = defineEmits<{
  reviewOpen: [open: boolean];
  startPtt: [];
  stopPtt: [];
}>();
const { snapshot, error, refresh } = useTaskProgress();
const selected = ref<ReviewTarget | null>(null);
onBeforeUnmount(() => { emit("stopPtt"); emit("reviewOpen", false); });
const threads = computed(() =>
  orderAgents(
    Object.keys(props.status?.agent_labels ?? {}),
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
function open(target: ReviewTarget) {
  emit("stopPtt");
  selected.value = target;
  emit("reviewOpen", true);
}
function close() {
  emit("stopPtt");
  selected.value = null;
  emit("reviewOpen", false);
}
</script>
<template>
  <section class="task-panel live-task-progress" aria-label="Task progress">
    <header>
      <h2>Ready for review</h2>
      <span>{{ ready.length }}</span>
    </header>
    <p v-if="error" role="status" class="quiet">
      {{ error }} <button @click="refresh">Retry</button>
    </p>
    <p v-else-if="!ready.length" class="quiet">
      No results waiting for review.
    </p>
    <div class="ready-list">
      <article
        v-for="result in ready"
        :key="result.thread.agent + result.task.report.task_id"
      >
        <div>
          <TaskTitle :text="result.task.report.title" /><small>{{
            result.thread.label
          }}</small>
        </div>
        <button
          @click="open({ agent: result.thread.agent, task: result.task })"
          :aria-label="result.task.report.review?.label"
        >
          Review ↗
        </button>
      </article>
    </div>
    <header class="work-heading"><h2>Work by thread</h2></header>
    <div class="thread-list" tabindex="0" aria-label="Thread work">
      <p v-if="!threads.length" class="quiet">
        Open an agent conversation to see its reported tasks.
      </p>
      <section v-for="thread in threads" :key="thread.agent" class="thread">
        <h3>{{ thread.label }}</h3>
        <p v-if="!thread.tasks.length" class="quiet">No task info reported.</p>
        <div
          v-for="task in thread.tasks"
          :key="task.report.task_id"
          class="work-item"
        >
          <div class="work-title">
            <TaskTitle :text="task.report.title" /><button
              v-if="task.report.review"
              @click="open({ agent: thread.agent, task })"
              :aria-label="task.report.review.label"
            >
              ↗
            </button>
          </div>
          <div class="work-meta">
            <span :class="task.report.state">{{
              task.review_state === "approved"
                ? "approved"
                : task.stale
                  ? "Update overdue"
                  : task.report.state
            }}</span>
            <div
              v-if="task.report.total"
              class="track"
              :aria-label="
                task.report.completed +
                ' of ' +
                task.report.total +
                ' steps complete'
              "
            >
              <i
                :style="{
                  width:
                    ((task.report.completed ?? 0) / task.report.total) * 100 +
                    '%',
                }"
              />
            </div>
            <small v-else>Steps not reported</small>
          </div>
          <small class="agent-metadata"
            >{{
              task.report.role ??
              (task.report.participant ? "Delegated agent" : "Main agent")
            }}
            · {{ task.report.model ?? "Model not reported" }}</small
          >
        </div>
      </section>
    </div>
    <TaskReview
      v-if="selected"
      :target="selected"
      :status="status"
      :offline="offline"
      :utterances="utterances"
      @close="close"
      @reviewed="refresh"
      @start-ptt="emit('startPtt')"
      @stop-ptt="emit('stopPtt')"
    />
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
button {
  color: var(--brand-accent, #a8c8ef);
}
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
.ready-list article {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 0;
  border-top: 1px solid #77839b22;
}
.ready-list article > div {
  min-width: 0;
  flex: 1;
}
.ready-list small {
  display: block;
  margin-top: 3px;
}
.work-heading {
  border-top: 1px solid #77839b44;
  margin-top: 9px;
  padding-top: 13px;
}
.thread-list {
  max-height: 320px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.thread {
  margin-bottom: 13px;
}
h3 {
  font-size: 10px;
  margin: 0 0 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.work-item {
  border-left: 1px solid #77839b44;
  padding: 7px 0 6px 8px;
  margin-left: 3px;
}
.work-title {
  display: flex;
  align-items: center;
  gap: 4px;
}
.work-title :deep(.full-task-title) {
  flex: 1;
  min-width: 0;
}
.work-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 3px;
}
.work-meta > span {
  font-size: 8px;
  min-width: 35px;
  color: var(--muted, #9ba5b5);
}
.work-meta > span.done {
  color: var(--brand-accent, #a8c8ef);
}
.work-meta > span.blocked {
  color: var(--warning, #d9ad73);
}
.track {
  flex: 1;
  height: 4px;
  border-radius: 3px;
  background: #77839b44;
}
.track i {
  height: 100%;
  display: block;
  border-radius: 3px;
  background: var(--brand-accent, #a8c8ef);
}
.agent-metadata {
  display: block;
  line-height: 15px;
  margin-top: 2px;
}
button:focus-visible {
  outline: 2px solid var(--brand-accent, #a8c8ef);
  outline-offset: 2px;
}
</style>
