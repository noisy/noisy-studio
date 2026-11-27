<script setup lang="ts">
import "./styles/dashboard.css";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { cancelTranscript, getDevices, runDiagnostics, saveApiKey, setAgentMuted, setMode, setMuted, setPtt, setSettings, setVoiceMuted, speakText, stopPlayback, type DiagnosticChecks, togglePlaybackPause, interruptPlayback, scheduleShutdown, cancelShutdown, postponeShutdown, requestHotkeyPermission, requestDictationPermission } from "./api/client";
import type { InputDevice } from "./types";
import { replaySpeechText } from "./components/bubbleStatus";
import type { Character, Utterance } from "./types";
import ActivityLine from "./components/ActivityLine.vue";
import AgentTabs from "./components/AgentTabs.vue";
import ColumnResizer from "./components/ColumnResizer.vue";
import { useColumnWidth } from "./composables/useColumnWidth";
import CatchUpBar from "./components/CatchUpBar.vue";
import VoicePersona from "./components/VoicePersona.vue";
import { provideTaskProgress } from "./composables/useTaskProgress";
provideTaskProgress();
import ConversationLog from "./components/ConversationLog.vue";
import ConversationTelemetry from "./components/ConversationTelemetry.vue";
import DiagnosticChecklist from "./components/DiagnosticChecklist.vue";
import EngineChoice from "./components/EngineChoice.vue";
import SpeechSettings from "./components/SpeechSettings.vue";
import HudPanel from "./components/HudPanel.vue";
import HeaderVoiceControls from "./components/HeaderVoiceControls.vue";
import TurnHistory from "./components/TurnHistory.vue";
import AudioControls from "./components/AudioControls.vue";
import type { AudioChange } from "./components/audioControls";
import { useAgentActivity } from "./composables/useAgentActivity";
import StageLive from "./components/StageLive.vue";
import TaskProgressPanel from "./components/task-progress/TaskProgressPanel.vue";
import TaskReviewPage from "./components/task-progress/TaskReviewPage.vue";
import { reviewPageTarget } from "./components/task-progress/reviewPage";
const reviewPage = reviewPageTarget(window.location.search);
const taskReviewOpen = ref(!!reviewPage);
function leaveReviewPage() {
  const url = new URL(window.location.href);
  for (const key of ["review_agent", "review_task", "review_revision"]) url.searchParams.delete(key);
  window.location.assign(url.href);
}
import SettingsView from "./components/SettingsView.vue";
import ShutdownBanner from "./components/ShutdownBanner.vue";
import { useTabStatus } from "./composables/useTabStatus";
import CompanionFloat from "./components/CompanionFloat.vue";
import VersionBadge from "./components/VersionBadge.vue";
import type { CueName } from "./composables/cueEvents";
import { useAudioCues } from "./composables/useAudioCues";
import { useDaemonState } from "./composables/useDaemonState";
import { useMicStream } from "./composables/useMicStream";
import { useUnheardBacklog } from "./composables/useUnheardBacklog";

const { status, utterances, allUtterances, utterancesFor, character, characterPending, characterError, changeCharacter, offline, viewedAgent, errors, clearErrors, selectAgent, dismissAgent, reorderAgents } =
  useDaemonState();

// Live pulse, the list's Working section and what each agent is doing.
const { thinking: thinkingAgents, activityText } = useAgentActivity(status);
// Left column: the conversation list and machine-global controls.
const leftColumn = useColumnWidth();

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
// Per-conversation mute: toggles the VIEWED tab; the next poll reflects it.
const toggleAgentMute = () => {
  const agent = viewedAgent.value;
  if (!agent) return;
  const muted = (status.value?.muted_agents ?? []).includes(agent);
  setAgentMuted(agent, !muted).catch(swallow);
};
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

const toggleVoiceMute = () => setVoiceMuted(!status.value?.voice_muted).catch(swallow);
const { unheard, catchUp, skipAll, summarize, canSummarize } = useUnheardBacklog(status, utterances, viewedAgent);

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

// Space = the talk button, but never while typing into a field.
function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}
function onKeyDown(event: KeyboardEvent) {
  if (taskReviewOpen.value || event.code !== "Space" || isTypingTarget(event.target)) return;
  if (status.value?.detection_mode !== "ptt" || status.value?.muted) return;
  event.preventDefault(); // don't scroll / re-click focused buttons
  startPtt();
}
function onKeyUp(event: KeyboardEvent) {
  if (event.code !== "Space") return;
  stopPtt();
}
function releaseHiddenPtt() { if (document.hidden) stopPtt(); }
onMounted(() => {
  addEventListener("blur", stopPtt);
  document.addEventListener("visibilitychange", releaseHiddenPtt);
  addEventListener("keydown", onKeyDown);
  addEventListener("keyup", onKeyUp);
});
onUnmounted(() => {
  stopPtt();
  removeEventListener("blur", stopPtt);
  document.removeEventListener("visibilitychange", releaseHiddenPtt);
  removeEventListener("keydown", onKeyDown);
  removeEventListener("keyup", onKeyUp);
  clearInterval(pttTimer);
});

