<script setup lang="ts">
/** The conversation's unheard backlog and the ways out of it: hear only
 * where things ended up (Summarize), hear every message one by one in
 * arrival order (Catch up), or drop it (Skip all). Summarize is the usual
 * choice, so it comes first, carries the count and gets twice Catch up's
 * width. Presentational: the daemon calls live in useUnheardBacklog. */
defineProps<{
  count: number;
  /** False while the conversation's session is offline: nobody to retell. */
  canSummarize: boolean;
}>();
defineEmits<{ catchUp: []; summarize: []; skip: [] }>();
</script>

<template>
  <div v-if="count" class="catchup-row">
    <button
      class="ctl summarize"
      :disabled="!canSummarize"
      :title="canSummarize
        ? 'The agent retells the unheard messages as one: only where things ended up'
        : 'This session is offline - nobody can summarize it'"
      @click="$emit('summarize')"
    >
      Σ Summarize {{ count }} unheard
    </button>
    <button
      class="ctl catchup"
      :title="`Play all ${count} unheard messages one after another, in the order they arrived`"
      @click="$emit('catchUp')"
    >
      ▶ Catch up one by one
    </button>
    <button class="ctl skipall" title="Dismiss all unheard messages without playing them" @click="$emit('skip')">
      Skip all
    </button>
  </div>
</template>

<style scoped>
/* `.catchup-row` in front out-ranks the global `.hud .ctl` look. */
.catchup-row { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
.catchup-row .catchup { flex:1 1 0; min-width:150px; border-color:var(--green); color:var(--green); }
/* Violet = the agent working: Summarize hands the backlog to it. */
.catchup-row .summarize { flex:2 1 0; min-width:150px; border-color:color-mix(in srgb, var(--violet) 70%, transparent); color:var(--violet); }
.catchup-row .summarize:disabled { opacity:.45; cursor:not-allowed; }
.catchup-row .skipall { color:var(--muted); }
</style>
