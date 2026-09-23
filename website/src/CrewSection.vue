<script setup lang="ts">
import { websiteAnalytics } from './analytics';
import { ref, onMounted, onBeforeUnmount } from "vue";
import RecordedCrewScene from "@dashboard/components/marketing/RecordedCrewScene.vue";
// Keep this a lightweight website copy when replacing it with actor footage.
// Preserve the original/master; regenerate with tools/website-media/prepare_todd.py
// following tools/website-media/README.md instead of embedding the full-size recording.
import recording from './assets/todd/crew.mp4';
import take from './assets/todd/crew.json';
import poster from './assets/todd/crew-poster.jpg';
import VoiceCarousel from "./VoiceCarousel.vue";
const frame = ref<HTMLElement | null>(null);
const scale = ref(0.7);
const compact = ref(false);
let observer: ResizeObserver | undefined;
onMounted(() => {
  if (!frame.value) return;
  observer = new ResizeObserver(() => {
    compact.value = frame.value!.clientWidth < 600;
    scale.value = frame.value!.clientWidth / (compact.value ? 600 : 760);
  });
  observer.observe(frame.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
});
</script>
<template>
  <section id="voices" class="section voice-section">
    <div class="wrap voice-layout">
      <div class="voice-copy">
        <p class="eyebrow">Different voices. One conversation at a time.</p>
        <h2>Know who’s talking.<br /><em>Before you look.</em></h2>
        <p class="section-intro">
          A deployment update. A PR worth celebrating. A personal reminder.
          Recognize the voice, know the context—and answer when you’re ready.
        </p>
        <VoiceCarousel />
      </div>
      <div>
        <div
          ref="frame"
          class="voice-stage"
          :style="{ height: `${440 * scale}px` }"
        >
          <div
            :style="{
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
            }"
          >
            <RecordedCrewScene :recording-src="recording" :recording-take="take" :recording-poster="poster" :camera-zoom="1 / (1 - 2 * 0.25)" @interaction="websiteAnalytics.trackDemo('crew', $event)" playback-controls :camera="!compact" :compact="compact" />
          </div>
        </div>
        <p class="voice-caption">
          Each voice takes its turn. Waiting messages stay with their
          conversation.
        </p>
      </div>
    </div>
  </section>
</template>
<style scoped>
.voice-section {
  background: radial-gradient(ellipse at 80% 60%, #31303f, #1c1e23 65%);
  border-block: 1px solid var(--line);
}
.voice-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.75fr) minmax(0, 1.25fr);
  align-items: center;
  gap: var(--layout-gap);
}
.voice-layout > div { min-width: 0; }
.voice-copy h2 {
  font-size: clamp(36px, 3.5vw, 56px);
}
.voice-caption {
  font-size: 12px;
  margin-top: 16px;
}
.voice-caption {
  text-align: center;
}
.voice-stage {
  width: 100%;
  max-width: 720px;
  margin-inline: auto;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid var(--line-strong);
}
@media (max-width: 900px) {
  .voice-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .voice-copy {
    max-width: 640px;
  }
}
</style>