// API key setup: full-screen gate when unconfigured; later managed from
// the SETTINGS view (which swaps in for the comm log).
const keyInput = ref("");
const showSettings = ref(false);
const showStage = ref(false);
// Stage is opened from Settings > Appearance; leaving it returns focus to
// the Settings toggle, the nearest control that is always on screen.
const settingsToggle = ref<HTMLButtonElement | null>(null);
async function closeStage() {
  stopPtt();
  showStage.value = false;
  await nextTick();
  settingsToggle.value?.focus();
}
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

// Microphone picker: the list refreshes when the select gains focus, so a
// freshly connected headset shows up without reloading the page.
const devices = ref<InputDevice[]>([]);
const loadDevices = () => getDevices().then((d) => (devices.value = d)).catch(swallow);
onMounted(loadDevices);
// Opening SETTINGS re-enumerates: /devices spawns a fresh PortAudio in a
// subprocess, so a mic plugged in after daemon start appears the moment
// the panel opens - not only after the manual refresh button.
watch(showSettings, (open) => { if (open) loadDevices(); });
useTabStatus(status);
const playbackPaused = ref(false);
const pausePlayback = async () => {
  try { playbackPaused.value = (await togglePlaybackPause()).paused; }
  catch { /* daemon unreachable */ }
};
// A new clip means the pause belonged to the previous one - reset, or the
// playing bubble would show a resume icon for audio that is running.
watch(
  () => status.value?.playing_utterance_id ?? 0,
  () => {
    playbackPaused.value = false;
  },
);

