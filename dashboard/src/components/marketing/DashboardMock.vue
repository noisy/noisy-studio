<script setup lang="ts">
import "../../styles/dashboard.css";
/* The dashboard, content only - no OS chrome.
 *
 * Marketing prop for the website hero: the landing page wraps screenshots
 * in its own CSS window frame, so this shot must NOT carry a macOS title
 * bar of its own. Real components, invented but believable session data,
 * a light re-creation of App.vue's layout (App itself needs a live daemon).
 */
import { onMounted, onUnmounted, ref } from "vue";
import type { Character, DaemonStatus, Utterance } from "../../types";
import AgentTabs from "../AgentTabs.vue";
import CharacterReadout from "../CharacterReadout.vue";
import ConversationLog from "../ConversationLog.vue";
import ConversationTelemetry from "../ConversationTelemetry.vue";
import HudPanel from "../HudPanel.vue";
import Oscilloscope from "../Oscilloscope.vue";
import TurnHistory from "../TurnHistory.vue";
import SpectrumBars from "../SpectrumBars.vue";
import StatusStrip from "../StatusStrip.vue";
import VoicePersona from "../VoicePersona.vue";

const now = Date.now() / 1000;

const UTTERANCES: Utterance[] = [
  { id: 1, role: "user", status: "delivered to Claude", text: "How far are we with the payment retries branch?", detail: "STT 0.4 s - 3.8 s AUDIO", cost_usd: 0.0003, agent: null, started_at: now - 340, updated_at: now - 336, committed_at: now - 340 },
  { id: 2, role: "claude", status: "played", voice: "lux", text: "The backoff logic is in and covered. I am reworking the dead-letter path now - the old one dropped events on redeploy.", detail: "TTS 1.2 s - 9.1 s AUDIO", cost_usd: 0.0031, agent: null, started_at: now - 320, updated_at: now - 308, committed_at: now - 320 },
  { id: 3, role: "user", status: "delivered to Claude", text: "Good catch. Keep the events in the queue and add a metric for it.", detail: "STT 0.4 s - 5.0 s AUDIO", cost_usd: 0.0004, agent: null, started_at: now - 180, updated_at: now - 175, committed_at: now - 180 },
  { id: 4, role: "claude", status: "played", voice: "lux", text: "Done - events survive redeploys and the new retry_backlog gauge is on the board. Two tests pin the behavior.", detail: "TTS 1.1 s - 8.3 s AUDIO", cost_usd: 0.0027, agent: null, started_at: now - 90, updated_at: now - 80, committed_at: now - 90 },
  { id: 5, role: "user", status: "recording...", text: "Nice. Next, let's look at the slow dashboard query and", detail: "VAD OPEN - 2.8 s", cost_usd: 0, agent: null, started_at: now - 3, updated_at: now, committed_at: now - 3 },
];

const STATUS = {
  listening: true, muted: false, voice_muted: false,
  api_key_set: true, api_key_hint: "xai-...k3f9",
  stt_latency_ms: 410, tts_latency_ms: 1240,
  recording: true, claude_speaking: false, playing_utterance_id: 0,
  speaking_agents: [], queued: 0,
  session_cost_usd: { user: 0.0214, claude: 0.1187 },
  usage: { stt_seconds: 764, tts_chars: 18432 },
  credits_usd: 4.21,
  mode: "batch", tts_mode: "batch", end_silence_ms: 1500,
  mic_sensitivity: 50, smart_turn: 0.7, smart_turn_mode: "soft",
  detection_mode: "auto", ptt_held: false,
  input_device: "", activity: {}, language: "en",
  agents: { "payment-retries": 5, "code-review": 2, "docs": 1 },
  agent_labels: { "payment-retries": "payment-retries", "code-review": "code-review", "docs": "docs" },
  active_agent: "payment-retries",
} as DaemonStatus;

const CHARACTER: Character = { humor: 40, honesty: 90, verbosity: 30, talkative: 30, voice: "lux", speed: 1.1 };

// The scopes draw from a live level; feed them a plausible voice envelope
// so the canvases are not flat in a static capture.
const level = ref(0.3);
let timer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  timer = setInterval(() => {
    level.value = Math.max(0.05, Math.min(0.85, level.value + (Math.random() - 0.48) * 0.25));
  }, 50);
});
onUnmounted(() => clearInterval(timer));

const noop = () => {};
</script>

<template>
  <div class="hud mock">
        <header class="topbar">
          <div class="logo">
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
          <button class="ctl header-action">Mute all agents</button>
        </header>
    <div class="cols">
      <div class="col-left">
        <button class="bigmute">
          <span class="bm-label">Mute microphone</span>
          <span class="bm-sub">Listening · click to pause</span>
        </button>
        <HudPanel index="01" title="Microphone">
          <Oscilloscope :level="level" />
        </HudPanel>
        <HudPanel index="02" title="Audio spectrum" class="spectrum-panel">
          <SpectrumBars :level="level" />
        </HudPanel>
        <HudPanel index="05" title="Session usage">
          <StatusStrip :status="STATUS" :offline="false" />
        </HudPanel>
      </div>

      <div class="col-mid">


        <div class="tabsbar">
          <AgentTabs
            :agents="STATUS.agent_labels"
            :active="'payment-retries'"
            :viewed="'payment-retries'"
            :speaking="[]"
            :thinking="['payment-retries']"
            :queued="{ 'code-review': 1 }"
            @select="noop"
            @dismiss="noop"
            @reorder="noop"
          />
        </div>
        <HudPanel class="convo-panel">
          <div class="conversation-heading">
            <div><h1>Payment retries</h1><p>Your conversation, as it happens</p></div>
            <span class="recipient">Receiving: Payment retries</span>
          </div>
          <div class="convo-body">
            <div class="convo-main">
              <ConversationLog :utterances="UTTERANCES" :playing-id="0" />
              <ConversationTelemetry
                :stt-latency-ms="410"
                :tts-latency-ms="1240"
                :user-cost-usd="0.0214"
                :claude-cost-usd="0.1187"
                :stt-seconds="764"
                :tts-chars="18432"
              />
            </div>
            <aside class="convo-rail">
              <section class="railbox">
                <VoicePersona voice="lux" :speaking="false" :muted="false" />
              </section>
              <section class="railbox">
                <div class="railtitle">Character</div>
                <CharacterReadout :character="CHARACTER" />
              </section>
              <section class="railbox">
                <div class="railtitle">Turn history</div>
                <TurnHistory :utterances="UTTERANCES" />
              </section>
            </aside>
          </div>
        </HudPanel>
      </div>
    </div>

    <footer>
      <span>DAEMON <b class="ok">ONLINE</b></span>
      <span>STT MODE <b>BATCH</b></span>
      <span>LANGUAGE <b>EN</b></span>
      <span>QUEUE <b>0</b></span>
      <span style="margin-left: auto">v3.0.0</span>
      <span>&#9672; ALL SYSTEMS NOMINAL</span>
    </footer>
  </div>
</template>

<style scoped>
.mock { width:100%; height:100dvh; }
</style>
