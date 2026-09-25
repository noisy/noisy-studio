<script setup lang="ts">
import { onMounted, ref } from 'vue';
import HeroScene from '../scenes/HeroSceneG.vue';
const scene = ref<InstanceType<typeof HeroScene>>();
const readme = new URLSearchParams(location.search).has('readme');
const intro = ref(!readme);
onMounted(async () => {
  await document.fonts.ready;
  const video = document.querySelector('video')!;
  video.preload = 'auto';
  if (video.readyState < 3) await new Promise<void>(resolve => video.addEventListener('canplay', () => resolve(), { once: true }));
  await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
  video.addEventListener('playing', () => {
    document.body.dataset.mediaStart = String((performance.timeOrigin + performance.now()) / 1000 - video.currentTime);
  }, { once: true });
  video.addEventListener('ended', () => {
    setTimeout(() => { document.body.dataset.exportEnded = 'true'; }, 800);
  }, { once: true });
  document.body.dataset.exportReady = 'true';
  setTimeout(async () => {
    intro.value = false;
    await scene.value?.play();
  }, 3500);
});
</script>
<template>
  <main class="video-export" :class="{ 'readme-export': readme }">
    <div class="scene"><HeroScene ref="scene" manual-playback /></div>
    <div v-if="intro" class="intro">
      <div class="lockup">
        <svg viewBox="0 0 46 46" width="110" height="110" aria-hidden="true">
          <rect x="3" y="3" width="40" height="40" rx="11" fill="#263448" />
          <g stroke="#b8cff3" stroke-width="3.2" stroke-linecap="round"><path d="M14 17v12M20 11v24M26 15v16M32 19v8" /></g>
        </svg>
        <h1>Noisy Studio</h1>
      </div>
      <p>Your voice, in the workflow.</p>
      <span class="soon">Coming soon</span>
    </div>
  </main>
</template>
<style>
html, body, #app { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #141619; }
.video-export { width: 100vw; height: 100vh; position: relative; display: grid; place-items: center; background: #141619; }
.video-export .scene { width: min(100vw, calc(100vh * 1200 / 760)); }
.video-export .hero-demo { border-radius: 0; }
.video-export .scene-sound { display: none; }
.readme-export .hero-terminal { opacity: 1 !important; transform: none !important; transition: none !important; }
.readme-export .recorded-widget.aloft { transform: scale(1.2) !important; transition: none !important; }
.intro { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; background: radial-gradient(ellipse at 50% 45%, #223236 0%, #141619 65%); }
.lockup { display: flex; align-items: center; gap: 25px; }
.lockup h1 { margin: 0; font-size: 76px; letter-spacing: -3px; color: #f3f5f7; }
.intro p { margin: 28px 0 40px; color: #abb8c0; font-size: 29px; }
.soon { color: #99d3c5; border: 1px solid #638d84; border-radius: 10px; padding: 12px 25px; font-size: 24px; transform: rotate(-5deg); }
</style>
