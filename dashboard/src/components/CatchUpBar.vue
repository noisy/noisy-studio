<script setup lang="ts">
/** The conversation's unheard backlog and the ways out of it: hear it all
 * (Catch up), hear only where things ended up (Summarize), or drop it
 * (Skip all). Catch up and Summarize share the row equally. Presentational:
 * the daemon calls live in useUnheardBacklog. */
defineProps<{
  count: number;
  /** False while the conversation's session is offline: nobody to retell. */
  canSummarize: boolean;
}>();
defineEmits<{ catchUp: []; summarize: []; skip: [] }>();
</script>

<template>
  <div v-if="count" class="catchup-row">
    <button class="ctl catchup" @click="$emit('catchUp')">
      ▶ Catch up ({{ count }} unheard)
    </button>
    <button
      class="ctl summarize"
      :disabled="!canSummarize"
      :title="canSummarize
        ? 'The agent retells the unheard messages as one: only where things ended up'
        : 'This session is offline - nobody can summarize it'"
      @click="$emit('summarize')"
    >
      Σ Summarize
    </button>
    <button class="ctl skipall" title="Dismiss all unheard messages without playing them" @click="$emit('skip')">
      Skip all
    </button>
  </div>
</template>

<style scoped>
/* `.catchup-row` in front out-ranks the global `.hud .ctl` look. */
.catchup-row { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
.catchup-row .catchup, .catchup-row .summarize { flex:1 1 0; min-width:150px; }
.catchup-row .catchup { border-color:var(--green); color:var(--green); }
/* Violet = the agent working: Summarize hands the backlog to it. */
.catchup-row .summarize { border-color:color-mix(in srgb, var(--violet) 70%, transparent); color:var(--violet); }
.catchup-row .summarize:disabled { opacity:.45; cursor:not-allowed; }
.catchup-row .skipall { color:var(--muted); }
</style>
