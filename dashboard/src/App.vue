<script setup lang="ts">
import "./styles/dashboard.css";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { cancelTranscript, getDevices, runDiagnostics, saveApiKey, setAgentMuted, setCharacter, setMode, setMuted, setPtt, setSettings, setVoiceMuted, speakText, stopPlayback, type DiagnosticChecks, togglePlaybackPause, interruptPlayback, skipUnheard, scheduleShutdown, cancelShutdown, postponeShutdown, requestHotkeyPermission } from "./api/client";
import type { InputDevice } from "./types";
import { replaySpeechText } from "./components/bubbleStatus";
import type { Character, Utterance } from "./types";
import ActivityLine from "./components/ActivityLine.vue";
import AgentTabs from "./components/AgentTabs.vue";
import VoicePersona from "./components/VoicePersona.vue";
import CharacterReadout from "./components/CharacterReadout.vue";
import ConversationLog from "./components/ConversationLog.vue";
import ConversationTelemetry from "./components/ConversationTelemetry.vue";
import DiagnosticChecklist from "./components/DiagnosticChecklist.vue";
import EngineChoice from "./components/EngineChoice.vue";
import SpeechSettings from "./components/SpeechSettings.vue";
import HudPanel from "./components/HudPanel.vue";
import Oscilloscope from "./components/Oscilloscope.vue";
import TurnHistory from "./components/TurnHistory.vue";
import SettingsView from "./components/SettingsView.vue";
import ShutdownBanner from "./components/ShutdownBanner.vue";
import { useTabStatus } from "./composables/useTabStatus";
import SpectrumBars from "./components/SpectrumBars.vue";
import StatusStrip from "./components/StatusStrip.vue";
import CompanionFloat from "./components/CompanionFloat.vue";
import VersionBadge from "./components/VersionBadge.vue";
import type { CueName } from "./composables/cueEvents";
import { useAudioCues } from "./composables/useAudioCues";
import { useBrowserAudio } from "./composables/useBrowserAudio";
import { useDaemonState } from "./composables/useDaemonState";
import { useMicStream } from "./composables/useMicStream";

const { status, utterances, utterancesFor, character, offline, viewedAgent, errors, selectAgent, dismissAgent, reorderAgents } =
  useDaemonState();

// Agents visibly "working": their live-activity line was updated in the
// last few seconds (tool running or THINKING between tools).
const THINKING_FRESH_S = 20;
const thinkingAgents = computed(() => {
  const activity = status.value?.activity ?? {};
  const now = Date.now() / 1000;
  return Object.entries(activity)
    .filter(([, a]) => a?.text && now - a.at < THINKING_FRESH_S)
    .map(([name]) => name);
});

const lastError = computed(() => errors.value[errors.value.length - 1] ?? null);
const errorCount = computed(() => errors.value.length);

const { prefs: cuePrefs, enabled: cuesEnabled } = useAudioCues(utterances, status, errorCount, utterancesFor);
const setCue = (name: CueName, value: boolean) => (cuePrefs.value.cues[name] = value);
const setHum = (patch: { recordingHum?: boolean; humNoise?: string; humVolume?: number }) =>
  Object.assign(cuePrefs.value, patch);

function eventTime(ts: number): string {
  const d = new Date(ts * 1000);
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}
const { level } = useMicStream();

const levelPercent = computed(() => `${Math.round(level.value * 100)}%`);
const levelDb = computed(() =>
  level.value > 0 ? `${(20 * Math.log10(level.value)).toFixed(1)} dB` : "−∞ dB",
);

// A dev instance is any daemon serving off the production port. The marker
// is deliberately confined to the logo block — the rest of the theme stays
// production-identical so prod colors can be tested on a local instance.
const props = withDefaults(defineProps<{ instancePort?: string }>(), {
  instancePort: () => window.location.port,
});
const isDevInstance = computed(() => props.instancePort !== "" && props.instancePort !== "9765");
const instanceLabel = computed(() => isDevInstance.value ? "DEV INSTANCE" : "");

// Controls: fire the POST, then let the next 400 ms poll reflect reality —
// no optimistic local state to get out of sync.
const swallow = () => {};
const toggleMute = () => setMuted(!status.value?.muted).catch(swallow);
const setSttMode = (mode: "batch" | "live") => setMode(mode).catch(swallow);
const setTtsMode = (mode: "batch" | "live") => setSettings({ tts_mode: mode }).catch(swallow);
const setSilence = (event: Event) =>
  setSettings({ end_silence_ms: Number((event.target as HTMLSelectElement).value) }).catch(swallow);
