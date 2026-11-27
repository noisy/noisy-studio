<script setup lang="ts">
// Hover details for a manager conversation, shown after a short delay to
// the right of the list, over the frame. `compact` is option B's tooltip.
import { computed } from "vue";
import { CHILD_TONE, childSummary, hueOf, initialOf, statusLine, type LabRow } from "./fixtures";

const props = defineProps<{ row: LabRow; compact?: boolean }>();
const status = computed(() => statusLine(props.row));
const childState = { working: "running", blocked: "blocked", review: "to review", done: "done", pending: "pending" } as const;
</script>

<template>
  <div v-if="compact" class="card compact">
    <div class="title">{{ row.title }}</div>
    <div class="mono">{{ row.path ?? "No project" }}<template v-if="row.branch"> · {{ row.branch }}</template></div>
    <div>{{ row.harness ?? "Unknown harness" }} · started {{ row.started }}</div>
    <div v-if="row.children.length">Delegated: {{ childSummary(row.children).text }}</div>
    <div v-if="row.shortcut"><kbd>Tab {{ row.shortcut }}</kbd></div>
  </div>
  <div v-else class="card" :style="hueOf(row) != null ? { '--hue': String(hueOf(row)) } : {}">
    <div class="head">
      <span class="tile" :class="{ legacy: !row.project }">{{ initialOf(row) }}</span>
      <div class="where">
        <div class="project">{{ row.project ?? "No project" }}</div>
        <div class="mono">{{ row.path ?? "working folder unknown" }}</div>
      </div>
    </div>
    <div class="title">{{ row.title }}</div>
    <div class="status" :class="status.tone">{{ status.text }}</div>
    <div v-if="row.children.length" class="kids">
      <div class="label">Delegated</div>
      <div v-for="child in row.children" :key="child.id" class="kid">
        <span class="kdot" :class="CHILD_TONE[child.state]" />
        <span class="ktitle">{{ child.title }}</span>
        <span class="kstate" :class="CHILD_TONE[child.state]">{{ child.progress ?? childState[child.state] }}</span>
        <span class="kwho">{{ child.who }}<template v-if="child.note"> · {{ child.note }}</template></span>
      </div>
    </div>
    <dl>
      <dt>Branch</dt><dd class="mono">{{ row.branch ?? "—" }}</dd>
      <dt>Harness</dt><dd>{{ row.harness ?? "—" }}</dd>
      <dt>Started</dt><dd>{{ row.started }} · last activity {{ row.lastActivity }}</dd>
      <dt>Hotkey</dt><dd><kbd v-if="row.shortcut">Tab {{ row.shortcut }}</kbd><template v-else>—</template></dd>
      <template v-if="row.mic"><dt>Mic</dt><dd class="green">Receives your speech</dd></template>
      <dt>Id</dt><dd class="mono">{{ row.shortId }}</dd>
    </dl>
  </div>
</template>

<style scoped>
.card { width:280px; padding:12px; border:1px solid var(--line-strong); border-radius:12px; background:var(--panel-solid); box-shadow:0 12px 32px rgba(0,0,0,.35); font:12px/1.4 var(--sans); color:var(--ink); display:flex; flex-direction:column; gap:8px; }
.card.compact { width:240px; gap:3px; padding:8px 10px; border-radius:8px; color:var(--muted); font-size:11px; }
.compact .title { font-size:12px; margin-bottom:2px; }
.head { display:flex; align-items:center; gap:8px; }
.tile { flex:none; width:24px; height:24px; border-radius:6px; font:600 12px/24px var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.tile.legacy { color:var(--muted); background:var(--line); }
.where { min-width:0; }
.project { font-weight:600; font-size:12px; }
.mono { font:10.5px var(--mono); color:var(--muted); overflow-wrap:anywhere; }
.title { font-size:14px; font-weight:600; line-height:1.3; }
.status { font-size:12px; }
.status.ink { color:var(--ink); } .status.green, .green { color:var(--green); } .status.amber { color:var(--amber); }
.status.violet { color:var(--violet-dim); } .status.red { color:var(--red); } .status.muted { color:var(--muted); }
.kids { display:flex; flex-direction:column; gap:5px; padding:8px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.label, dt { font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
.kid { display:grid; grid-template-columns:10px 1fr auto; column-gap:6px; align-items:center; }
.kdot { width:6px; height:6px; border-radius:50%; }
.kdot.violet { background:var(--violet); } .kdot.amber { background:var(--amber); } .kdot.muted { background:var(--line-strong); }
.ktitle { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.kstate { font-size:11px; font-variant-numeric:tabular-nums; }
.kstate.violet { color:var(--violet-dim); } .kstate.amber { color:var(--amber); font-weight:600; } .kstate.muted { color:var(--muted); }
.kwho { grid-column:2 / 4; font-size:10.5px; color:var(--muted); }
dl { display:grid; grid-template-columns:62px 1fr; gap:4px 8px; align-items:baseline; }
dd { min-width:0; }
kbd { padding:0 5px; border:1px solid var(--line-strong); border-radius:4px; font:10.5px var(--mono); color:var(--ink); }
</style>
