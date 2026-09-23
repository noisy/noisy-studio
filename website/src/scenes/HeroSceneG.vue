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
const { frame, scale } = useStage();
</script>
<template>
  <div ref="frame" class="hero-demo" :style="{ height: `${760 * scale}px` }">
    <RecordedHeroScene :recording-src="recording" :recording-take="take" :recording-poster="poster" :presentation-edits="[]" :activity-blocks="activities as ActivityBlock[]" :camera-zoom="1 / (1 - 2 * 0.15)" @interaction="websiteAnalytics.trackDemo('hero', $event)" :style="{ transform: `scale(${scale})` }" />
  </div>
</template>
<style scoped>
.hero-demo { min-width: 0; position: relative; overflow: hidden; border-radius: 10px; }
.hero-demo > * { transform-origin: top left; }
</style>
