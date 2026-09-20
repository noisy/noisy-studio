import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, ref } from "vue";

/* FOUR APPROACHES to the provider chooser in SETTINGS (stories only).
 *
 * Krzysztof's brief: the current form is four decisions where one belongs,
 * and it must live INLINE on the settings page - no modal. Each concept
 * below shows: the current engine, what's on disk locally (name + size +
 * downloaded-or-not), switching, a download in progress, and where
 * "advanced" (mixed directions, whisper size, voice) lives.
 *
 * Nothing here is wired - review, pick one, then it gets implemented.
 * Benchmark context baked into the copy: local STT (whisper tiny/base) is
 * faster than realtime; local TTS (Kokoro) takes ~5 s per reply on this
 * machine - the concepts surface that honestly.
 */

const meta: Meta = { title: "Lab/ProviderChooserOptions" };
export default meta;

// Shared mock state: what the daemon would report.
const MODELS = [
  { name: "Kokoro voice model", size: "326 MB", done: true },
  { name: "Kokoro voices pack", size: "27 MB", done: true },
  { name: "Whisper base", size: "74 MB", done: false },
];

const SHARED_CSS = `
  .concept { font-family: var(--mono); display: grid; gap: 10px; max-width: 620px; }
  .muted { color: var(--muted); }
  .chip { font-size: 9px; letter-spacing: 0.14em; padding: 2px 8px;
          border: 1px solid var(--line-strong); }
  .chip.ok { color: var(--green); }
  .chip.todo { color: var(--cyan-dim); }
  .chip.slow { color: var(--amber); }
  .bar { height: 5px; background: rgba(4,12,20,0.9); border: 1px solid var(--line-strong); }
  .fill { height: 100%; width: 62%; background: var(--cyan); }
  .adv { font-size: 9.5px; letter-spacing: 0.16em; color: var(--cyan-dim); cursor: pointer; }
  .adv-body { display: grid; gap: 8px; padding: 10px 0 0 12px; font-size: 10px; color: var(--muted); }
  select, input[type=text] { font-family: var(--mono); font-size: 11px; color: var(--ink);
          background: rgba(4,12,20,0.9); border: 1px solid var(--line-strong); padding: 4px 8px; }
`;

/* (a) TWO CARDS - one decision. CLOUD or LOCAL sets both directions;
 * everything else folds under ADVANCED. */
const TwoCards = defineComponent({
  setup() {
    const picked = ref<"cloud" | "local">("cloud");
    const advanced = ref(false);
    return { picked, advanced, MODELS };
  },
  template: `
  <div class="concept">
    <style>${SHARED_CSS}
      .cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      .card { display: grid; gap: 8px; text-align: left; cursor: pointer; color: var(--ink);
              background: rgba(4,12,20,0.9); border: 1px solid var(--line-strong); padding: 14px; }
      .card.on { border-color: var(--cyan); box-shadow: 0 0 8px rgba(63,216,255,0.25); }
      .card-title { font-size: 10px; letter-spacing: 0.2em; color: var(--cyan); }
      .card-sub { font-size: 10px; line-height: 1.6; color: var(--muted); }
      .models { display: grid; gap: 4px; font-size: 9.5px; }
      .mrow { display: flex; justify-content: space-between; gap: 8px; }
    </style>
    <div class="cards">
      <button class="card" :class="{ on: picked === 'cloud' }" @click="picked = 'cloud'">
        <span class="card-title">CLOUD · GROK</span>
        <span class="card-sub">Natural voices, live streaming. Needs a key; pennies per hour.</span>
        <span class="chip ok">✓ KEY ····kRc9</span>
      </button>
      <button class="card" :class="{ on: picked === 'local' }" @click="picked = 'local'">
        <span class="card-title">LOCAL · OFFLINE</span>
        <span class="card-sub">Free, private, works without internet. Voice replies take ~5 s.</span>
        <span class="models">
          <span v-for="m in MODELS" :key="m.name" class="mrow">
            <span>{{ m.name }} · {{ m.size }}</span>
            <span class="chip" :class="m.done ? 'ok' : 'todo'">{{ m.done ? "✓ ON DISK" : "TO FETCH" }}</span>
          </span>
        </span>
      </button>
    </div>
    <div class="adv" @click="advanced = !advanced">ADVANCED {{ advanced ? "▴" : "▾" }}</div>
    <div v-if="advanced" class="adv-body">
      <label>TRANSCRIPTION <select><option>SAME AS ABOVE</option><option>GROK</option><option>LOCAL</option></select></label>
      <label>VOICE ENGINE <select><option>SAME AS ABOVE</option><option>GROK</option><option>LOCAL</option></select></label>
      <label>WHISPER SIZE <select><option>TINY (16x realtime)</option><option>BASE (9x)</option><option>SMALL (3x)</option></select></label>
      <label>KOKORO VOICE <select><option>AF_SARAH</option><option>AM_ADAM</option></select></label>
    </div>
  </div>`,
});

/* (b) ENGINE LIST - a radio list, one row per engine, status inline.
 * The selected row grows its own options; no separate advanced section. */
