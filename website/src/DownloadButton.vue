<script setup lang="ts">
// Without a release URL, keep the download visibly unavailable.
defineProps<{ downloadUrl?: string; releaseLabel?: string }>();
</script>
<template>
  <component :is="downloadUrl ? 'a' : 'button'" class="button primary download-button" :href="downloadUrl" :disabled="!downloadUrl" :title="downloadUrl ? undefined : 'Download for macOS — coming soon'">
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4" /></svg>
    <span class="download-copy"><span>Download for macOS</span><small v-if="releaseLabel">{{ releaseLabel }}</small></span>
    <span v-if="!downloadUrl" class="coming-soon">Coming soon</span>
  </component>
</template>
<style scoped>
.download-button { position: relative; width: 100%; display: flex; align-items: center; justify-content: center; border: 1px solid var(--brand-accent); border-radius: 9px; background: var(--brand-accent); color: var(--bg0); text-decoration: none; min-height: 60px; padding: 17px 25px; gap: 13px; font-size: 16px; font-weight: 650; box-shadow: 0 4px 22px #80d1cb16; }
.download-button:disabled { opacity: 1; cursor: default; }
.download-button:disabled:hover { transform: none; background: var(--brand-accent); }
.download-copy { display:flex; flex-direction:column; align-items:center; gap:4px; }
.download-copy small { font-size:12px; font-weight:500; }
.download-button svg { flex-shrink: 0; }
.coming-soon { position: absolute; right: 8px; top: -13px; transform: rotate(7deg); padding: 4px 9px; border: 1px solid var(--agent-accent, #a9b5ef); border-radius: 4px; background: #292c3d; color: #d0d6ff; font: 650 10px/1.2 var(--sans); letter-spacing: .04em; box-shadow: 0 3px 9px #0004; }
</style>
