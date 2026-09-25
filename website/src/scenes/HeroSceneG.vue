<script setup lang="ts">
import { ref } from 'vue';
import { websiteAnalytics } from '../analytics';
import RecordedHeroScene from '@dashboard/components/marketing/RecordedHeroScene.vue';
// Keep this a lightweight website copy when replacing it with actor footage.
// Preserve the original/master; regenerate with tools/website-media/prepare_todd.py
// following tools/website-media/README.md instead of embedding the full-size recording.
import recording from '../assets/todd/hero.mp4';
import take from '../assets/todd/hero.json';
import poster from '../assets/todd/hero-poster.jpg';
import activities from '../assets/todd/hero-activities.json';
import type { ActivityBlock } from '@dashboard/components/marketing/presentationTiming';
import { useStage } from './shared';
import { toddCamera } from '../toddCamera';
const props = defineProps<{ manualPlayback?: boolean }>();
const scene = ref<InstanceType<typeof RecordedHeroScene>>();
defineExpose({ play: () => scene.value?.play() });
const { frame, scale } = useStage();
</script>
<template>
  <div ref="frame" class="hero-demo" :style="{ height: `${760 * scale}px` }">
    <RecordedHeroScene ref="scene" :manual-playback="props.manualPlayback" :recording-src="recording" :recording-take="take" :recording-poster="poster" :presentation-edits="[]" :activity-blocks="activities as ActivityBlock[]" v-bind="toddCamera" @interaction="websiteAnalytics.trackDemo('hero', $event)" :style="{ transform: `scale(${scale})` }" />
  </div>
</template>
<style scoped>
.hero-demo { min-width: 0; position: relative; overflow: hidden; border-radius: 10px; }
.hero-demo > * { transform-origin: top left; }
/* Approved inward layout. Crop is baked into the lightweight media export. */
.hero-demo :deep(.hero .recorded-camera) {
  left: 24px; bottom: 24px; width: 336px; height: 199.5px; aspect-ratio: auto;
}
.hero-demo :deep(.recorded-camera video) { object-fit: cover; }
/* Shift the entire console up by the added camera height, preserving its size. */
.hero-demo :deep(.hero-terminal) { top: 49px; bottom: 113px; }
/* Center the visible idle controls, rather than their transparent window.
   Only the opening pose changes; the existing 3.2s transition is retained. */
.hero-demo :deep(.hero .recorded-widget.aloft) {
  transform: translate(-316px, -280px) scale(1.2);
}
</style>
