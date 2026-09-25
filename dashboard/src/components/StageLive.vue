<script setup lang="ts">
import { computed } from 'vue';
import Stage from './Stage.vue';
import type { DaemonStatus, Utterance } from '../types';
import { stageModel } from '../stage/model';
import { useStagePreferences } from '../stage/preferences';
const props = defineProps<{ status: DaemonStatus | null; utterances: Utterance[]; offline: boolean }>();
defineEmits<{ exit: [] }>();
const preferences = useStagePreferences();
const model = computed(() => stageModel(props.status, props.utterances, preferences.value.labels));
</script>
<template>
  <div class="stage-live">
    <p v-if="offline" class="stage-disconnected" role="status">Connection lost. Waiting for Noisy Studio…</p>
    <Stage :people="model.people" :lines="model.lines" :speaking="offline ? '' : model.speaking" :caption="offline ? null : model.caption" :initial-display="preferences.display" :initial-hidden="preferences.hidden" :label-mode="preferences.labels" @preferences="Object.assign(preferences, $event)" @label-mode="preferences.labels = $event" @exit="$emit('exit')" />
  </div>
</template>
<style scoped>
.stage-live{position:fixed;inset:0;overflow:auto;z-index:90;background:#0b1719}.stage-disconnected{position:absolute;z-index:4;top:0;left:0;right:0;margin:0;padding:5px 12px;background:#624529;color:#fff0d0;text-align:center;font:12px system-ui}
</style>
