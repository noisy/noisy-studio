<script setup lang="ts">
import type { ModelDownload } from '../api/client';
defineProps<{ downloads: ModelDownload[] }>();
const megabytes = (bytes: number) => `${(Math.max(0, bytes) / 1_000_000).toFixed(1)} MB`;
const percent = (download: ModelDownload) => Math.min(100, Math.floor(Math.max(0, download.done_bytes) / download.total_bytes * 100));
</script>

<template>
  <section v-if="downloads.length" class="downloads" aria-label="Model downloads">
    <h3>Model downloads</h3>
    <p>Your current engine stays active. You can keep browsing settings.</p>
    <div v-for="download in downloads" :key="download.name" class="download">
      <div class="label"><strong>{{ download.label }}</strong><span>{{ download.state === 'done' ? 'Downloaded' : download.state === 'error' ? 'Download failed' : 'Downloading' }}</span></div>
      <template v-if="download.state === 'downloading'">
        <progress :aria-label="download.label" :value="download.total_bytes > 0 ? Math.min(download.done_bytes, download.total_bytes) : undefined" :max="download.total_bytes > 0 ? download.total_bytes : 1" />
        <small v-if="download.total_bytes > 0">{{ megabytes(download.done_bytes) }} / {{ megabytes(download.total_bytes) }} · {{ percent(download) }}%</small>
        <small v-else>{{ download.done_bytes > 0 ? `${megabytes(download.done_bytes)} downloaded · ` : '' }}Total size unavailable</small>
      </template>
      <p v-if="download.state === 'error'" class="error">{{ download.detail || 'Open this engine and retry the download.' }}</p>
    </div>
  </section>
</template>

<style scoped>
.downloads{padding:16px 18px;background:var(--bg1);border:1px solid var(--line-strong);border-radius:12px;display:grid;gap:12px}.downloads h3{margin:0;font-size:14px}.downloads p{margin:0;color:var(--muted);font-size:12px}.download{display:grid;gap:7px;min-width:0}.label{display:flex;justify-content:space-between;gap:12px;font-size:12px}.label strong{overflow-wrap:anywhere}.label span,small{color:var(--muted);font-size:11px}.label span{flex-shrink:0}progress{width:100%;height:8px;accent-color:var(--brand-accent)}.downloads .error{color:var(--amber);overflow-wrap:anywhere}
</style>
