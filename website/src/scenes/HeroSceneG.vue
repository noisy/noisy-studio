<script setup lang="ts">
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
import { toddCamera, cornerCameraPreview, inwardCameraPreview } from '../toddCamera';
const { frame, scale } = useStage();
</script>
<template>
  <div ref="frame" class="hero-demo" :class="{ 'corner-camera': cornerCameraPreview, 'inward-camera': inwardCameraPreview }" :style="{ height: `${760 * scale}px` }">
    <RecordedHeroScene :recording-src="recording" :recording-take="take" :recording-poster="poster" :presentation-edits="[]" :activity-blocks="activities as ActivityBlock[]" v-bind="toddCamera" @interaction="websiteAnalytics.trackDemo('hero', $event)" :style="{ transform: `scale(${scale})` }" />
  </div>
</template>
<style scoped>
.hero-demo { min-width: 0; position: relative; overflow: hidden; border-radius: 10px; }
.hero-demo > * { transform-origin: top left; }
/* Enlarge the actor window without changing the video crop or crew scene. */
.hero-demo :deep(.hero .recorded-camera) { width: 312px; }
/* Keep the old top-right at (336, 560.5); extend to the stage edges. */
.hero-demo.corner-camera :deep(.hero .recorded-camera) {
  left: 0; bottom: 0; width: 336px; height: 199.5px; aspect-ratio: auto;
  border-radius: 0 12px 0 0;
}
.hero-demo.corner-camera :deep(.recorded-camera video) { object-fit: cover; }
/* Same size as B, anchored at A's bottom-left; grow toward the center. */
.hero-demo.inward-camera :deep(.hero .recorded-camera) {
  left: 24px; bottom: 24px; width: 336px; height: 199.5px; aspect-ratio: auto;
}
.hero-demo.inward-camera :deep(.recorded-camera video) { object-fit: cover; }
/* Shift the entire console up by the added camera height, preserving its size. */
.hero-demo.inward-camera :deep(.hero-terminal) { top: 49px; bottom: 113px; }
</style>
