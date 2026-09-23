<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Companion from "../Companion.vue";
import "../../styles/companion-window.css";
import recording from "./recorded-crew/crew-recording.mp4";
import poster from "./recorded-crew/crew-recording-poster.jpg";
import take from "./recorded-crew/crew-recording.json";
import { type RecordedTake, recordedCrewAt } from "./recordedCrewTimeline";

const props = withDefaults(defineProps<{
  manualPlayback?: boolean;
  playbackControls?: boolean;
  activityAtTime?: (timeMs: number) => string | null;
  layout?: 'crew' | 'hero';
  recordingSrc?: string;
  recordingPoster?: string;
  recordingTake?: RecordedTake;
  compact?: boolean;
  camera?: boolean;
  cameraZoom?: number;
  cameraOffsetX?: number;
  cameraOffsetY?: number;
}>(), { camera: true, cameraZoom: 1.35, cameraOffsetX: 0, cameraOffsetY: 0 });
const cameraScale = computed(() => Math.max(1, Math.min(4, props.cameraZoom)));
const cameraTransform = computed(() => {
  // Each axis spans the available overflow at this zoom. Even the end stops
  // keep the image covering the camera window, with no exposed empty edges.
  const travel = (cameraScale.value - 1) * 50;
  const x = Math.max(-100, Math.min(100, props.cameraOffsetX)) / 100 * travel;
  const y = Math.max(-100, Math.min(100, props.cameraOffsetY)) / 100 * travel;
  return `translate(${x}%, ${y}%) scale(${cameraScale.value})`;
});
const emit = defineEmits<{ time: [timeMs: number]; interaction: [action: 'play' | 'pause' | 'mute' | 'unmute'] }>();
const video = ref<HTMLVideoElement | null>(null);
const timeMs = ref(0);
const soundOn = ref(false);
const playing = ref(false);
const playbackError = ref(false);
const reducedMotion = ref(false);
const state = computed(() => recordedCrewAt(props.recordingTake ?? take, timeMs.value));
let animation = 0;
let visibility: IntersectionObserver | undefined;
let motion: MediaQueryList;
let soundRequest = 0;
function motionChanged() { reducedMotion.value = motion.matches; }
function sampleTime() {
  if (video.value) { timeMs.value = video.value.currentTime * 1000; emit('time', timeMs.value); }
  animation = requestAnimationFrame(sampleTime);
}
function updateTime() { timeMs.value = (video.value?.currentTime ?? 0) * 1000; }
function seek(ms: number) {
  if (video.value) video.value.currentTime = Math.max(0, ms) / 1000;
  updateTime();
}
function pause() { ++soundRequest; video.value?.pause(); playing.value = false; }
function restart() {
  if (video.value) video.value.currentTime = 0;
  timeMs.value = 0;
}
async function setSound(enabled: boolean) {
  const media = video.value;
  if (!media) return;
  const request = ++soundRequest;
  soundOn.value = enabled;
  media.muted = !enabled;
  if (!enabled) return;
  if (media.ended) restart();
  try {
    await media.play();
    if (request !== soundRequest) return;
    playbackError.value = false;
  } catch {
    if (request !== soundRequest) return;
    soundOn.value = false;
    playing.value = false;
    media.muted = true;
    playbackError.value = true;
  }
}
function toggleSound() { return setSound(!soundOn.value); }
function ended() {
  playing.value = false;
  void setSound(false);
}
onMounted(() => {
  motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  motionChanged();
  motion.addEventListener("change", motionChanged);
  animation = requestAnimationFrame(sampleTime);
  visibility = new IntersectionObserver(([entry]) => {
    if (!video.value) return;
    if (!entry.isIntersecting) {
      pause();
      void setSound(false);
    } else if (!props.manualPlayback && !props.playbackControls && !reducedMotion.value && !video.value.ended) {
      void video.value.play().catch(() => {});
    }
  });
  if (video.value) visibility.observe(video.value);
});
onBeforeUnmount(() => {
  cancelAnimationFrame(animation);
  visibility?.disconnect();
  motion?.removeEventListener("change", motionChanged);
  video.value?.pause();
});
defineExpose({ restart, toggleSound, soundOn, seek, pause, play: () => setSound(true) });
</script>