const setSensitivity = (event: Event) =>
  setSettings({ mic_sensitivity: Number((event.target as HTMLSelectElement).value) }).catch(swallow);
const setSmartTurn = (event: Event) =>
  setSettings({ smart_turn: Number((event.target as HTMLSelectElement).value) }).catch(swallow);

const changeCharacter = (patch: Partial<Character>) =>
  setCharacter({ ...patch, agent: viewedAgent.value ?? undefined }).catch(swallow);
// Per-conversation mute: toggles the VIEWED tab; the next poll reflects it.
const toggleAgentMute = () => {
  const agent = viewedAgent.value;
  if (!agent) return;
  const muted = (status.value?.muted_agents ?? []).includes(agent);
  setAgentMuted(agent, !muted).catch(swallow);
};
const setDetection = (mode: "auto" | "ptt") =>
  setSettings({ detection_mode: mode }).catch(swallow);
// The button toggles: playing this very bubble → stop it (the queue moves
// on by itself); otherwise queue a replay that outranks current playback.
const replay = (utterance: Utterance) => {
  if (status.value?.playing_utterance_id === utterance.id) {
    stopPlayback().catch(swallow);
    return;
  }
  speakText(
    replaySpeechText(utterance.text), utterance.id, viewedAgent.value ?? undefined,
  ).catch(swallow);
};
const cancel = (utterance: Utterance) => cancelTranscript(utterance.id).catch(swallow);

const unheard = computed(() =>
  utterances.value.filter((u) => u.role === "claude" && u.status.includes("unheard")),
);
const toggleVoiceMute = () => setVoiceMuted(!status.value?.voice_muted).catch(swallow);
// Catch up: unmute FIRST (or the replays would park as unheard again) —
// BOTH the global voice mute and this conversation's own mute — then
// queue every parked message in arrival order; the playback queue
// serializes them, each stoppable with its ⏹.
// Skip-all: the mirror of catch-up - settle the parked queue unplayed.
// One daemon call; the next status poll empties the counter.
const skipAll = () => skipUnheard(viewedAgent.value ?? undefined).catch(swallow);

async function catchUp() {
  await setVoiceMuted(false).catch(swallow);
  const agent = viewedAgent.value;
  if (agent && (status.value?.muted_agents ?? []).includes(agent)) {
    await setAgentMuted(agent, false).catch(swallow);
  }
  // Sequential awaits + interrupt:false — parallel POSTs can arrive out of
  // order and an interrupting replay would jump the queue, so a batch
  // catch-up must do neither (it played last-before-previous once).
  const parked = [...unheard.value].sort(
    (a, b) => (a.committed_at || a.started_at) - (b.committed_at || b.started_at),
  );
  for (const u of parked) {
    await speakText(replaySpeechText(u.text), u.id, undefined, { interrupt: false }).catch(swallow);
  }
}

// Push-to-talk: while the button (or the space bar) is physically held we
// renew the daemon's hold lease (it expires by itself if we die mid-hold).
let pttTimer: ReturnType<typeof setInterval> | undefined;
function startPtt() {
  if (pttTimer) return; // already holding (e.g. key auto-repeat)
  setPtt(true).catch(swallow);
  pttTimer = setInterval(() => setPtt(true).catch(swallow), 500);
}
function stopPtt() {
  if (!pttTimer) return;
  clearInterval(pttTimer);
  pttTimer = undefined;
  setPtt(false).catch(swallow);
}
function pttPress(event: PointerEvent) {
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  startPtt();
}

// Space = the talk button, but never while typing into a field.
function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}
function onKeyDown(event: KeyboardEvent) {
  if (event.code !== "Space" || isTypingTarget(event.target)) return;
  if (status.value?.detection_mode !== "ptt" || status.value?.muted) return;
  event.preventDefault(); // don't scroll / re-click focused buttons
  startPtt();
}
function onKeyUp(event: KeyboardEvent) {
  if (event.code !== "Space" || isTypingTarget(event.target)) return;
  stopPtt();
}
onMounted(() => {
  addEventListener("keydown", onKeyDown);
  addEventListener("keyup", onKeyUp);
});
onUnmounted(() => {
  removeEventListener("keydown", onKeyDown);
  removeEventListener("keyup", onKeyUp);
  clearInterval(pttTimer);
});