const skipPlayback = () => {
  playbackPaused.value = false;
  interruptPlayback().catch(swallow);
};
async function pickMic(name: string) {
  await setSettings({ input_device: name }).catch(swallow);
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
const grantDictation = () => requestDictationPermission().catch(swallow);
// One action at a time: the daemon merges, refuses collisions, and the
// next snapshot carries the stored map plus any problem to show (#104).
const setHotkey = (action: string, chord: string) => setSettings({ hotkeys: { [action]: chord } }).catch(swallow);

function changeAudio({id,value}: AudioChange) {
  if (id === 'cues') { cuesEnabled.value = value === 'on'; return; }
  if (id === 'recognition') { setMode(value as 'batch' | 'live').catch(swallow); return; }
  const keys = {microphone:'input_device',language:'language',turn:'detection_mode',agent:'tts_mode',length:'max_utterance_ms',silence:'end_silence_ms',sensitivity:'mic_sensitivity',smart:'smart_turn'};
  const numeric = ['length','silence','sensitivity','smart'].includes(id);
  setSettings({[keys[id]]:numeric ? Number(value) : value}).catch(swallow);
}
</script>

<template>
  <TaskReviewPage v-if="reviewPage" :agent="reviewPage.agent" :task-id="reviewPage.taskId" :revision="reviewPage.revision" :status="status" :offline="offline" :utterances="allUtterances" @close="leaveReviewPage" @start-ptt="startPtt" @stop-ptt="stopPtt" />
  <template v-else>

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
            and this console shows the whole conversation live. The mic meter
            at the top is already listening to your mic.
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

    <!-- Graceful shutdown (#35): D5 bar picked in Storybook. -->
    <ShutdownBanner
      v-if="shutdownSeconds !== null"
      class="shutdown-bar"
      :style="showStage ? { position: 'fixed', top: 0, left: 0, right: 0, zIndex: 120 } : undefined"
      :label="shutdownLabel"
      @restart-now="scheduleShutdown(0).catch(swallow)"
      @postpone="postponeShutdown(60).catch(swallow)"
      @cancel="cancelShutdown().catch(swallow)"
    />
  <StageLive v-if="showStage && !unconfigured" :status="status" :utterances="allUtterances" :offline="offline" @exit="closeStage" />
  <div v-show="!showStage || unconfigured" class="hud" :inert="unconfigured">
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
            <!-- Sound in both directions, machine-wide: YOU · INPUT (meter +
                 one mic slot) and AGENTS · OUTPUT (mute all). -->
            <HeaderVoiceControls
              :status="status" :offline="offline" :level="level"
              @toggle-mute="toggleMute" @toggle-agents-mute="toggleVoiceMute"
              @ptt-start="startPtt" @ptt-stop="stopPtt"
            />
            <button ref="settingsToggle" class="ctl header-action settings-toggle" :aria-pressed="showSettings" @click="showSettings = !showSettings">Settings</button>
          </div>
        </header>
    <div class="cols" :style="{ '--left-column-width': leftColumn.width.value + 'px' }">
      <ColumnResizer :width="leftColumn.width.value" @resize="leftColumn.set" @reset="leftColumn.reset" />
      <div class="col-left">
        <!-- The conversations, grouped by project; ended sessions fold
             into Settled below. -->
        <AgentTabs
          class="convo-list"
          :agents="status?.agent_labels ?? {}"
          :meta="status?.agents_meta ?? null"
          :active="status?.active_agent ?? null"
          :viewed="viewedAgent"
          :speaking="status?.speaking_agents ?? []"
          :thinking="thinkingAgents"
          :activity="activityText"
          :queued="status?.queued_by_agent ?? {}"
          :muted="status?.muted_agents ?? []"
          @select="selectAgent"
          @dismiss="dismissAgent"
          @reorder="reorderAgents"
        />
        <TaskProgressPanel :status="status" :offline="offline" :utterances="allUtterances" @review-open="taskReviewOpen = $event" @start-ptt="startPtt" @stop-ptt="stopPtt" />
      </div>

      <div class="col-mid" :class="{ locked: unconfigured }">

        <HudPanel v-if="showSettings" index="08" title="Settings">
          <button class="settings-x" title="Close settings" @click="showSettings = false">✕</button>
          <SettingsView
            :api-key-hint="status?.api_key_hint ?? ''"
            :devices="devices"
            :selected-device="status?.input_device ?? ''"
            :cue-prefs="cuePrefs"
            :hotkeys="status?.hotkeys ?? null"
            :dictation="status?.dictation ?? null"
            :checks="visibleChecks"
            :checks-running="checksRunning"
            @save="saveKey"
            @pick-device="pickMic"
            @set-hotkey="setHotkey"
            @grant-hotkeys="grantHotkeys"
            @grant-dictation="grantDictation"
            @refresh-devices="loadDevices"
            @toggle-cue="setCue"
            @set-hum="setHum"
            @run-checks="runChecks"
            @open-stage="showStage = true"
          >
            <template #audio-controls><AudioControls :status="status" :devices="devices" :cues-enabled="cuesEnabled" @change="changeAudio" @refresh-devices="loadDevices" /></template>
          </SettingsView>
        </HudPanel>
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
              <CatchUpBar :count="unheard.length" :can-summarize="canSummarize" @catch-up="catchUp" @summarize="summarize" @skip="skipAll" />
              <ConversationLog
                :utterances="utterances"
                :history-trimmed="(status?.history_trimmed?.[viewedAgent ?? ''] ?? 0) > 0"
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
                  :key="viewedAgent ?? 'none'"
                  :character="character"
                  @character-change="changeCharacter"
                  :voice="character?.voice ?? ''"
                  :pending="characterPending"
                  :error="characterError"
                  :voice-labels="status?.voice_labels"
                  :speaking="!!viewedAgent && (status?.speaking_agents ?? []).includes(viewedAgent)"
                  :muted="!!viewedAgent && (status?.muted_agents ?? []).includes(viewedAgent)"
                  @change="(v) => changeCharacter({ voice: v })"
                  @toggle-mute="toggleAgentMute"
                />
              </section>
              <TaskProgressPanel v-if="viewedAgent" :agent="viewedAgent" :status="status" :offline="offline" :utterances="allUtterances" @review-open="taskReviewOpen = $event" @start-ptt="startPtt" @stop-ptt="stopPtt" />
              <section class="railbox">
                <div class="railtitle">Turn history</div>
                <TurnHistory :utterances="utterances"
                :history-trimmed="(status?.history_trimmed?.[viewedAgent ?? ''] ?? 0) > 0" />
              </section>
            </aside>
          </div>
        </HudPanel>
      </div>

    </div>

    <footer>
      <span>Service <b :class="offline ? 'bad' : 'ok'">{{ offline ? "OFFLINE" : "ONLINE" }}</b></span>
      <span>Recognition <b>{{ (status?.recognition_mode ?? status?.mode)?.toUpperCase() ?? "—" }}</b></span>
      <span>Language <b>{{ status?.language || "Auto" }}</b></span>
      <span>Queue <b>{{ status?.queued ?? "—" }}</b></span>
      <span v-if="lastError" class="lasterr" :title="`${lastError.detail} (${errors.length} error(s) this session)`">
        ⚠ {{ eventTime(lastError.ts) }} {{ lastError.kind.toUpperCase() }} · {{ lastError.detail }}
      </span>
      <button v-if="lastError" type="button" title="Clear warnings in this dashboard; diagnostic logs are kept" @click="clearErrors">Clear warnings</button>
      <!-- Right edge order: version second-from-corner, system status in
           the corner itself. -->
      <CompanionFloat style="margin-left: auto" />
      <VersionBadge :daemon-version="status?.version" :latest-version="status?.latest_version" :dev-instance="isDevInstance" />
      <span>{{ offline ? "Connection lost" : lastError ? "Needs attention" : "Ready" }}</span>
    </footer>
  </div>
  </template>
</template>
