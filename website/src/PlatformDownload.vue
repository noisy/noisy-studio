<script setup lang="ts">
import DownloadButton from './DownloadButton.vue';
import { computed, onMounted, ref } from 'vue';
type Platform = 'mac' | 'windows' | 'linux';
const props = defineProps<{ platform?: Platform; downloadUrl?: string; compact?: boolean }>();
const emit = defineEmits<{ notify: [details: { platform: Platform; email: string }] }>();
const detectedPlatform = ref<Platform>('mac');
onMounted(() => {
  const system = navigator.userAgent.toLowerCase();
  detectedPlatform.value = system.includes('windows') ? 'windows' : system.includes('linux') && !system.includes('android') ? 'linux' : 'mac';
});
const selected = computed(() => props.platform ?? detectedPlatform.value);
const email = ref('');
const name = computed(() => ({ mac: 'macOS', windows: 'Windows', linux: 'Linux' })[selected.value]);
const emailId = computed(() => `notify-${selected.value}-${props.compact ? 'hero' : 'footer'}`);
function notify() { emit('notify', { platform: selected.value, email: email.value }); }
</script>
<template>
  <section class="platform-download" :class="{ compact }" :aria-label="`Noisy Studio for ${name}`">
    <template v-if="selected === 'mac'">
      <p v-if="!compact" class="platform-kicker">MADE FOR YOUR MAC</p>
      <h3 v-if="!compact">Your next conversation<br>starts here.</h3>
      <p v-if="!compact" class="platform-description">Bring Noisy Studio into your coding workflow.</p>
      <DownloadButton :download-url="downloadUrl" />
      <p v-if="downloadUrl" class="download-compatibility">Apple Silicon · 3.0.0-beta.1</p>
    </template>
    <template v-else>
      <p v-if="!compact" class="platform-kicker">{{ name.toUpperCase() }} VERSION · COMING LATER</p>
      <h3 v-if="!compact">{{ name }} is next.</h3>
      <p class="platform-description">{{ name }} version coming soon.</p>
      <form @submit.prevent="notify">
        <label :for="emailId">Email address</label>
        <input :id="emailId" v-model="email" type="email" autocomplete="email" placeholder="you@example.com" required>
        <button class="platform-primary" type="submit">Notify me <span aria-hidden="true">→</span></button>
      </form>
    </template>
  </section>
</template>
<style scoped>
.platform-download { box-sizing:border-box; width:100%; max-width:470px; padding:32px; color:var(--ink); background:linear-gradient(145deg,var(--accent-surface),var(--bg1) 65%); border:1px solid var(--accent-border); border-radius:20px; font:15px/1.55 var(--sans); }
.download-compatibility { margin:10px 0 0; color:var(--muted); font-size:12px; text-align:center; }
.platform-kicker { color:var(--brand-accent); font-size:10px; font-weight:700; letter-spacing:.12em; margin:0 0 12px; }
h3 { font-size:30px; line-height:1.2; letter-spacing:-.035em; margin:0 0 16px; }
.platform-description { color:var(--muted); margin:0 0 24px; }
.platform-primary { box-sizing:border-box; display:flex; width:100%; align-items:center; justify-content:center; gap:12px; min-height:56px; border:1px solid var(--brand-accent); border-radius:9px; background:var(--brand-accent); color:var(--bg0); text-decoration:none; font:650 15px/1.4 var(--sans); cursor:pointer; padding:14px; text-align:center; }
.platform-primary:disabled { opacity:1; cursor:default; }
form label { display:block; font-size:12px; margin-bottom:6px; }
form input { box-sizing:border-box; width:100%; background:var(--bg0); color:var(--ink); border:1px solid var(--line-strong); border-radius:8px; padding:12px; font:inherit; margin-bottom:12px; }
.platform-secondary { display:inline-block; margin-top:14px; color:var(--muted); font:12px var(--sans); text-decoration:underline; text-underline-offset:3px; }
button:focus-visible,input:focus-visible,a:focus-visible { outline:2px solid var(--brand-accent); outline-offset:3px; }
.compact { padding:0; border:0; background:none; border-radius:0; }
.compact .platform-description { margin-bottom:14px; font-size:13px; }
.compact .platform-primary { font-size:14px; }
@media(max-width:420px) { .platform-download:not(.compact) { padding:22px; } h3 { font-size:27px; } }
</style>