// API key setup: full-screen gate when unconfigured; later managed from
// the SETTINGS view (which swaps in for the comm log).
const keyInput = ref("");
const showSettings = ref(false);
// The gate must not blink away mid-verification OR right after a
// rejection: the daemon stores the candidate key while it live-checks it,
// so the polled api_key_set reads true for a few seconds even for a key
// about to be rejected — and stays stale for one more poll after the
// verdict. Both flags bridge those windows.
const firstContactVerifying = ref(false);
const firstContactFailed = ref(false);
// Which path the engine cards picked; the key form belongs to "cloud".
const gateMode = ref<"cloud" | "local">("cloud");
const setupSpeechSettings = ref(false);
// "Unconfigured" asks about a READY engine, not about a key: a local-only
// setup has no key at all. voice_ready is additive — an older daemon
// without it falls back to the key check.
// Browser-tab semantics (#101): closing the last tab must take its window
// with it. Without a viewed conversation the log would otherwise fall back
// to EVERY utterance and render a pane no tab owns.
const noTabs = computed(
  () => status.value != null && Object.keys(status.value.agents ?? {}).length === 0,
);
const unconfigured = computed(
  () =>
    status.value != null &&
    (!(status.value.voice_ready ?? status.value.api_key_set) ||
      firstContactVerifying.value ||
      firstContactFailed.value),
);
// Per-endpoint xAI checks: run automatically on key save, or on demand.
// Kept here (not in SettingsView) so the panel stays a dumb form — and
// shared with the first-contact gate, which accepts a key ONLY once the
// daemon verified it against the live service.
const keyChecks = ref<DiagnosticChecks | null>(null);
const checksRunning = ref(false);
const keyError = ref("");
const saveKey = async (key: string): Promise<boolean> => {
  keyChecks.value = null;
  keyError.value = "";
  checksRunning.value = true;
  try {
    const result = await saveApiKey(key);
    keyChecks.value = result.checks ?? null;
    if (!result.ok) keyError.value = result.error ?? "the key failed verification";
    return result.ok;
  } catch {
    keyError.value = "cannot reach the daemon";
    return false;
  } finally {
    checksRunning.value = false;
  }
};
async function submitKey() {
  const key = keyInput.value.trim();
  if (key.length < 8) return;
  firstContactVerifying.value = true;
  firstContactFailed.value = false;
  try {
    const accepted = await saveKey(key);
    if (accepted) keyInput.value = "";
    firstContactFailed.value = !accepted;
  } finally {
    firstContactVerifying.value = false;
  }
}
// While checks run, the daemon reports verdicts as they land — show those;
// once the save resolves, its authoritative result takes over.
const visibleChecks = computed(() =>
  keyChecks.value ?? (checksRunning.value ? status.value?.diagnostic_checks ?? null : null),
);
const runChecks = async () => {
  keyChecks.value = null;
  checksRunning.value = true;
  try {
    keyChecks.value = await runDiagnostics();
  } catch {
    keyChecks.value = null;
  } finally {
    checksRunning.value = false;
  }
};

const setLanguage = (event: Event) =>
  setSettings({ language: (event.target as HTMLSelectElement).value }).catch(swallow);

// Microphone picker: the list refreshes when the select gains focus, so a
// freshly connected headset shows up without reloading the page.
const devices = ref<InputDevice[]>([]);
const loadDevices = () => getDevices().then((d) => (devices.value = d)).catch(swallow);
onMounted(loadDevices);
// Opening SETTINGS re-enumerates: /devices spawns a fresh PortAudio in a
// subprocess, so a mic plugged in after daemon start appears the moment
// the panel opens - not only after the manual refresh button.
watch(showSettings, (open) => { if (open) loadDevices(); });
const browserAudio = useBrowserAudio();
useTabStatus(status);
// Tab honesty (#30): mute releases the capture (Chrome's red dot goes
// away), unmute re-acquires it - permission is already granted, so no
// gesture is needed on the way back.
watch(
  () => status.value?.muted ?? false,
  (muted) => {
    if (muted) browserAudio.suspendMic();
    else browserAudio.resumeMic().catch(swallow);
  },
);
// Playback lives in ONE of two places: the browser tab (output=browser)
// or a daemon-side system player (output=system). The transport buttons
// drive both - whichever holds the clip reacts, the other no-ops.
const daemonPaused = ref(false);
const playbackPaused = computed(
  () => browserAudio.playbackPaused.value || daemonPaused.value,
);
const pausePlayback = async () => {
  browserAudio.pauseToggle();
  try {
    daemonPaused.value = (await togglePlaybackPause()).paused;
  } catch {
    /* daemon unreachable - the tab side already did what it could */
  }
};
// A new clip means the pause belonged to the previous one - reset, or the
// playing bubble would show a resume icon for audio that is running.
watch(
  () => status.value?.playing_utterance_id ?? 0,
  () => {
    daemonPaused.value = false;
  },
);

