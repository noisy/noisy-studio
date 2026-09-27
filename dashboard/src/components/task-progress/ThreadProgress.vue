<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import type { ReportedTask } from "./types";
import { readyForReview } from "./types";
import TaskTitle from "./TaskTitle.vue";
const props = defineProps<{ tasks: ReportedTask[] }>();
const active = computed(() => props.tasks.filter(task => task.report.state !== "done"));
const completed = computed(() => props.tasks.filter(task => task.report.state === "done" && !readyForReview(task)).length);
const now = ref(Date.now() / 1000);
let clock: ReturnType<typeof setInterval> | undefined;
onMounted(() => { clock = setInterval(() => now.value = Date.now() / 1000, 1000); });
onBeforeUnmount(() => clearInterval(clock));
function elapsed(start: number | null | undefined) {
  if (start == null || !Number.isFinite(start)) return "—";
  const seconds = Math.max(0, Math.floor(now.value - start));
  if (seconds >= 86400) return `${Math.floor(seconds / 86400)}d ${Math.floor(seconds % 86400 / 3600)}h`;
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
  return `${seconds}s`;
}
function percentage(task: ReportedTask) {
  return task.report.total ? Math.round((task.report.completed ?? 0) / task.report.total * 100) : null;
}
</script>
<template>
  <section class="thread-progress" aria-label="Active tasks">
    <h2>Progress</h2>
    <p v-if="!tasks.length" class="quiet">No progress reported yet.</p>
    <p v-else-if="!active.length" class="quiet">No active tasks.</p>
    <article v-for="task in active" :key="task.report.task_id">
      <TaskTitle :text="task.report.title" />
      <div class="progress-row" :class="{ blocked: task.report.state === 'blocked', stale: task.stale }">
        <small :title="task.started_at == null ? 'Start time unavailable' : 'Time since task started'">{{ elapsed(task.started_at) }}</small>
        <div v-if="percentage(task) !== null" class="bar" role="progressbar" :aria-label="task.report.title" :aria-valuenow="percentage(task)!" :aria-valuemin="0" :aria-valuemax="100" :aria-valuetext="task.stale ? 'Update overdue' : task.report.state === 'blocked' ? 'Blocked' : undefined" :title="task.stale ? 'Update overdue' : task.report.state === 'blocked' ? 'Blocked' : 'Reported steps completed'">
          <i :style="{ width: percentage(task) + '%' }" />
        </div>
        <span v-else class="unknown">{{ task.stale ? 'Update overdue' : task.report.state === 'blocked' ? 'Blocked' : 'Progress not reported' }}</span>
        <span v-if="percentage(task) !== null" class="percentage">{{ percentage(task) }}%</span>
      </div>
    </article>
    <p v-if="completed" class="quiet">{{ completed }} completed · no review pending</p>
  </section>
</template>
<style scoped>
.thread-progress { min-width:0; }
h2 { font-size:11px; margin:12px 0 8px; }
article { min-width:0; padding:7px 0 8px; }
article + article { border-top:1px solid color-mix(in srgb, var(--line) 60%, transparent); }
.progress-row { display:grid; grid-template-columns:6ch minmax(0,1fr) 4ch; align-items:center; gap:8px; margin-top:5px; font-size:9px; font-variant-numeric:tabular-nums; color:var(--muted); }
small { font:inherit; white-space:nowrap; }
.percentage { text-align:right; }
.bar { height:5px; background:var(--line); border-radius:4px; min-width:0; }
.bar i { height:100%; display:block; border-radius:4px; background:var(--brand-accent); }
.blocked .bar i { background:var(--warning, #d9ad73); }
.stale .bar i { background:var(--muted); }
.unknown { grid-column:2 / 4; }
.quiet { color:var(--muted); font-size:9px; line-height:1.5; }
</style>
