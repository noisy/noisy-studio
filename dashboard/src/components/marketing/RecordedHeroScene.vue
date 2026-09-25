<script setup lang="ts">
import { ref, computed } from 'vue';
import type { RecordedTake } from './recordedCrewTimeline';
import RecordedCrewScene from './RecordedCrewScene.vue';
import ClaudeCodeMock from './ClaudeCodeMock.vue';
import recording from './recorded-hero/hero-recording.mp4';
import poster from './recorded-hero/hero-recording-poster.jpg';
import take from './recorded-hero/hero-recording.json';
import savedPresentation from '../../../../tools/demo-recorder/takes/hero-v1/presentation-edits.json';
import { recordedHeroConsoleAt } from './recordedHeroConsole';
import { activityAt, presentationTake, type TurnTiming, type ActivityBlock } from './presentationTiming';
const props = withDefaults(defineProps<{ recordingSrc?: string; recordingPoster?: string; recordingTake?: RecordedTake; manualPlayback?: boolean; activityBlocks?: ActivityBlock[]; presentationEdits?: TurnTiming[]; cameraZoom?: number; cameraOffsetX?: number; cameraOffsetY?: number }>(), {
  activityBlocks: () => savedPresentation.activities as ActivityBlock[], presentationEdits: () => savedPresentation.turns as TurnTiming[], cameraZoom: 1.35, cameraOffsetX: 0, cameraOffsetY: 0,
});
const emit = defineEmits<{time: [timeMs: number]; interaction: [action: 'play' | 'pause' | 'mute' | 'unmute']}>();
const sourceTake = computed(() => props.recordingTake ?? take);
const adjustedTake = computed(() => presentationTake(sourceTake.value, props.presentationEdits));
const activity = (time: number) => activityAt(sourceTake.value, props.presentationEdits, time, props.activityBlocks);
const scene = ref<InstanceType<typeof RecordedCrewScene>>();
defineExpose({ seek: (ms: number) => scene.value?.seek(ms), pause: () => scene.value?.pause(), play: () => scene.value?.play(), restart: () => scene.value?.restart(), toggleSound: () => scene.value?.toggleSound() });
</script>
<template>
  <RecordedCrewScene ref="scene" class="hero-recording" layout="hero"
    :recording-src="recordingSrc ?? recording" :recording-poster="recordingPoster ?? poster" :recording-take="adjustedTake" :manual-playback="manualPlayback" :activity-at-time="activity" @time="emit('time', $event)" @interaction="emit('interaction', $event)"
    :camera-zoom="cameraZoom" :camera-offset-x="cameraOffsetX" :camera-offset-y="cameraOffsetY">
    <template #default="{ timeMs }">
      <div class="hero-terminal" :class="{ visible: timeMs >= 1800 }">
        <ClaudeCodeMock full-bleed banner="mascot" title="workspace" project-name="workspace" :transcript="recordedHeroConsoleAt(adjustedTake, timeMs, presentationEdits, activityBlocks)" />
      </div>
    </template>
  </RecordedCrewScene>
</template>
<style scoped>
.hero-recording.hero { background: url('./recorded-hero/mac-desktop.webp') center / cover no-repeat; }
.hero-terminal { position: absolute; inset: 73px 87px 89px; opacity: 0; transform: translateX(-1260px); filter: saturate(.4) brightness(.75); transition: opacity .5s ease, transform 1s cubic-bezier(.22,.8,.3,1); }
.hero-terminal.visible { opacity: 1; transform: translateX(0); }
@media(prefers-reduced-motion: reduce) { .hero-terminal { opacity: 1; transform: none; transition: none; } }
</style>