const skipPlayback = () => {
  browserAudio.skip();
  daemonPaused.value = false;
  interruptPlayback().catch(swallow);
};
// The SPEAKER side needs no permission and no gesture — connect the WS
// lease the moment the page knows the tab is a nominated device, so
// Claude's first words (the first-contact greeting) can play at once.
let autoConnectTried = false;
watch(status, (s) => {
  if (autoConnectTried || !s) return;
  if (s.input_device === "browser" || s.output_device === "browser") {
    autoConnectTried = true; // once per page load; the banner is the retry
    browserAudio.connect().catch(swallow);
  }
});
// The banner covers what still needs the USER: the mic permission (and a
// reconnect after a failed auto-connect).
const tabAudioNeeded = computed(
  () =>
    !!status.value &&
    !unconfigured.value &&
    ((status.value.input_device === "browser" && !browserAudio.micLive.value) ||
      (status.value.output_device === "browser" && !browserAudio.active.value)),
);
const tabAudioRoles = computed(() => {
  const roles = [];
  if (status.value?.input_device === "browser" && !browserAudio.micLive.value) {
    roles.push("microphone");
  }
  if (status.value?.output_device === "browser" && !browserAudio.active.value) {
    roles.push("speaker");
  }
  return roles.join(" and ");
});
async function enableTabAudio() {
  try {
    if (status.value?.input_device === "browser") await browserAudio.enable();
    else await browserAudio.connect();
  } catch {
    // the reason is already in browserAudio.error, shown on the banner
  }
}
// The tab connection serves both directions — tear it down only when
// NEITHER side uses the tab anymore.
function dropTabUnlessNeeded() {
  const s = status.value;
  if (s?.input_device !== "browser" && s?.output_device !== "browser") {
    browserAudio.disable();
  }
}
async function pickMic(name: string) {
  if (name !== "browser") {
    await setSettings({ input_device: name }).catch(swallow);
    dropTabUnlessNeeded();
    return;
  }
  // The picker click is our user gesture — getUserMedia is allowed here.
  try {
    await browserAudio.enable();
    await setSettings({ input_device: "browser" });
  } catch {
    // Permission or lease refused: stay on the system default rather than
    // pointing the daemon at a microphone that will never send a frame.
    await setSettings({ input_device: "" }).catch(swallow);
  }
}
// Ticking countdown for the shutdown banner (0.5 s poll keeps it honest).
const nowTick = ref(Date.now());
const shutdownTimer = setInterval(() => (nowTick.value = Date.now()), 500);
onUnmounted(() => clearInterval(shutdownTimer));
const shutdownSeconds = computed(() => {
  const at = status.value?.shutdown_at ?? 0;
  if (!at) return null;
  return Math.max(0, Math.ceil(at - nowTick.value / 1000));
});
const shutdownLabel = computed(() => {
  const s = shutdownSeconds.value ?? 0;
  return s >= 60 ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}` : `${s}s`;
});

// The GRANT button in settings: the one other moment macOS may prompt (#97).
const grantHotkeys = () => requestHotkeyPermission().catch(swallow);
// One action at a time: the daemon merges, refuses collisions, and the
// next snapshot carries the stored map plus any problem to show (#104).
const setHotkey = (action: string, chord: string) => setSettings({ hotkeys: { [action]: chord } }).catch(swallow);

async function pickOutput(value: string) {
  if (value !== "browser") {
    await setSettings({ output_device: "system" }).catch(swallow);
    dropTabUnlessNeeded();
    return;
  }
  try {
    await browserAudio.connect(); // lease only — the speaker needs no mic permission
    await setSettings({ output_device: "browser" });
  } catch {
    await setSettings({ output_device: "system" }).catch(swallow);
  }
}

const SILENCE_OPTIONS = [800, 1500, 2000, 3000, 4000];
// User terms for the VAD speech threshold (never raw RMS): LOW for noisy
// rooms (mic needs a clear voice), HIGH for quiet rooms / soft speakers.
const SENSITIVITY_OPTIONS: Array<[number, string]> = [
  [0, "MIN"], [25, "LOW"], [50, "MID"], [75, "HIGH"], [100, "MAX"],
];
const SMART_TURN_OPTIONS = [0, 0.5, 0.7, 0.9];
// Languages supported by the Grok voice API (same set as the legacy UI).
const LANGUAGES: Record<string, string> = {
  "": "AUTO-DETECT",
  en: "ENGLISH",
  pl: "POLSKI",
  de: "DEUTSCH",
  es: "ESPAÑOL",
  fr: "FRANÇAIS",
  "pt-BR": "PORTUGUÊS (BR)",
  it: "ITALIANO",
  ja: "日本語",
  zh: "中文",
};
</script>

<template>

  <!-- First contact: the HUD itself is the demo — live scopes prove the
       mic works, API-dependent sections sit dimmed behind the key prompt. -->
  <div v-if="unconfigured" class="setup-overlay" role="dialog" aria-modal="true" aria-labelledby="setup-title">
    <div class="setup-box" :class="{ 'speech-recovery-box': setupSpeechSettings }">
      <div id="setup-title" class="setup-title">Welcome to Noisy Studio</div>
      <!-- Engine first, key second (#36/#37): the cards decide whether the
           key form below applies at all. -->
      <button class="ctl" @click="setupSpeechSettings = !setupSpeechSettings">
        {{ setupSpeechSettings ? 'Back to setup' : 'Speech settings and recovery' }}
      </button>
      <SpeechSettings v-if="setupSpeechSettings" @configure="setupSpeechSettings = false" />
      <template v-else>
      <EngineChoice @mode="gateMode = $event" />
      <!-- The welcome pitch has done its job the moment a key is submitted:
           from then on the box is a verification panel, and every saved
           line keeps it on-screen even with seven failing checks. It folds
           away (grid-rows collapse) instead of vanishing in one frame. -->
      <div
        v-show="gateMode === 'cloud'"
        class="setup-pitch"
        :class="{ collapsed: checksRunning || !!visibleChecks || firstContactFailed }"
      >
        <div class="setup-pitch-inner">
          <p class="setup-text">
            Talk to your agent out loud — it hears you, answers through your speakers,
            and this console shows the whole conversation live. The oscilloscope
            below is already listening to your mic.
          </p>
          <p class="setup-text">
            All it needs is an xAI API key, and it runs on <b>pennies</b>:
            listening costs <b>$0.10 per hour</b>, a spoken reply is a fraction of
            a cent. Create a key at
            <a href="https://console.x.ai" target="_blank" rel="noreferrer">console.x.ai</a>
            and paste it here:
          </p>
        </div>
      </div>
      <div v-show="gateMode === 'cloud'" class="setup-row">
        <input
          v-model="keyInput"
          type="password"
          class="setup-input" aria-label="xAI API key" autofocus
          placeholder="xai-…"
          :disabled="checksRunning"
          @keyup.enter="submitKey"
        />
        <button class="ctl" :disabled="checksRunning" @click="submitKey">
          {{ checksRunning ? "VERIFYING…" : "CONNECT" }}
        </button>
      </div>
      <!-- Verify-then-commit: the key is accepted only after the daemon
           confirmed it against the live service — a dead key must fail
           HERE, not utterances later. Verdicts land row by row, live. -->
      <p v-if="keyError" class="setup-error">✗ {{ keyError.toUpperCase() }}</p>
      <DiagnosticChecklist v-if="visibleChecks" :checks="visibleChecks" class="setup-checks" />
      <!-- Honest next steps: usually it's the key, sometimes it's xAI. -->
      <p v-if="firstContactFailed && !checksRunning" class="setup-text setup-hint">
        This key doesn't seem right — xAI rejected it. Most often the key is
        mistyped, expired, or lacks permissions: check it at
        <a href="https://console.x.ai" target="_blank" rel="noreferrer">console.x.ai</a>
        and paste it again. In fairness, it can also be xAI itself having a
        moment (<a href="https://status.x.ai" target="_blank" rel="noreferrer">status.x.ai</a>)
        — in that case the very same key might pass if you retry in a while.
      </p>
      </template>
    </div>
  </div>

  <div class="hud" :inert="unconfigured">
    <!-- Graceful shutdown (#35): D5 bar picked in Storybook. -->
    <ShutdownBanner
      v-if="shutdownSeconds !== null"
      class="shutdown-bar"
      :label="shutdownLabel"
      @restart-now="scheduleShutdown(0).catch(swallow)"
      @postpone="postponeShutdown(60).catch(swallow)"
      @cancel="cancelShutdown().catch(swallow)"
    />
    <button v-if="tabAudioNeeded" class="tabaudio" @click="enableTabAudio">
      🎙 ENABLE TAB AUDIO — this tab is your {{ tabAudioRoles }}; click once to activate
      <span v-if="browserAudio.error.value" class="taberr">{{ browserAudio.error.value }}</span>
    </button>
        <header class="topbar">
          <div class="topbar-logobox">
            <div class="logo" :class="{ dev: isDevInstance }">
              <svg width="46" height="46" viewBox="0 0 46 46" aria-hidden="true">
                <rect x="4" y="4" width="38" height="38" rx="11" fill="var(--surface-hover)" />
                <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <line x1="17" y1="20" x2="17" y2="26" />
                  <line x1="21" y1="16" x2="21" y2="30" />
                  <line x1="25" y1="19" x2="25" y2="27" />
                  <line x1="29" y1="21" x2="29" y2="25" />
                </g>
              </svg>
              <div>
                <div class="title">Noisy Studio</div>
                <div class="sub">Your voice, in the workflow</div>
              </div>
            </div>
            <div v-if="instanceLabel" class="devbadge" title="Development instance — not production">{{ instanceLabel }}</div>
          </div>

          <div class="sysstate">
            <button class="ctl header-action settings-toggle" :aria-pressed="showSettings" @click="showSettings = !showSettings">Settings</button>
            <button
              class="ctl header-action header-mute" :disabled="offline" :aria-pressed="!!status?.voice_muted"
              :title="status?.voice_muted ? 'Resume agent playback' : 'Mute playback and keep replies for later'"
              :class="{ muted: status?.voice_muted, locked: unconfigured }"
              @click="toggleVoiceMute"
            >
              {{ status?.voice_muted ? "Unmute all agents" : "Mute all agents" }}
            </button>
          </div>
        </header>
    <div class="cols">
      <div class="col-left">
        <div class="microphone-actions" :class="{ 'with-ptt': status?.detection_mode === 'ptt' }">
          <!-- Panic-sized mute: quick muting must not require aiming at a
               tiny control, so it gets widget-scale real estate up top. -->
          <button class="bigmute" :disabled="offline" :aria-label="status?.muted ? 'Unmute microphone' : 'Mute microphone'" :aria-pressed="!!status?.muted" :class="{ muted: status?.muted, locked: unconfigured }" @click="toggleMute">
            <span class="bm-label">{{ offline ? "Microphone unavailable" : status?.muted ? "Microphone muted" : status?.detection_mode === "ptt" ? "Mute mic" : "Mute microphone" }}</span>
            <span class="bm-sub">{{ offline ? "Waiting for the voice service" : status?.muted ? "Click to unmute" : status?.detection_mode === "ptt" ? "Click to pause" : "Listening · click to pause" }}</span>
          </button>
          <!-- Holding while muted records nothing — lock the button and say
               why instead of silently eating the press. -->
          <button
            v-if="status?.detection_mode === 'ptt'"
            class="bigmute talk"
            :class="{ held: status?.ptt_held }"
            :disabled="status?.muted || offline"
            @pointerdown="pttPress"
            @pointerup="stopPtt"
            @pointercancel="stopPtt"
          >
            <span class="bm-label">
              {{ status?.muted ? "⊘ LOCKED" : status?.ptt_held ? "◉ ON AIR" : "Hold to talk" }}
            </span>
            <span class="bm-sub">
              {{ status?.muted ? "MIC MUTED — UNMUTE FIRST"
                 : status?.ptt_held ? (status?.ptt_toggle_key ? `LIVE — ${status.ptt_toggle_key.toUpperCase()} OR TAP HERE TO END` : "RELEASE TO SEND")
                 : "or hold Space" }}
            </span>
          </button>
        </div>
        <HudPanel index="01" title="Microphone" class="flexpanel">
          <Oscilloscope :level="level" />
          <div class="dbrow">
            <span class="lbl">Level</span>
            <span class="dbbar"><i :style="{ width: levelPercent }" /></span>
            <span class="val">{{ levelDb }}</span>
          </div>
        </HudPanel>
        <HudPanel index="02" title="Audio spectrum" class="spectrum-panel">
          <SpectrumBars :level="level" />
        </HudPanel>
        <HudPanel index="03" title="Audio controls" :class="{ locked: unconfigured }">
          <div class="controls">
            <!-- The two mode toggles sit together: same choice, two
                 directions (Claude's voice out vs your voice in). -->
            <div class="ctlrow" title="Agent speech: batch renders the whole clip first, live streams as it synthesizes">
              <span class="lbl">Agent speech</span>
              <button class="ctl small" :class="{ on: (status?.speech_output_mode ?? status?.tts_mode) === 'batch' }" @click="setTtsMode('batch')">Batch</button>
              <button class="ctl small" :class="{ on: (status?.speech_output_mode ?? status?.tts_mode) === 'live' }" :disabled="status?.speech_live_available === false" :title="status?.speech_live_available === false ? 'This voice engine generates complete replies before playback.' : undefined" @click="setTtsMode('live')">Live</button>
            </div>
            <div class="ctlrow" title="Your speech: batch transcribes after you finish, live transcribes while you talk when supported by your engine">
              <span class="lbl">Your speech</span>
              <button class="ctl small" :class="{ on: (status?.recognition_mode ?? status?.mode) === 'batch' }" @click="setSttMode('batch')">Batch</button>
              <button class="ctl small" :class="{ on: (status?.recognition_mode ?? status?.mode) === 'live' }" :disabled="status?.recognition_live_available === false" :title="status?.recognition_live_available === false ? 'This recognition engine transcribes after you finish speaking.' : undefined" @click="setSttMode('live')">Live</button>
            </div>
            <div class="ctlrow" title="Subtle blips on conversation events; pick which in Settings">
              <span class="lbl">Sound cues</span>
              <button class="ctl small" :class="{ on: cuesEnabled }" @click="cuesEnabled = true">On</button>
              <button class="ctl small" :class="{ on: !cuesEnabled }" @click="cuesEnabled = false">Off</button>
            </div>
            <div class="ctlcol" title="How your turn ends: auto = the VAD detects silence; push to talk = you hold the big button">
              <span class="lbl">Turn detection</span>
              <div class="ctlbtns">
                <button class="ctl small" :class="{ on: status?.detection_mode === 'auto' }" @click="setDetection('auto')">Auto</button>
                <button class="ctl small" :class="{ on: status?.detection_mode === 'ptt' }" @click="setDetection('ptt')">Push to talk</button>
              </div>
            </div>
            <div class="ctlrow">
              <span class="lbl">End silence</span>
              <select class="ctl small" aria-label="End silence" :value="status?.end_silence_ms" @change="setSilence">
                <option v-for="ms in SILENCE_OPTIONS" :key="ms" :value="ms">{{ (ms / 1000).toFixed(1) }}s</option>
              </select>
            </div>
            <div class="ctlrow" title="Noise gate: how loud a voice must be to trip the mic. Lower it in a noisy room (café, open office) so background sound stops triggering recordings.">
              <span class="lbl">Sensitivity</span>
              <select class="ctl small" aria-label="Microphone sensitivity" :value="status?.mic_sensitivity ?? 50" @change="setSensitivity">
                <option v-for="[value, label] in SENSITIVITY_OPTIONS" :key="value" :value="value">{{ label }}</option>
              </select>
            </div>
            <div class="ctlrow">
              <span class="lbl">Smart turn</span>
              <select class="ctl small" aria-label="Smart turn" :value="status?.smart_turn" @change="setSmartTurn">
                <option v-for="v in SMART_TURN_OPTIONS" :key="v" :value="v">{{ v === 0 ? "Off" : v.toFixed(1) }}</option>
              </select>
            </div>
            <div class="ctlrow" title="Language for speech recognition and synthesis; auto-detect handles mixed Polish/English">
              <span class="lbl">Language</span>
              <select class="ctl small" aria-label="Language" :value="status?.language ?? ''" @change="setLanguage">
                <option v-for="(name, code) in LANGUAGES" :key="code" :value="code">{{ name }}</option>
              </select>
            </div>
          </div>
        </HudPanel>
        <!-- Global, machine-wide cost/state: deliberately OUTSIDE the
             conversation frame — the daemon meters all conversations. -->
        <HudPanel index="05" title="Session usage">
          <StatusStrip :status="status" :offline="offline" />
        </HudPanel>
      </div>

      <div class="col-mid" :class="{ locked: unconfigured }">

        <HudPanel v-if="showSettings" index="08" title="Settings">
          <button class="settings-x" title="Close settings" @click="showSettings = false">✕</button>
          <SettingsView
            :api-key-hint="status?.api_key_hint ?? ''"
            :devices="devices"
            :browser-audio="status?.browser_audio ?? false"
            :selected-device="status?.input_device ?? ''"
            :output-device="status?.output_device ?? 'system'"
            :cue-prefs="cuePrefs"
            :hotkeys="status?.hotkeys ?? null"
            :checks="visibleChecks"
            :checks-running="checksRunning"
            @save="saveKey"
            @pick-device="pickMic"
            @pick-output="pickOutput"
            @set-hotkey="setHotkey"
            @grant-hotkeys="grantHotkeys"
            @refresh-devices="loadDevices"
            @toggle-cue="setCue"
            @set-hum="setHum"
            @run-checks="runChecks"
          />
        </HudPanel>
        <!-- Tabs live OUTSIDE the conversation frame, protruding above it
             like folder tabs — the frame reads as "the selected tab's
             window", and everything inside starts one line higher. -->
        <div v-if="!showSettings" class="tabsbar">
          <AgentTabs
            :agents="status?.agent_labels ?? {}"
            :meta="status?.agents_meta ?? null"
            :active="status?.active_agent ?? null"
            :viewed="viewedAgent"
            :speaking="status?.speaking_agents ?? []"
            :thinking="thinkingAgents"
            :queued="status?.queued_by_agent ?? {}"
            :muted="status?.muted_agents ?? []"
            @select="selectAgent"
            @dismiss="dismissAgent"
            @reorder="reorderAgents"
          />
        </div>
        <HudPanel v-if="!showSettings" class="convo-panel" :aria-label="status?.agent_labels?.[viewedAgent ?? ''] ?? 'Conversation'">
          <p v-if="offline" class="conversation-connection" role="status">Reconnecting to the voice service…</p>
          <p v-else-if="noTabs" class="conversation-connection convo-empty" role="status">
            No open conversations. Start or resume a Claude Code or Codex session and its tab appears here.
          </p>
          <!-- Everything below the tabs is THIS conversation: the log on
               the left, and the conversation-scoped rail (voice avatar,
               character, turn timeline) inside the same frame on the
               right. Global widgets live in the left column instead. -->
          <div v-if="!noTabs" class="convo-body">
            <div class="convo-main">
              <!-- Catch-up spans the bubbles column only, like telemetry —
                   never the rail. -->
              <div v-if="unheard.length" class="catchup-row">
                <button class="ctl catchup" @click="catchUp">
                  ▶ Catch up ({{ unheard.length }} unheard)
                </button>
                <button class="ctl skipall" title="Dismiss all unheard messages without playing them" @click="skipAll">
                  Skip all
                </button>
              </div>
              <ConversationLog
                :utterances="utterances"
                :speaker-colors="status?.speaker_colors ?? {}"
                :speaker-labels="status?.speaker_labels ?? {}"
                :playing-id="status?.playing_utterance_id ?? 0"
                :playback-paused="playbackPaused"
                :activity="status?.activity?.[viewedAgent ?? ''] ?? null"
                @replay="replay"
                @cancel="cancel"
                @pause="pausePlayback"
                @skip="skipPlayback"
              />
              <ConversationTelemetry
                :stt-latency-ms="status?.stt_latency_ms ?? null"
                :tts-latency-ms="status?.tts_latency_ms ?? null"
                :user-cost-usd="status?.session_cost_usd.user ?? 0"
                :claude-cost-usd="status?.session_cost_usd.claude ?? 0"
                :stt-seconds="status?.usage.stt_seconds ?? 0"
                :tts-chars="status?.usage.tts_chars ?? 0"
              />
            </div>
            <aside class="convo-rail">
              <section class="railbox">
                <VoicePersona
                  :voice="character?.voice ?? ''"
                  :voice-labels="status?.voice_labels"
                  :speaking="!!viewedAgent && (status?.speaking_agents ?? []).includes(viewedAgent)"
                  :muted="!!viewedAgent && (status?.muted_agents ?? []).includes(viewedAgent)"
                  @change="(v) => changeCharacter({ voice: v })"
                  @toggle-mute="toggleAgentMute"
                />
              </section>
              <section class="railbox">
                <div class="railtitle">Character</div>
                <CharacterReadout v-if="character" :character="character" @change="changeCharacter" />
                <p v-else class="todo">Choose a conversation to see its character</p>
              </section>
              <section class="railbox">
                <div class="railtitle">Turn history</div>
                <TurnHistory :utterances="utterances" />
              </section>
            </aside>
          </div>
        </HudPanel>
      </div>

    </div>

    <footer>
      <span>Service <b :class="offline ? 'bad' : 'ok'">{{ offline ? "OFFLINE" : "ONLINE" }}</b></span>
      <span v-if="status?.input_device === 'browser'">
        TAB MIC <b :class="status?.tab_audio ? 'ok' : 'bad'">{{ status?.tab_audio ? "Live" : "NO TAB" }}</b>
      </span>
      <span>Recognition <b>{{ (status?.recognition_mode ?? status?.mode)?.toUpperCase() ?? "—" }}</b></span>
      <span>Language <b>{{ status?.language || "Auto" }}</b></span>
      <span>Queue <b>{{ status?.queued ?? "—" }}</b></span>
      <span v-if="lastError" class="lasterr" :title="`${lastError.detail} (${errors.length} error(s) this session)`">
        ⚠ {{ eventTime(lastError.ts) }} {{ lastError.kind.toUpperCase() }} · {{ lastError.detail }}
      </span>
      <!-- Right edge order: version second-from-corner, system status in
           the corner itself. -->
      <CompanionFloat style="margin-left: auto" />
      <VersionBadge :daemon-version="status?.version" :latest-version="status?.latest_version" :dev-instance="isDevInstance" />
      <span>{{ offline ? "Connection lost" : lastError ? "Needs attention" : "Ready" }}</span>
    </footer>
  </div>
</template>