<template>
  <div class="recorded-crew companion-transparent" :class="{ compact, hero: layout === 'hero' }" :style="{ width: layout === 'hero' ? '1200px' : compact ? '600px' : '760px' }"
    role="group" aria-label="Recorded conversation demo">
    <slot :time-ms="timeMs" />
    <div class="recorded-widget" :class="{ aloft: layout === 'hero' && timeMs < 3200 && !reducedMotion }" :style="{
      transform: layout === 'hero' ? undefined : camera && !reducedMotion && state.zoom ? 'scale(2)' : 'scale(1)',
    }">
      <div class="companion-window" inert><div class="companion-host">
        <Companion draggable avatar-set="editorial" :mode="state.mode" :voice="state.voice" :feed="state.feed"
          :activity="activityAtTime?.(timeMs) ?? null" :live-text="state.liveText" :agents="layout === 'hero' ? [{ name: 'workspace', label: 'Claude', voice: 'lux', active: true }] : state.agents" :max-height="200" />
      </div></div>
    </div>
    <!-- The camera is a sibling of the zooming widget: anchored to the
         screenshot's top-left corner throughout every agent handover. -->
    <div class="recorded-camera">
      <video ref="video" :src="recordingSrc ?? recording" :poster="recordingPoster ?? poster" muted playsinline preload="metadata"
        :style="{ transform: cameraTransform }"
        :aria-label="layout === 'hero' ? 'Recorded conversation with Lux' : 'Recorded conversation with Lux, Rex and Luna'"
        @timeupdate="updateTime" @seeked="updateTime" @ended="ended" @playing="playing = true" @pause="playing = false"
        @error="playbackError = true" />
    </div>
      <button v-if="playbackControls" class="scene-playback" :class="{ 'scene-pause': playing }" type="button"
        :aria-label="playing ? 'Pause demo' : 'Play demo'" @click="emit('interaction', playing ? 'pause' : 'play'); playing ? pause() : setSound(true)">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path v-if="!playing" d="M8 4v16l13-8z" />
          <path v-else d="M6 4h4v16H6zM14 4h4v16h-4z" />
        </svg>
      </button>
      <button v-if="!playbackControls || playing" class="scene-sound" type="button" :aria-pressed="soundOn"
        :aria-label="soundOn ? 'Mute demo sound' : 'Enable demo sound'"
        :title="soundOn ? 'Mute sound' : 'Enable sound'" @click="emit('interaction', soundOn ? 'mute' : 'unmute'); toggleSound()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
          stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M11 5 6 9H3v6h3l5 4V5Z" />
          <path v-if="!soundOn" d="m16 9 6 6m0-6-6 6" />
          <path v-else d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14" />
        </svg>
      </button>
    <p v-if="playbackError" class="playback-error" role="status">Unable to play this recording. Please try again.</p>
  </div>
</template>

<style scoped>
.recorded-crew {
  height: 440px; position: relative; overflow: hidden;
  background: radial-gradient(1100px 700px at 25% 15%, #2a2350 0%, transparent 55%),
    radial-gradient(900px 600px at 85% 85%, #1b2a4a 0%, transparent 60%),
    linear-gradient(160deg, #0b0d1f, #141334 55%, #0a0f24);
}
.hero { height: 760px; }
.hero .recorded-widget { top: auto; right: 32px; bottom: 52px; transform: scale(1.2); transform-origin: bottom right; }
.hero .recorded-widget.aloft { transform: translate(-316px, -88px) scale(1.2); }
.hero .recorded-camera { width: 260px; left: 24px; top: auto; bottom: 24px; }
.hero .scene-sound { left: 24px; top: 24px; bottom: auto; }
.recorded-widget {
  position: absolute; right: 20px; top: 20px; width: 420px; height: 400px;
  transform-origin: 94% 100%; transition: transform .75s cubic-bezier(.22,.61,.36,1);
}
.recorded-widget :deep(.companion-header) { visibility: hidden; }
.recorded-widget :deep(.companion-window::after) { display: none; }
.recorded-widget :deep(.rail) { scrollbar-width: none; }
.recorded-widget :deep(.rail::-webkit-scrollbar) { display: none; }
.recorded-camera {
  position: absolute; left: 16px; top: 16px; width: 192px; aspect-ratio: 16 / 9;
  overflow: hidden; border-radius: 12px; border: 1px solid #ffffff38;
  box-shadow: 0 6px 24px #0005; background: #18171c;
}
.compact .recorded-camera { width: 132px; }
.recorded-camera video { display: block; width: 100%; height: 100%; }
.scene-sound {
  position: absolute; left: 16px; bottom: 16px;
  width: 64px; height: 64px; display: grid; place-items: center;
  color: #fff; background: #16181eb3; border: 1px solid #ffffff80;
  border-radius: 50%; opacity: .8; cursor: pointer;
  box-shadow: 0 3px 14px #0004;
}
.scene-sound svg { width: 34px; height: 34px; }
.scene-sound:hover, .scene-sound:focus-visible { opacity: 1; background: #16181ee6; }
.scene-sound:focus-visible { outline: 2px solid white; outline-offset: 3px; }
.compact .scene-sound { width: 52px; height: 52px; }
.scene-playback {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  width: 80px; height: 80px; display: grid; place-items: center;
  color: #fff; background: #16181ecc; border: 1px solid #ffffff80;
  border-radius: 50%; cursor: pointer; box-shadow: 0 3px 20px #0005;
}
.scene-playback svg { width: 36px; height: 36px; }
.scene-pause { opacity: 0; pointer-events: none; }
.recorded-crew:hover .scene-pause, .scene-pause:focus-visible { opacity: 1; pointer-events: auto; }
.scene-playback:focus-visible { outline: 2px solid white; outline-offset: 4px; }
@media (hover: none) { .scene-pause { opacity: 1; pointer-events: auto; } }
.playback-error { position: absolute; left: 16px; top: 8px; color: #ffcfb1; font-size: 12px; }
@media (prefers-reduced-motion: reduce) { .recorded-widget { transition: none; } }
</style>
