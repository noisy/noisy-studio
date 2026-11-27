<script setup lang="ts">
// Lab mock: three ways to bring the machine-global mic control into the
// header next to "Mute all agents". The mic gets ONE slot whose job follows
// the turn mode: Auto -> Mute mic, Push to talk -> Hold to talk (muting is
// pointless there: nothing is captured unless you hold). A mute left over
// from Auto shows in the same slot as "click to unmute", so it is never a
// dead end. Static markup on the real tokens - nothing talks to the daemon.
import { computed } from "vue";
import Oscilloscope from "../../components/Oscilloscope.vue";

export type HeaderVariant = "A" | "B" | "C";
export interface HeaderState {
  mode: "auto" | "ptt";
  micMuted: boolean;
  pttHeld: boolean;
  agentsMuted: boolean;
}

const props = defineProps<{ variant: HeaderVariant; state: HeaderState; level: number }>();

// Geometry knobs. The mic slot keeps one width in every mode and state, so
// switching Auto <-> Push to talk or muting never moves its neighbours.
const PLATE_HEIGHT_PX = 48;
const MIC_PLATE_PX = 252;
const AGENTS_PLATE_PX = 184;
const MIC_SEG_PX = 140;
const CONSOLE_SCOPE_PX = 180;

type SlotKind = "mute" | "muted" | "talk" | "held";
const slot = computed<SlotKind>(() => {
  if (props.state.micMuted) return "muted";
  if (props.state.mode === "auto") return "mute";
  return props.state.pttHeld ? "held" : "talk";
});
const SLOT_TEXT: Record<SlotKind, { label: string; sub: string }> = {
  mute: { label: "Mute mic", sub: "Listening · click to pause" },
  muted: { label: "Mic muted", sub: "Click to unmute" },
  talk: { label: "Hold to talk", sub: "or hold Space" },
  held: { label: "◉ On air", sub: "Release to send" },
};
const micText = computed(() => SLOT_TEXT[slot.value]);
const agentsLabel = computed(() => (props.state.agentsMuted ? "Agents muted" : "Mute all agents"));
const agentsSub = computed(() => (props.state.agentsMuted ? "Replies kept for later" : "Replies play aloud"));
const scopeLevel = computed(() => (props.state.micMuted ? 0 : props.level));
</script>

<template>
  <header
    class="strip"
    :class="`v${variant}`"
    :style="{
      '--plate-h': PLATE_HEIGHT_PX + 'px',
      '--mic-w': MIC_PLATE_PX + 'px',
      '--agents-w': AGENTS_PLATE_PX + 'px',
      '--seg-w': MIC_SEG_PX + 'px',
      '--console-scope': CONSOLE_SCOPE_PX + 'px',
    }"
  >
    <div class="logo">
      <svg width="40" height="40" viewBox="0 0 46 46" aria-hidden="true">
        <rect x="4" y="4" width="38" height="38" rx="11" fill="var(--surface-hover)" />
        <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="17" y1="20" x2="17" y2="26" /><line x1="21" y1="16" x2="21" y2="30" />
          <line x1="25" y1="19" x2="25" y2="27" /><line x1="29" y1="21" x2="29" y2="25" />
        </g>
      </svg>
      <div><div class="title">Noisy Studio</div><div class="sub">Your voice, in the workflow</div></div>
    </div>

    <!-- A: paired plates on the right - the mic slot and the agents plate
         share one shape; the icon and the word tell them apart. -->
    <div v-if="variant === 'A'" class="right">
      <button class="plate mic" :class="slot">
        <svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="1.5" width="5" height="9" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3 8a5 5 0 0 0 10 0M8 13v2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        <span class="txt"><span class="lbl">{{ micText.label }}</span><span class="sub2">{{ micText.sub }}</span></span>
        <span class="scope"><Oscilloscope :level="scopeLevel" /></span>
      </button>
      <span class="divider" />
      <button class="plate agents" :class="{ muted: state.agentsMuted }">
        <svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6h3l4-3v10l-4-3H2z" fill="currentColor"/><path v-if="!state.agentsMuted" d="M11.5 5.5a3.5 3.5 0 0 1 0 5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path v-else d="M11 6l3.5 4M14.5 6L11 10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        <span class="txt"><span class="lbl">{{ agentsLabel }}</span><span class="sub2">{{ agentsSub }}</span></span>
      </button>
      <button class="action">Settings</button>
    </div>

    <!-- B: the mic is the instrument - scope and the mic slot as one
         console in the middle; output and settings stay on the right. -->
    <template v-else-if="variant === 'B'">
      <div class="console" :class="{ muted: state.micMuted }">
        <span class="scope wide"><Oscilloscope :level="scopeLevel" /></span>
        <button class="seg mic" :class="slot"><span class="lbl">{{ micText.label }}</span></button>
      </div>
      <div class="right">
        <button class="action agents" :class="{ muted: state.agentsMuted }">{{ state.agentsMuted ? "Unmute all agents" : "Mute all agents" }}</button>
        <button class="action">Settings</button>
      </div>
    </template>

    <!-- C: two labelled groups, input and output - the frame already says
         which way the sound goes. -->
    <div v-else class="right">
      <fieldset class="group">
        <legend>You · input</legend>
        <span class="meter"><Oscilloscope :level="scopeLevel" /></span>
        <button class="seg mic" :class="slot"><span class="lbl">{{ micText.label }}</span></button>
      </fieldset>
      <fieldset class="group">
        <legend>Agents · output</legend>
        <button class="seg agents" :class="{ muted: state.agentsMuted }"><span class="lbl">{{ agentsLabel }}</span></button>
      </fieldset>
      <button class="action">Settings</button>
    </div>
  </header>
