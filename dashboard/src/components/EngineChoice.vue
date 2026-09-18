<script setup lang="ts">
// Prepare local models before selecting them; the working engines stay active.
import { computed, onMounted, onUnmounted, ref } from "vue";
import { getProviders, setProviders, type ProvidersInfo } from "../api/client";

const emit = defineEmits<{ mode: [mode: "cloud" | "local"] }>();

const info = ref<ProvidersInfo | null>(null);
const chosen = ref<"cloud" | "local">("cloud");
const busy = ref(false);
const error = ref("");
const pendingLocal = ref(false);

const POLL_MS = 1000;
let pollTimer: ReturnType<typeof setInterval> | undefined;

const localEntry = computed(() =>
  info.value?.catalog.find((p) => p.name === "local"),
);
const downloads = computed(() =>
  (info.value?.downloads ?? []).filter((d) => d.state !== "missing"),
);
const downloading = computed(() =>
  (info.value?.downloads ?? []).some((d) => d.state === "downloading"),
);
const localActive = computed(() => {
  const active = info.value?.active;
  return active?.tts === "local" && active?.stt === "local";
});

// Reflect a pre-existing local setup ONCE, on first load — later polls
// must not fight a user who clicked back to CLOUD mid-download.
let syncedOnce = false;

async function refresh() {
  try {
    info.value = await getProviders();
    if (!syncedOnce && localActive.value) setChosen("local");
    syncedOnce = true;
  } catch {
    info.value = null; // an old daemon — the parent's key flow still works
  }
}
onMounted(() => {
  void refresh();
  pollTimer = setInterval(() => {
    if (!busy.value && (chosen.value === 'local' || downloading.value)) void refresh();
  }, POLL_MS);
});
onUnmounted(() => clearInterval(pollTimer));

// The daemon answers errors as {"error": "..."} — surface that wording;
// anything else gets a human line instead of a stack-trace string.
function friendly(e: unknown): string {
  const text = e instanceof Error ? e.message : String(e);
  const match = text.match(/\{"error":\s*"([^"]+)"/);
  return match ? match[1] : "the daemon didn't accept that — try again";
}

function setChosen(mode: "cloud" | "local") {
  chosen.value = mode;
  emit("mode", mode);
}

async function pickLocal() {
  setChosen("local");
  if (!localEntry.value?.ready) return; // remedy line renders below
  busy.value = true;
  error.value = "";
  try {
    pendingLocal.value = true;
    await setProviders({ stt: "local", tts: "local" });
    pendingLocal.value = false;
  } catch (e) {
    error.value = friendly(e);
  } finally {
    await refresh();
    busy.value = false;
  }
}

function percent(done: number, total: number): number {
  return total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
}
function megabytes(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(0)} MB`;
}

async function retryDownloads() { await pickLocal(); }

</script>

<template>
  <div v-if="info" class="engines">
    <div class="cards">
      <button
        class="card"
        :class="{ on: chosen === 'cloud' }"
        :aria-pressed="chosen === 'cloud'"
        :disabled="busy"
        @click="setChosen('cloud')"
      >
        <span class="card-title">Cloud · Grok (xAI)</span>
        <span class="card-text">
          The full experience: natural voices, live streaming both ways.
          Requires an xAI API key and an internet connection.
        </span>
      </button>
      <button
        class="card"
        :class="{ on: chosen === 'local' }"
        :aria-pressed="chosen === 'local'"
        :disabled="busy"
        @click="pickLocal"
      >
        <span class="card-title">Local · Offline</span>
        <span class="card-text">
          Whisper transcribes your speech; Kokoro speaks in English on this
          machine. Download the models first, then choose Use local engines.
          Text appears after you finish; replies are generated before playback.
        </span>
      </button>
    </div>

    <template v-if="chosen === 'local'">
      <p v-if="localEntry && !localEntry.ready" class="remedy">
        {{ localEntry.ready_detail || "local engines are not available on this system" }}
      </p>
      <div v-if="downloads.length" class="downloads">
        <div v-for="d in downloads" :key="d.name" class="dlrow">
          <span class="dl-label">{{ d.label.toUpperCase() }}</span>
          <template v-if="d.state === 'downloading'">
            <div class="bar">
              <div
                class="fill"
                :class="{ pulse: !d.total_bytes }"
                :style="{ width: (d.total_bytes ? percent(d.done_bytes, d.total_bytes) : 100) + '%' }"
              />
            </div>
            <span class="dl-state">
              {{ d.total_bytes
                ? `${percent(d.done_bytes, d.total_bytes)}% OF ${megabytes(d.total_bytes)}`
                : "DOWNLOADING…" }}
            </span>
          </template>
          <span v-else-if="d.state === 'done'" class="dl-state ok">
            ✓ DOWNLOADED{{ d.total_bytes ? ` — ${megabytes(d.total_bytes)}` : "" }}
          </span>
          <template v-else-if="d.state === 'error'">
            <span class="dl-state err">FAILED — {{ d.detail }}</span>
            <button class="retry" :disabled="busy" @click="retryDownloads">RETRY</button>
          </template>
        </div>
      </div>
      <p v-if="localActive && !downloading" class="ok-line">
        ✓ Local voice is set up — this gate closes by itself. A cloud key can
        be added any time in SETTINGS.
      </p>
      <button v-if="pendingLocal && localEntry?.ready" class="retry" :disabled="busy || downloading" @click="pickLocal">
        {{ downloading ? 'Preparing local engines…' : 'Use local engines' }}
      </button>
      <p v-if="error" class="remedy">{{ error }}</p>
    </template>
  </div>
</template>

<style scoped>
.engines { display: grid; gap: 12px; margin-bottom: 14px; }
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card {
  display: flex; flex-direction: column; gap: 6px; text-align: left; cursor: pointer;
  font-family: var(--sans); color: var(--ink);
  background: var(--bg1);
  border: 1px solid var(--line-strong);
  padding: 12px 14px;
}
.card.on { border-color: var(--cyan); box-shadow: none; }
.card:hover { border-color: var(--cyan-dim); }
.card-title { font-size: 13px; letter-spacing: normal; color: var(--cyan); }
.card-text { font-size: 12px; line-height: 1.6; color: var(--muted); }

.remedy { font-size: 11px; color: var(--amber); margin: 0; }
.ok-line { font-size: 11px; color: var(--green); margin: 0; }

.downloads { display: grid; gap: 8px; }
.dlrow { display: flex; align-items: center; gap: 10px; }
.dl-label { font-size: 11px; letter-spacing: normal; color: var(--muted); flex: none; }
.bar {
  flex: 1; height: 6px; background: var(--bg1);
  border: 1px solid var(--line-strong); overflow: hidden;
}
.fill { height: 100%; background: var(--cyan); transition: width 0.4s linear; }
.fill.pulse { animation: none; }
@keyframes dl-pulse { 0%, 100% { opacity: 0.35; } 50% { opacity: 0.9; } }
.dl-state { font-size: 11px; letter-spacing: normal; color: var(--cyan-dim); flex: none; }
.dl-state.ok { color: var(--green); }
.dl-state.err { color: var(--amber); }
.retry {
  font-family: var(--sans); font-size: 11px; letter-spacing: normal;
  color: var(--cyan); background: rgba(158, 188, 245, 0.06);
  border: 1px solid var(--line-strong); padding: 4px 10px; cursor: pointer;
}
@media (max-width: 520px) { .cards { grid-template-columns: minmax(0, 1fr); } .dlrow { flex-wrap: wrap; } }
</style>
