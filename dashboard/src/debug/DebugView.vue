<script setup lang="ts">
/** Chat-window sandbox at /debug.

Drives the REAL ConversationLog with hand-clicked state transitions, no
daemon involved. The chat machine (machines/chat.ts) decides which events
are clickable: a button lights up only when the event is legal in the
target card's current state, and anything injected illegally anyway lands
in the log as ⚠ UNEXPECTED — that's the assumption-bug detector. Every
click lands in an event log (ms timestamps) that can be copied and pasted
into a bug report: "with this sequence, X". */

import { computed, ref } from "vue";
import ConversationLog from "../components/ConversationLog.vue";
import HudPanel from "../components/HudPanel.vue";
import {
  CLAUDE_WORKER_STATES,
  canDeliverDuring,
  nextState,
  statusAllows,
  stateToStatus,
  statusToState,
  type Role,
} from "../machines/chat";
import type { Utterance } from "../types";

const utterances = ref<Utterance[]>([]);
const activity = ref<{ text: string; at: number } | null>(null);
const playingId = ref(0);
const log = ref<string[]>([]);
let nextId = 1;

const SAMPLE_USER = "No dobra, to teraz przejdźmy do refaktoru modułu billing i zróbmy to porządnie.";
const SAMPLE_CLAUDE = "Zrobione — testy zielone, wszystko zacommitowane na main.";

function note(action: string, detail = "") {
  const d = new Date();
  const ts = [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":") + "." + String(d.getMilliseconds()).padStart(3, "0");
  log.value.push(`${ts} ${action}${detail ? ` ${detail}` : ""}`);
}

function now() {
  return Date.now() / 1000;
}

// --- event targeting --------------------------------------------------------
// The daemon's single playback worker takes the OLDEST queued claude card
// and plays it before touching the next — so lifecycle events land on the
// worker's current card, or the FIFO head when the worker is free. Never
// on the newest arrival. (The real daemon also prefetches synthesis of
// queued cards; the sandbox keeps the simpler one-card-at-a-time model.)
function claudeTarget(): Utterance | undefined {
  const cards = utterances.value.filter((u) => u.role === "claude");
  const working = cards.find((u) =>
    CLAUDE_WORKER_STATES.has(statusToState("claude", u.status) ?? ""),
  );
  return working ?? cards.find((u) => statusToState("claude", u.status) === "queued");
}

// User events hit the newest card that accepts them (the mic guard keeps
// at most one composition alive, so this is unambiguous in practice).
function userTarget(event: string): Utterance | undefined {
  return [...utterances.value]
    .reverse()
    .find((u) => u.role === "user" && statusAllows("user", u.status, event));
}

function readyCards(): Utterance[] {
  return utterances.value.filter(
    (u) => u.role === "user" && statusToState("user", u.status) === "ready",
  );
}

// --- event injection --------------------------------------------------------
// One path for every lifecycle event: ask the machine for the next state,
// write its canonical status onto the card, log the hop. An illegal event
// (impossible via the disabled buttons, but not via future replays of a
// pasted log) is the interesting case: it gets a ⚠ line instead of a patch.

// Sandbox dressing per event — the fields the daemon would fill alongside
// the status change.
const EVENT_FIELDS: Record<string, (u: Utterance) => Partial<Utterance>> = {
  "user.TRANSCRIBE": (u) => ({
    text: (u.text ? u.text + " " : "") + SAMPLE_USER.split(" ").slice(0, 5).join(" "),
  }),
  "user.READY": () => ({ text: SAMPLE_USER, committed_at: now(), duration_s: 6.4 }),
  "claude.PLAYED": () => ({ duration_s: 8.2 }),
};

// Cross-machine invariants live outside the per-card machines: they gate
// an event on the state of ANOTHER machine. Returns why the event is
// impossible right now, or null when it may fire.
function crossGuard(role: Role, event: string): string | null {
  if (role === "user" && event === "DELIVER" && !canDeliverDuring(activity.value?.text ?? null)) {
    return `a tool is executing ("${activity.value?.text}") — hooks drain only between tools or at turn end`;
  }
  return null;
}

// Apply one event to one specific card — the shared core for injector
// buttons and the bubbles' own ↻/✕ affordances.
function fire(u: Utterance, role: Role, event: string) {
  const from = statusToState(role, u.status);
  const to = from === null ? null : nextState(role, from, event);
  if (to === null) {
    note(`⚠ UNEXPECTED ${role}.${event} in state "${from ?? u.status}" (id ${u.id})`);
    return;
  }
  const blocked = crossGuard(role, event);
  if (blocked) {
    note(`⚠ UNEXPECTED ${role}.${event} — ${blocked}`);
    return;
  }
  const fields = EVENT_FIELDS[`${role}.${event}`]?.(u) ?? {};
  Object.assign(u, fields, { status: stateToStatus(role, to), updated_at: now() });
  if (role === "claude" && event === "PLAY") playingId.value = u.id;
  if (role === "claude" && event !== "PLAY" && playingId.value === u.id) playingId.value = 0;
  note(`${role}.${event}`, `(id ${u.id}: ${from} → ${to})`);
}

