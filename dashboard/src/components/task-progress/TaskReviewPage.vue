<script setup lang="ts">
import { computed } from 'vue';
import type { DaemonStatus, Utterance } from '../../types';
import { useTaskProgress } from '../../composables/useTaskProgress';
import TaskReview from './TaskReview.vue';
import { reviewUrl } from './types';
import { reviewPageUrl } from './reviewPage';
const props = defineProps<{ agent: string; taskId: string; revision: number; status: DaemonStatus | null; offline: boolean; utterances: Utterance[] }>();
const emit = defineEmits<{ close: []; startPtt: []; stopPtt: [] }>();
const { snapshot, error, refresh } = useTaskProgress();
const task = computed(() => snapshot.value.threads[props.agent]?.[props.taskId]);
const current = computed(() => task.value?.report.revision === props.revision && task.value.report.state === 'done' && reviewUrl(task.value));
</script>
<template>
  <TaskReview v-if="task && current" :target="{agent, task}" :status="status" :offline="offline" :utterances="utterances" @close="emit('close')" @reviewed="refresh" @start-ptt="emit('startPtt')" @stop-ptt="emit('stopPtt')" />
  <main v-else class="review-unavailable">
    <h1>Noisy Studio review</h1>
    <p role="status">{{ error || (task ? 'This task has changed since this review link was created.' : 'Waiting for this review. If it stays unavailable, the task may have been removed or the desktop disconnected.') }}</p>
    <a v-if="task && task.report.state === 'done' && reviewUrl(task)" :href="reviewPageUrl(agent, taskId, task.report.revision)">Open current review</a>
    <button @click="refresh">Retry</button>
    <button @click="emit('close')">Back to dashboard</button>
  </main>
</template>
<style scoped>
.review-unavailable { padding:32px; color:var(--ink); }
button,a { margin-right:12px; }
</style>
