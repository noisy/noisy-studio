<script setup lang="ts">
import { computed, ref } from 'vue';
import { reviewTask } from '../../api/client';
import { reviewTargetUrl } from './reviewPage';
import type { ReportedTask } from './types';
import TaskTitle from './TaskTitle.vue';
const props = defineProps<{ agent: string; task: ReportedTask; threadLabel?: string; offline: boolean }>();
const emit = defineEmits<{ reviewed: [] }>();
const busy = ref(false), error = ref('');
const savedState = ref<ReportedTask['review_state']>();
const state = computed(() => savedState.value ?? props.task.review_state);
const href = computed(() => reviewTargetUrl(props.agent, props.task));
async function save(action: 'opened' | 'approve' | 'reject') {
  busy.value = true;
  error.value = '';
  try {
    await reviewTask(props.agent, props.task.report.task_id, props.task.report.revision, action);
    savedState.value = action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'opened';
    emit('reviewed');
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Review could not be saved';
  } finally {
    busy.value = false;
  }
}
function open(event: MouseEvent) {
  if (props.offline || busy.value) { event.preventDefault(); return; }
  // Keep browser navigation synchronous with the click; save the visit separately.
  void save('opened');
}
</script>
<template>
  <article class="review-item" :class="{ opened: state !== 'unopened' }">
    <a class="review-link" :href="href" target="_blank" rel="noopener noreferrer"
      :aria-label="task.report.review?.label" :aria-disabled="offline || busy" @click="open">
      <span class="identity"><TaskTitle :text="task.report.title" /><small v-if="threadLabel">{{ threadLabel }}</small></span>
      <span aria-hidden="true">↗</span>
    </a>
    <Transition name="actions">
      <div v-if="state === 'opened'" class="review-actions">
        <button :disabled="offline || busy" @click="save('approve')">Approve</button>
        <button :disabled="offline || busy" @click="save('reject')">Reject</button>
      </div>
    </Transition>
    <p v-if="error" role="alert">{{ error }}</p>
  </article>
</template>
<style scoped>
.review-item { min-width:0; margin:4px 0; border:1px solid var(--line,#363a43); border-radius:7px; overflow:hidden; }
.review-link { display:flex; align-items:center; gap:8px; padding:9px; color:var(--ink,#e4e7ee); text-decoration:none; background:var(--panel,#202329); transition:background .15s; }
.review-link:hover, .opened .review-link { background:color-mix(in srgb,var(--brand-accent,#a8c8ef) 15%,var(--panel,#202329)); }
.identity { flex:1; min-width:0; }
small { display:block; margin-top:3px; color:var(--muted,#9ba5b5); font-size:9px; }
.review-actions { display:flex; gap:1px; background:var(--line,#363a43); border-top:1px solid var(--line,#363a43); }
button { flex:1; cursor:pointer; border:0; padding:7px; font:inherit; color:var(--brand-accent,#a8c8ef); background:var(--panel,#202329); }
button:hover { filter:brightness(1.2); }
button:disabled, a[aria-disabled="true"] { opacity:.5; cursor:default; }
a:focus-visible, button:focus-visible { outline:2px solid var(--brand-accent,#a8c8ef); outline-offset:-2px; }
p { margin:6px; font-size:10px; color:var(--warning,#d9ad73); }
.actions-enter-active, .actions-leave-active { transition:opacity .18s, transform .18s, max-height .18s; max-height:45px; }
.actions-enter-from, .actions-leave-to { opacity:0; transform:translateY(-8px); max-height:0; }
@media(prefers-reduced-motion:reduce) { .actions-enter-active,.actions-leave-active,.review-link { transition:none; } }
</style>