function inject(role: Role, event: string) {
  // A hook drain delivers EVERY ready transcript in one gulp, not one card.
  if (role === "user" && event === "DELIVER") {
    const cards = readyCards();
    if (!cards.length) {
      note("⚠ user.DELIVER — nothing awaiting pickup");
      return;
    }
    cards.forEach((u) => fire(u, "user", "DELIVER"));
    return;
  }
  const u = role === "user" ? userTarget(event) : claudeTarget();
  if (!u) {
    note(`⚠ ${role}.${event} — no ${role} card can receive it`);
    return;
  }
  fire(u, role, event);
}

function allows(role: Role, event: string): boolean {
  if (crossGuard(role, event) !== null) return false;
  if (role === "user" && event === "DELIVER") return readyCards().length > 0;
  const u = role === "user" ? userTarget(event) : claudeTarget();
  return !!u && statusAllows(role, u.status, event);
}

// The bubbles' own controls work in the sandbox too: ↻ re-queues that very
// card (visible only once the worker picks it up — like the daemon), ⏹
// stops the playback, ✕ recalls an awaiting transcript.
function onReplay(u: Utterance) {
  note("ui.replay_clicked", `(id ${u.id})`);
  if (playingId.value === u.id) {
    fire(u, "claude", "SKIP"); // ⏹ — an explicit dismissal stays dismissed
    return;
  }
  const busy = claudeTarget();
  if (busy && CLAUDE_WORKER_STATES.has(statusToState("claude", busy.status) ?? "")) {
    note("ui.replay_deferred", `(worker busy with id ${busy.id} — no visible change until it frees)`);
    return;
  }
  fire(u, "claude", "REPLAY");
}

function onCancel(u: Utterance) {
  note("ui.cancel_clicked", `(id ${u.id})`);
  fire(u, "user", "CANCEL");
}

interface EventButton {
  event: string;
  label: string;
  dim?: boolean;
}

const USER_BUTTONS: EventButton[] = [
  { event: "TRANSCRIBE", label: "+ PARTIAL TRANSCRIPT" },
  { event: "READY", label: "READY (AWAITING)" },
  { event: "DELIVER", label: "DELIVERED" },
  { event: "EMPTY", label: "EMPTY (NOISE)", dim: true },
  { event: "DROP", label: "DROPPED", dim: true },
  { event: "STT_ERROR", label: "STT ERROR", dim: true },
  { event: "CANCEL", label: "CANCELLED", dim: true },
];

const CLAUDE_BUTTONS: EventButton[] = [
  { event: "HOLD", label: "HOLDING" },
  { event: "SYNTHESIZE", label: "SYNTHESIZING" },
  { event: "PLAY", label: "PLAYING" },
  { event: "PLAYED", label: "PLAYED" },
  { event: "UNHEARD", label: "UNHEARD", dim: true },
  { event: "TTS_ERROR", label: "TTS ERROR", dim: true },
];

// --- card spawns ------------------------------------------------------------
// The one mic can't record two segments at once — a new recording is legal
// only while no user card is still composing. Claude messages just queue.
const canStartRecording = computed(
  () =>
    !utterances.value.some((u) => {
      if (u.role !== "user") return false;
      const state = statusToState("user", u.status);
      return state === "recording" || state === "transcribing";
    }),
);

function userStartRecording() {
  const u: Utterance = {
    id: nextId++, role: "user", status: stateToStatus("user", "recording"), text: "",
    detail: "VAD OPEN", cost_usd: 0, agent: null,
    started_at: now(), updated_at: now(), committed_at: 0,
  };
  utterances.value.push(u);
  note("user.START_RECORDING", `(id ${u.id})`);
}

function claudeNew() {
  const u: Utterance = {
    id: nextId++, role: "claude", status: stateToStatus("claude", "queued"), text: SAMPLE_CLAUDE,
    detail: "", cost_usd: 0.0008, agent: null,
    started_at: now(), updated_at: now(), committed_at: now(),
  };
  utterances.value.push(u);
  note("claude.ARRIVES", `(id ${u.id}: queued)`);
}

// --- activity (start/stop pairs) -------------------------------------------
// Deliberately NOT a machine: the activity line is last-writer-wins from
// hooks that may fire in any order (parallel tool batches, parallel
// agents, a restart mid-turn) — every sequence is legal, so every button
// stays clickable.
function startTool() {
  activity.value = { text: "Edit · App.vue", at: now() };
  note("activity.start_tool", "(Edit · App.vue)");
}
function startThinking() {
  activity.value = { text: "THINKING…", at: now() };
  note("activity.start_thinking");
}
function stopActivity() {
  activity.value = null;
  note("activity.stop (turn ended)");
}

// --- system ---------------------------------------------------------------
function sysMicRow() {
  utterances.value.push({
    id: nextId++, role: "system", status: "", text: "MIC → Sandbox Device",
    detail: "", cost_usd: 0, agent: null,
    started_at: now(), updated_at: now(), committed_at: now(),
  });
  note("system.mic_row");
}