</template>

<style scoped>
.strip { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:10px 20px; background:var(--bg0); color:var(--ink); font:14px/1.4 var(--sans); }
.strip.vB { display:grid; grid-template-columns:1fr auto 1fr; }
.strip.vB .right { justify-self:end; }
.logo { display:flex; align-items:center; gap:10px; min-width:0; }
.title { font-size:17px; font-weight:600; letter-spacing:-.3px; }
.sub { font-size:11px; color:var(--muted); }
.right { display:flex; align-items:center; gap:8px; }
button { font:inherit; color:var(--ink); background:var(--surface-hover); border:1px solid var(--line-strong); border-radius:7px; cursor:pointer; }
.action { height:40px; padding:0 14px; font-size:13px; font-weight:500; background:var(--bg1); border-color:var(--line); white-space:nowrap; }
.lbl { font-size:13px; font-weight:600; white-space:nowrap; }
.sub2 { font-size:11px; color:var(--muted); white-space:nowrap; }
.txt { display:flex; flex-direction:column; align-items:flex-start; gap:1px; }
.ico { width:16px; height:16px; flex:none; }
/* Red = muting, amber = on air: the existing colour meanings. */
.muted { color:var(--red); border-color:var(--red); }
.muted .lbl { animation:mute-blink 1.6s step-end infinite; }
.held { color:var(--amber); border-color:var(--amber); }
.talk { touch-action:none; user-select:none; }
@keyframes mute-blink { 50% { opacity:.55; } }

/* A */
.plate { display:flex; align-items:center; gap:10px; height:var(--plate-h); padding:0 12px; }
.plate.mic { width:var(--mic-w); }
.plate.agents { width:var(--agents-w); }
.plate .scope { width:64px; height:28px; margin-left:auto; opacity:.9; }
.plate.muted .scope { opacity:.3; }
.divider { width:1px; height:30px; background:var(--line); margin:0 4px; }
.scope :deep(canvas), .meter :deep(canvas) { height:100% !important; min-height:0 !important; }

/* B */
.console { display:flex; align-items:center; gap:6px; padding:4px; border:1px solid var(--line); border-radius:10px; background:var(--bg1); }
.console.muted { border-color:color-mix(in srgb, var(--red) 45%, var(--line)); }
.scope.wide { width:var(--console-scope); height:36px; padding:0 6px; }
.console.muted .scope.wide { opacity:.3; }
.seg { height:40px; padding:0 14px; }
.seg.mic { width:var(--seg-w); }

/* C */
.group { display:flex; align-items:center; gap:6px; border:1px solid var(--line); border-radius:10px; padding:2px 6px 6px; margin:0; }
.group legend { font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:0 4px; }
.meter { width:84px; height:30px; }
.group .seg.agents { min-width:140px; }
</style>
