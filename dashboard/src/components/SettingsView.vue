<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
import AppearanceSettings from "./AppearanceSettings.vue";

// The panel got crowded - a toolbar splits it into four homes. AUDIO is
// first: it's what gets touched mid-session.
const TABS = ["AUDIO", "SOUNDS", "HOTKEYS", "APPEARANCE", "SPEECH", "SYSTEM"] as const;
const tab = ref<(typeof TABS)[number]>("AUDIO");
const audioSection = ref<HTMLElement | null>(null);
async function openAudioControls() {
  tab.value = 'AUDIO';
  await nextTick();
  audioSection.value?.focus();
  audioSection.value?.scrollIntoView?.({block:'nearest'});
}
defineExpose({openAudioControls});

import type { DiagnosticChecks } from "../api/client";
import type { InputDevice, HotkeyState } from "../types";
import { CUE_LABELS, type CuePrefs } from "../composables/useAudioCues";
import { HUM_NOISES, startRecordingHum, stopRecordingHum } from "../composables/cueSounds";
import type { CueName } from "../composables/cueEvents";
import { playCue } from "../composables/cueSounds";
import DiagnosticChecklist from "./DiagnosticChecklist.vue";
import HotkeysSettings, { type HotkeyBinding, type HotkeyPane } from "./HotkeysSettings.vue";
import { useKeyCapture } from "../composables/useKeyCapture";
import SpeechSettings from "./SpeechSettings.vue";

const props = withDefaults(
  defineProps<{
    apiKeyHint: string;
    devices?: InputDevice[];
    selectedDevice?: string;
    cuePrefs?: CuePrefs | null;
    hotkeys?: HotkeyState | null;
    checks?: DiagnosticChecks | null;
    checksRunning?: boolean;
  }>(),
  {
    devices: () => [], selectedDevice: "", cuePrefs: null,
    hotkeys: null,
    checks: null, checksRunning: false,
  },
);
// Settings > Hotkeys (#104): the daemon's action map rendered as two panes;
// a click on a field captures the next chord from THIS window.
const HOTKEY_LABELS: Record<string, string> = {
  hold: "Hold", toggle: "Toggle", scratch: "Scratch", tab1: "Tab 1", tab2: "Tab 2", tab3: "Tab 3", tab4: "Tab 4",
};
const binding = (action: string): HotkeyBinding => ({
  action,
  label: HOTKEY_LABELS[action],
  chord: props.hotkeys?.stored?.[action] ?? "",
  problem: props.hotkeys?.problems?.[action],
});
const talkPane = computed<HotkeyPane>(() => ({
  title: "Push to talk",
  caption: "Works in any app. Hold opens the mic while held; toggle opens and closes on a press; scratch drops the recording in progress.",
  bindings: ["hold", "toggle", "scratch"].map(binding),
}));
const tabsPane = computed<HotkeyPane>(() => ({
  title: "…to a specific tab",
  caption: "Toggle aimed at one conversation, counted left to right. Press again to close; another tab's key hands the mic over.",
  bindings: ["tab1", "tab2", "tab3", "tab4"].map(binding),
}));
const appPane: HotkeyPane = {
  title: "Companion window",
  bindings: [
    { action: "ghost", label: "Ghost mode", chord: "ctrl+alt+g", readonly: true },
    { action: "reload", label: "Reload windows", chord: "ctrl+alt+r", readonly: true },
  ],
};
const capture = useKeyCapture((action, result) => {
  if (result.kind === "chord") emit("setHotkey", action, result.chord);
  else if (result.kind === "clear") emit("setHotkey", action, "");
});
const emit = defineEmits<{
  save: [key: string];
  pickDevice: [name: string];
  setHotkey: [action: string, chord: string];
  grantHotkeys: [];
  refreshDevices: [];
  toggleCue: [name: CueName, value: boolean];
  setHum: [patch: { recordingHum?: boolean; humNoise?: string; humVolume?: number }];
  runChecks: [];
}>();

const cueNames = Object.keys(CUE_LABELS) as CueName[];