function resetAll() {
  utterances.value = [];
  activity.value = null;
  playingId.value = 0;
  nextId = 1;
  note("reset");
}

async function copyLog() {
  try {
    await navigator.clipboard.writeText(log.value.join("\n"));
    note("log.copied_to_clipboard");
  } catch {
    note("log.copy_FAILED");
  }
}
</script>

<template>
  <div class="scanlines" />
  <div class="vignette" />
  <div class="hud">
    <header class="dbg-header">
      <div class="title">NOISY STUDIO // CHAT SANDBOX</div>
      <span class="sub">/debug — clicks drive the real ConversationLog; buttons follow the chat machine; nothing touches the daemon</span>
    </header>

    <div class="dbg-cols">
      <HudPanel index="D1" title="EVENT INJECTOR" class="dbg-panel">
        <div class="group">
          <div class="glabel">USER MESSAGE</div>
          <button class="ctl" :disabled="!canStartRecording" @click="userStartRecording">
            START RECORDING
          </button>
          <button
            v-for="b in USER_BUTTONS"
            :key="b.event"
            class="ctl"
            :class="{ dim: b.dim }"
            :disabled="!allows('user', b.event)"
            @click="inject('user', b.event)"
          >{{ b.label }}</button>
        </div>
        <div class="group">
          <div class="glabel">AGENT MESSAGE</div>
          <button class="ctl" @click="claudeNew">ARRIVES (QUEUED)</button>
          <button
            v-for="b in CLAUDE_BUTTONS"
            :key="b.event"
            class="ctl"
            :class="{ dim: b.dim }"
            :disabled="!allows('claude', b.event)"
            @click="inject('claude', b.event)"
          >{{ b.label }}</button>
        </div>
        <div class="group">
          <div class="glabel">ACTIVITY (START/STOP)</div>
          <button class="ctl" @click="startTool">START TOOL</button>
          <button class="ctl" @click="startThinking">START THINKING</button>
          <button class="ctl warn" @click="stopActivity">STOP ACTIVITY</button>
        </div>
        <div class="group">
          <div class="glabel">SYSTEM</div>
          <button class="ctl" @click="sysMicRow">MIC SWITCH ROW</button>
          <button class="ctl danger" @click="resetAll">RESET ALL</button>
        </div>
      </HudPanel>

      <HudPanel index="D2" title="COMM LOG · UNDER TEST" class="dbg-mid">
        <ConversationLog
          :utterances="utterances"
          :playing-id="playingId"
          :activity="activity"
          @replay="onReplay"
          @cancel="onCancel"
        />
      </HudPanel>

      <HudPanel index="D3" title="EVENT LOG" class="dbg-panel">
        <button class="ctl" @click="copyLog">COPY LOG</button>
        <div class="loglines">
          <div v-for="(line, i) in [...log].reverse()" :key="log.length - i" class="logline">{{ line }}</div>
        </div>
      </HudPanel>
    </div>
  </div>
</template>

<style scoped>
.dbg-header { padding: 10px 18px 14px; border-bottom: 1px solid var(--line); flex: none; }
.dbg-header .title { font-size: 16px; letter-spacing: normal; color: var(--cyan-hi); text-shadow: none; }
.dbg-header .sub { font-size: 11px; letter-spacing: normal; color: var(--muted); }
.dbg-cols {
  display: grid;
  grid-template-columns: 240px minmax(380px, 1fr) 320px;
  gap: 18px;
  margin-top: 14px;
  flex: 1 1 auto;
  min-height: 0;
}
.dbg-panel { overflow-y: auto; }
.dbg-mid { display: flex; flex-direction: column; min-height: 0; }
.dbg-cols :deep(.panel) { margin-bottom: 0; }
.dbg-mid :deep(.panel) { flex: 1; min-height: 0; display: flex; flex-direction: column; }

.group { display: grid; gap: 6px; margin-bottom: 16px; }
.glabel { font-size: 11px; letter-spacing: normal; color: var(--muted); margin-bottom: 2px; }
.ctl {
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: normal;
  color: var(--cyan);
  background: rgba(63, 216, 255, 0.06);
  border: 1px solid var(--line-strong);
  padding: 6px 10px;
  cursor: pointer;
  text-align: left;
  border-radius: 8px;
}
.ctl:hover:not(:disabled) { color: var(--cyan-hi); text-shadow: none; }
.ctl.dim { color: var(--muted); border-color: var(--line); }
.ctl.warn { color: var(--amber); border-color: var(--amber-dim); }
.ctl.danger { color: var(--red); border-color: rgba(255, 95, 107, 0.5); }
.ctl:disabled {
  /* Illegal in the current machine state — visibly off, not just inert. */
  opacity: 0.28;
  cursor: not-allowed;
  text-shadow: none;
}

.loglines { margin-top: 10px; display: grid; gap: 3px; overflow-y: auto; }
.logline { font-size: 11px; color: var(--muted); letter-spacing: normal; white-space: nowrap; }
.logline:first-child { color: var(--cyan); }
</style>
