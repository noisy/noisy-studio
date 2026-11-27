<script setup lang="ts">
// Lab mock: the conversation tabs as a vertical list in the left column,
// T3-style - what needs you stays on top, working and settled sessions
// move down and out of the way. Static data, no daemon.
import { ref } from "vue";

type RowStatus = "ready" | "waiting" | "speaking" | "working" | "offline";
interface Row { label: string; status: RowStatus; count?: number; viewed?: boolean; mic?: boolean; activity?: string }

const props = defineProps<{ settledOpen?: boolean }>();

const COLUMN_PX = 268;
const ROW_PX = 34;

const yourTurn: Row[] = [
  { label: "noisy-studio · dashboard", status: "ready", viewed: true, mic: true },
  { label: "Bucky", status: "waiting", count: 2 },
  { label: "QA docs", status: "speaking" },
  { label: "fitatu", status: "ready" },
];
const working: Row[] = [
  { label: "Bug fixing", status: "working", activity: "Bash · pytest" },
  { label: "release 3.0.0", status: "working", activity: "Thinking…" },
  { label: "mobile TestFlight", status: "working", activity: "Edit · App.swift" },
];
const settled: Row[] = ["website CTA", "grok harness", "presentation", "issue 152 live", "issue 172 review", "stream overlay", "thumbnails", "docs rename", "hotkey preview"].map(
  (label) => ({ label, status: "offline" as const }),
);
const open = ref(!!props.settledOpen);
</script>

<template>
  <div class="mock" :style="{ '--column': COLUMN_PX + 'px', '--row': ROW_PX + 'px' }">
    <aside class="column">
      <nav class="list" aria-label="Conversations">
        <button v-for="r in yourTurn" :key="r.label" class="row" :class="{ viewed: r.viewed }">
          <span class="slot">
            <span v-if="r.status === 'waiting'" class="wait">{{ r.count }}</span>
            <span v-else-if="r.status === 'speaking'" class="eq"><i /><i /><i /></span>
            <span v-else class="dot" />
          </span>
          <span class="label">{{ r.label }}</span>
          <span v-if="r.mic" class="mic">Mic</span>
          <span class="x">✕</span>
        </button>

        <div class="section">Working <b>{{ working.length }}</b></div>
        <button v-for="r in working" :key="r.label" class="row dim" :title="r.activity">
          <span class="slot"><span class="dot think" /></span>
          <span class="label">{{ r.label }}</span>
          <span class="activity">{{ r.activity }}</span>
          <span class="x">✕</span>
        </button>

        <button class="section toggle" :aria-expanded="open" @click="open = !open">
          <span class="chev" :class="{ open }">▸</span> Settled <b>{{ settled.length }}</b>
        </button>
        <template v-if="open">
          <button v-for="r in settled" :key="r.label" class="row offline">
            <span class="slot"><span class="dot" /></span>
            <span class="label">{{ r.label }}</span>
            <span class="x">✕</span>
          </button>
        </template>
      </nav>
      <section class="review"><span>Ready for review</span><b>2</b></section>
    </aside>
    <section class="frame">
      <div class="bubble agent">Done - the header now carries the mic controls. Want me to build it?</div>
      <div class="bubble you">Yes, go with option A.</div>
      <div class="frame-note">conversation frame (unchanged)</div>
    </section>
  </div>
</template>

<style scoped>
.mock { display:grid; grid-template-columns:var(--column) minmax(0,1fr); gap:20px; height:620px; background:var(--bg0); color:var(--ink); font:13px/1.4 var(--sans); padding:12px 20px; }
.column { display:flex; flex-direction:column; min-height:0; padding-right:0; }
.list { display:flex; flex-direction:column; gap:2px; overflow-y:auto; padding:2px; flex:1; min-height:0; }
button { font:inherit; color:inherit; background:none; border:1px solid transparent; cursor:pointer; text-align:left; }
.row { position:relative; flex:none; display:flex; align-items:center; gap:8px; height:var(--row); padding:0 10px; border-radius:8px; color:var(--muted); }
.row:hover { background:var(--surface-hover); color:var(--ink); }
/* The viewed row is simply selected - it does not fuse with the frame,
   which would break as soon as the list scrolls. */
.row.viewed { background:var(--surface-hover); color:var(--ink); border-color:var(--line-strong); }
.row.dim .label { color:color-mix(in srgb, var(--muted) 85%, transparent); }
.row.offline { border-style:dashed; border-color:transparent; }
.row.offline .label { opacity:.7; }
.slot { width:13px; height:13px; display:inline-flex; align-items:center; justify-content:center; flex:none; }
.dot { width:6px; height:6px; border-radius:50%; background:var(--muted); }
.think { background:var(--violet); animation:pulse 1.6s ease-in-out infinite; }
.wait { color:var(--amber); font-size:11px; }
.eq { height:12px; display:flex; gap:2px; align-items:center; }
.eq i { width:2px; height:9px; background:var(--green); }
.eq i:nth-child(2) { height:13px; }
.label { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mic { font-size:10px; color:var(--green); }
.activity { font-size:10px; color:var(--violet-dim); max-width:84px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.x { width:16px; text-align:center; color:var(--muted); opacity:0; }
.row:hover .x { opacity:1; }
.section { display:flex; align-items:center; gap:6px; margin:14px 10px 4px; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); border:0; padding:0; }
.section b { font-weight:500; color:var(--ink); letter-spacing:0; }
.toggle:hover { color:var(--ink); }
.chev { display:inline-block; font-size:12px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }
.review { display:flex; justify-content:space-between; margin:10px 0 0; padding:10px 12px; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); font-size:12px; font-weight:600; }
.review b { color:var(--amber); font-weight:500; }
.frame { position:relative; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:24px; display:flex; flex-direction:column; gap:12px; }
.bubble { max-width:60%; padding:10px 14px; border-radius:12px; border:1px solid var(--line); }
.bubble.agent { border-color:color-mix(in srgb, var(--agent-accent) 40%, var(--line)); }
.bubble.you { align-self:flex-end; background:var(--surface-hover); }
.frame-note { margin-top:auto; color:var(--muted); font-size:11px; text-align:center; }
@keyframes pulse { 50% { opacity:.5; } }
</style>