const EngineList = defineComponent({
  setup() {
    const picked = ref("grok");
    return { picked, MODELS };
  },
  template: `
  <div class="concept">
    <style>${SHARED_CSS}
      .rows { display: grid; gap: 6px; }
      .row { display: grid; gap: 6px; border: 1px solid var(--line-strong);
             background: rgba(4,12,20,0.9); padding: 10px 12px; cursor: pointer; }
      .row.on { border-color: var(--cyan); }
      .head { display: flex; align-items: center; gap: 10px; }
      .rname { font-size: 10.5px; letter-spacing: 0.16em; color: var(--ink); flex: 1; }
      .dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid var(--cyan-dim); }
      .row.on .dot { background: var(--cyan); }
      .mline { display: flex; gap: 8px; align-items: center; font-size: 9.5px; color: var(--muted);
               padding-left: 20px; }
    </style>
    <div class="rows">
      <div class="row" :class="{ on: picked === 'grok' }" @click="picked = 'grok'">
        <div class="head"><span class="dot"></span><span class="rname">GROK CLOUD</span>
          <span class="chip ok">✓ KEY</span><span class="chip ok">FASTEST</span></div>
      </div>
      <div class="row" :class="{ on: picked === 'local' }" @click="picked = 'local'">
        <div class="head"><span class="dot"></span><span class="rname">LOCAL — WHISPER + KOKORO</span>
          <span class="chip ok">FREE</span><span class="chip slow">VOICE ~5 s</span></div>
        <div v-for="m in MODELS" :key="m.name" class="mline">
          <span style="flex:1">{{ m.name }} · {{ m.size }}</span>
          <span class="chip" :class="m.done ? 'ok' : 'todo'">{{ m.done ? "✓ DOWNLOADED" : "DOWNLOAD" }}</span>
        </div>
        <div v-if="picked === 'local'" class="adv-body">
          <label>WHISPER SIZE <select><option>TINY (16x realtime)</option><option>BASE (9x)</option></select></label>
          <label>VOICE <select><option>AF_SARAH</option><option>AM_ADAM</option></select></label>
          <label><input type="checkbox" /> SPLIT DIRECTIONS (transcribe local, speak cloud)</label>
        </div>
      </div>
      <div class="row" :class="{ on: picked === 'say' }" @click="picked = 'say'">
        <div class="head"><span class="dot"></span><span class="rname">LOCAL — MACOS SAY</span>
          <span class="chip ok">ZERO SETUP</span><span class="chip slow">ROBOTIC</span></div>
      </div>
    </div>
  </div>`,
});

/* (c) SUMMARY LINE - the settings page shows ONE line; the whole chooser
 * appears in place only when asked. Cheapest screen estate. */
const SummaryLine = defineComponent({
  components: { EngineList },
  setup() {
    const open = ref(false);
    return { open };
  },
  template: `
  <div class="concept">
    <style>${SHARED_CSS}
      .summary { display: flex; align-items: center; gap: 12px; border: 1px solid var(--line-strong);
                 background: rgba(4,12,20,0.9); padding: 10px 12px; cursor: pointer; }
      .s-label { font-size: 9px; letter-spacing: 0.22em; color: var(--muted); }
      .s-value { font-size: 10.5px; letter-spacing: 0.16em; color: var(--cyan); flex: 1; }
    </style>
    <div class="summary" @click="open = !open">
      <span class="s-label">VOICE ENGINE</span>
      <span class="s-value">GROK CLOUD · READY</span>
      <span class="chip ok">✓</span>
      <span class="adv">{{ open ? "CLOSE ▴" : "CHANGE ▾" }}</span>
    </div>
    <EngineList v-if="open" />
  </div>`,
});

/* (d) SIGNAL PATH - my proposal: the chooser IS a picture of the audio
 * path. Two pills on the wire (ear and mouth); clicking a pill flips that
 * half. Mixing directions stops being an "advanced" concept - it's just
 * the two pills disagreeing. Downloads hang under the pill they belong to. */
const SignalPath = defineComponent({
  setup() {
    const ear = ref("GROK");
    const mouth = ref("LOCAL");
    const flip = (pill: typeof ear) => {
      pill.value = pill.value === "GROK" ? "LOCAL" : "GROK";
    };
    return { ear, mouth, flip, MODELS };
  },
  template: `
  <div class="concept">
    <style>${SHARED_CSS}
      .path { display: flex; align-items: center; gap: 8px; font-size: 9.5px;
              letter-spacing: 0.14em; color: var(--muted); }
      .wire { flex: 1; border-top: 1px dashed var(--line-strong); }
      .pill { font-size: 10px; letter-spacing: 0.18em; color: var(--cyan); cursor: pointer;
              border: 1px solid var(--cyan-dim); border-radius: 999px; padding: 5px 14px;
              background: rgba(4,12,20,0.9); }
      .pill:hover { border-color: var(--cyan); }
      .under { display: grid; gap: 4px; margin-left: 90px; font-size: 9.5px; color: var(--muted); }
      .mrow { display: flex; gap: 8px; align-items: center; }
    </style>
    <div class="path">
      <span>YOUR MIC</span><span class="wire"></span>
      <button class="pill" title="click to switch" @click="flip(ear)">{{ ear }} HEARS</button>
      <span class="wire"></span><span>CLAUDE</span><span class="wire"></span>
      <button class="pill" @click="flip(mouth)">{{ mouth }} SPEAKS</button>
      <span class="wire"></span><span>SPEAKERS</span>
    </div>
    <div v-if="mouth === 'LOCAL'" class="under">
      <div class="mrow"><span style="flex:1">Kokoro voice model · 326 MB</span><span class="chip ok">✓ ON DISK</span></div>
      <div class="mrow"><span style="flex:1">Whisper base · 74 MB</span>
        <div class="bar" style="flex:2"><div class="fill"></div></div><span class="chip todo">62%</span></div>
      <div class="mrow muted">voice replies take ~5 s on this machine · free · offline</div>
    </div>
    <div class="adv">ADVANCED ▾ <span class="muted">(whisper size, voice, retry downloads)</span></div>
  </div>`,
});

export const A_TwoCards: StoryObj = { render: () => TwoCards };
export const B_EngineList: StoryObj = { render: () => EngineList };
export const C_SummaryLine: StoryObj = { render: () => SummaryLine };
export const D_SignalPath: StoryObj = { render: () => SignalPath };