let humPreviewTimer: ReturnType<typeof setTimeout> | undefined;
function previewHum(noise: string, volume: number) {
  clearTimeout(humPreviewTimer);
  startRecordingHum(noise as never, volume);
  humPreviewTimer = setTimeout(stopRecordingHum, 1500);
}

const keyInput = ref("");
const editing = ref(false);

function submit() {
  const key = keyInput.value.trim();
  if (key.length < 8) return;
  emit("save", key);
  keyInput.value = "";
  editing.value = false;
}
</script>

<template>
  <div class="settings">
    <nav class="toolbar">
      <button
        v-for="t in TABS" :key="t" class="tabbtn" :class="{ on: tab === t }"
        :aria-pressed="tab === t" @click="tab = t"
      >{{ t.charAt(0) + t.slice(1).toLowerCase() }}</button>
    </nav>

    <AppearanceSettings v-if="tab === 'APPEARANCE'" />

    <HotkeysSettings
      v-if="tab === 'HOTKEYS'"
      :permission="hotkeys?.permission ?? 'unknown'"
      :talk="talkPane"
      :tabs="tabsPane"
      :app="appPane"
      :capturing="capture.capturing.value"
      @grant="emit('grantHotkeys')"
      @capture="capture.start"
      @clear="(action) => emit('setHotkey', action, '')"
    />

    <template v-if="tab === 'AUDIO'">
    <div ref="audioSection" tabindex="-1" aria-label="Audio controls"><slot name="audio-controls">
    <!-- Microphone first: switched far more often than the API key. -->
    <section class="sec">
      <div class="keyrow">
        <span class="lbl">Microphone</span>
        <select
          class="keyinput"
          :value="selectedDevice"
          aria-label="Microphone"
          @focus="emit('refreshDevices')"
          @change="emit('pickDevice', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">System default</option>
          <option v-for="d in devices" :key="d.name" :value="d.value ?? d.name">
            {{ d.name }}{{ d.default ? " ◆" : "" }}
          </option>
        </select>
      </div>
      <div class="text">
        <p>
          Which input the daemon listens to — switching swaps the audio stream
          live, no restart. ◆ marks the system default. A device plugged in
          after the daemon started appears when you refresh the list. Speech plays
          through the system’s selected speakers.
        </p>
      </div>
    </section>



    </slot></div>
    <section class="sec">
      <div class="keyrow">
        <span class="lbl">Hotkeys</span>
        <span class="pointer">Hold, toggle, scratch and per-tab keys live in the <button class="linkbtn" @click="tab = 'HOTKEYS'">Hotkeys</button> tab.</span>
      </div>
    </section>
    </template>

    <SpeechSettings v-if="tab === 'SPEECH'" @configure="tab = 'SYSTEM'" />
    <template v-if="tab === 'SYSTEM'">

    <section class="sec">
      <div class="keyrow">
        <span class="lbl">xAI API key</span>
        <!-- Always an input-shaped field, so it reads as a form at a
             glance — readonly masked value until REPLACE is clicked. -->
        <template v-if="!editing">
          <input class="keyinput stored" aria-label="Stored xAI API key" :value="`••••••••••••${apiKeyHint.replace(/·/g, '')}`" readonly @click="editing = true" />
          <button class="btn" @click="editing = true">Replace</button>
        </template>
        <template v-else>
          <input
            v-model="keyInput"
            aria-label="New xAI API key"
            type="password"
            class="keyinput"
            placeholder="xai-…"
            @keyup.enter="submit"
          />
          <button class="btn" @click="submit">Save</button>
          <button class="btn dim" @click="editing = false">Cancel</button>
        </template>
      </div>

      <div class="text">
        <p>
          The key powers everything this console does: transcribing your speech
          (Grok STT) and giving your agent a voice (Grok TTS). Get one at
          <a href="https://console.x.ai" target="_blank" rel="noreferrer">console.x.ai</a>
          → <b>API Keys</b> → <b>Create API key</b>, then paste it above.
        </p>
        <details class="costs">
          <summary>WONDERING WHAT THIS COSTS? PENNIES — SEE THE MATH ▾</summary>
          <p>
            Speech-to-text costs <b>$0.10 per hour of audio</b> ($0.20 in
            live-streaming mode) and text-to-speech <b>$4.20 per million
            characters</b>. In practice:
          </p>
          <ul>
            <li>a 15-second spoken command ≈ <b>$0.0004</b></li>
            <li>a typical spoken agent reply (~200 characters) ≈ <b>$0.0008</b></li>
            <li>a full hour of live conversation ≈ <b>$0.20–0.30</b> both ways</li>
            <li>an hour a day, every workday ≈ <b>$5–7 / month</b></li>
          </ul>
          <p>
            Pricing and docs:
            <a href="https://x.ai/api" target="_blank" rel="noreferrer">x.ai/api</a> ·
            <a href="https://docs.x.ai" target="_blank" rel="noreferrer">docs.x.ai</a> ·
            credits &amp; billing at
            <a href="https://console.x.ai" target="_blank" rel="noreferrer">console.x.ai</a>.
          </p>
        </details>
      </div>
    </section>

    <section class="sec">
      <div class="keyrow">
        <span class="lbl">Diagnostics</span>
        <button class="btn" :disabled="checksRunning" @click="emit('runChecks')">
          {{ checksRunning ? "Running…" : "Run checks" }}
        </button>
      </div>
      <DiagnosticChecklist v-if="checks" class="checks-indent" :checks="checks" />
      <div class="text">
        <p>
          Live-checks every xAI call this console makes — each verdict
          stands alone, so one failing endpoint never reads as "your key is
          wrong". The same checks run automatically when you save a key.
        </p>
      </div>
    </section>

    </template>

    <template v-if="tab === 'SOUNDS'">
    <section v-if="cuePrefs" class="sec">
      <div class="keyrow">
        <span class="lbl">Recording hum</span>
        <button
          class="btn" :class="{ dim: !(cuePrefs.recordingHum ?? true) }"
          @click="emit('setHum', { recordingHum: !(cuePrefs.recordingHum ?? true) })"
        >{{ (cuePrefs.recordingHum ?? true) ? "ON" : "OFF" }}</button>
      </div>
      <div class="keyrow">
        <span class="lbl">Noise</span>
        <select
          class="keyinput"
          :value="cuePrefs.humNoise ?? 'pink'"
          aria-label="Recording noise"
          @change="emit('setHum', { humNoise: ($event.target as HTMLSelectElement).value });
                   previewHum(($event.target as HTMLSelectElement).value, cuePrefs.humVolume ?? 0.25)"
        >
          <option v-for="n in HUM_NOISES" :key="n" :value="n">{{ n.toUpperCase() }}</option>
        </select>
      </div>
      <div class="keyrow">
        <span class="lbl">Volume</span>
        <input
          class="slider" type="range" min="0" max="1" step="0.05"
          aria-label="Recording hum volume"
          :value="cuePrefs.humVolume ?? 0.25"
          @input="emit('setHum', { humVolume: Number(($event.target as HTMLInputElement).value) })"
          @change="previewHum(cuePrefs.humNoise ?? 'pink', Number(($event.target as HTMLInputElement).value))"
        />
      </div>
      <div class="text">
        <p>
          The barely-there noise that plays while the system can hear you.
          Changing the color or volume gives a 1.5 s preview.
        </p>
      </div>
    </section>

    <section v-if="cuePrefs" class="sec">
      <div class="keyrow">
        <span class="lbl">Audio cues</span>
        <span class="cue-hint">{{ cuePrefs.enabled ? "ENABLED" : "DISABLED — TURN ON IN CONTROLS" }}</span>
      </div>
      <div class="cuegrid">
        <div v-for="name in cueNames" :key="name" class="cuerow">
          <button class="btn preview" title="Preview" @click="playCue(name)">▶</button>
          <span class="cue-label">{{ CUE_LABELS[name] }}</span>
          <button
            class="btn"
            :class="{ dim: !cuePrefs.cues[name] }"
            @click="emit('toggleCue', name, !cuePrefs.cues[name])"
          >{{ cuePrefs.cues[name] ? "ON" : "OFF" }}</button>
        </div>
      </div>
      <div class="text">
        <p>
          Whisper-quiet blips for conversation events, so you know what's
          happening without watching the screen. Stored per browser.
        </p>
      </div>
    </section>
    </template>
  </div>
</template>

<style scoped>
.settings { display: grid; grid-template-columns: minmax(0, 1fr); gap: 22px; min-width: 0; container-type: inline-size; }
.sec { min-width: 0; }
.toolbar { display: flex; gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
.tabbtn {
  font-family: var(--sans); font-size: 11px; letter-spacing: normal;
  color: var(--muted); background: none; border: 1px solid transparent;
  padding: 4px 12px; cursor: pointer;
}
.tabbtn.on { color: var(--cyan); border-color: rgba(158, 188, 245, 0.4); }
.tabbtn:hover { color: var(--cyan-hi); }
.slider { flex: 1; min-width: 0; accent-color: var(--cyan); }

.keyrow { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.keyrow .lbl { font-size: 11px; letter-spacing: normal; color: var(--muted); width: 92px; flex: none; }
.keyinput {
  flex: 1;
  min-width: 0;
  border-radius: 6px;
  font-family: var(--sans);
  font-size: 12px;
  color: var(--ink);
  background: var(--bg1);
  border: 1px solid var(--line-strong);
  padding: 8px 12px;
}
.keyinput.stored { color: var(--green); letter-spacing: normal; cursor: pointer; }
.btn {
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: normal;
  color: var(--cyan);
  background: rgba(158, 188, 245, 0.06);
  border: 1px solid var(--line-strong);
  padding: 7px 14px;
  cursor: pointer;
  border-radius: 8px;
}
.btn:hover { color: var(--cyan-hi); text-shadow: none; }
.btn.dim { color: var(--muted); border-color: var(--line); }

.checks-indent { margin: 4px 0 14px 102px; }

.cue-hint { flex: 1; font-size: 11px; letter-spacing: normal; color: var(--muted); }
.cuegrid { display: grid; gap: 8px; margin: 4px 0 14px 102px; max-width: 420px; }
.cuerow { display: flex; align-items: center; gap: 10px; }
.cuerow .preview { padding: 4px 9px; }
.cue-label { flex: 1; font-size: 11px; letter-spacing: normal; color: var(--ink); }
.pointer { font-size: 12px; color: var(--muted); }
.linkbtn { background: none; border: 0; padding: 0; font: inherit; color: var(--cyan); cursor: pointer; border-bottom: 1px dotted var(--cyan-dim); }
.linkbtn:hover { color: var(--cyan-hi); }
.text {
  font-size: 13px;
  line-height: 1.75;
  color: var(--muted);
  display: grid;
  gap: 10px;
  max-width: 640px;
  margin-left: 102px;
}
.costs summary {
  cursor: pointer;
  list-style: none;
  font-size: 11px;
  letter-spacing: normal;
  color: var(--cyan-dim);
}
.costs summary::-webkit-details-marker { display: none; }
.costs summary:hover { color: var(--cyan); }
.costs[open] summary { color: var(--cyan); margin-bottom: 8px; }
.costs p, .costs ul { margin-top: 6px; }
.text b { color: var(--ink); font-weight: 400; }
.text a { color: var(--amber-dim); text-decoration: none; border-bottom: 1px dotted var(--amber-dim); }
.text a:hover { color: var(--amber); text-shadow: none; }
.text ul { margin: 0 0 0 18px; display: grid; gap: 4px; }
.text li b { color: var(--ink); }
@container (max-width: 560px) {
  .keyrow { flex-wrap: wrap; gap: 8px; }
  .keyrow .lbl { width: 100%; font-size: 12px; }
  .keyinput { flex-basis: 60%; }
  .text, .cuegrid, .checks-indent { margin-left: 0; }
  .cue-hint { flex-basis: 100%; }
}
</style>
