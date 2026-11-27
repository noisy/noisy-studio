<script setup lang="ts">
// The project's details, opened by hovering its header: what waits for you,
// what it consumes (machine, plan window, money) and who consumes it, and
// the CEO's levers. An overlay to the right of the list; nothing reflows.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { clockLabel, demandsOf, hueOf, initialOf, isLive, percent, runningOf, tokensLabel, type Project } from "./orgModel";

// Geometry knobs.
const CARD_PX = 300;
const CONSUMERS_SHOWN = 5;

const props = defineProps<{ project: Project; now: number }>();
defineEmits<{ setFocus: [focused: boolean]; pauseAll: []; cap: [] }>();

const demands = computed(() => demandsOf(props.project, props.now));
const running = computed(() => runningOf(props.project));
const usage = computed(() => props.project.usage);
// Who spends the project's tokens today, biggest first.
const consumers = computed(() =>
  props.project.managers.filter(isLive)
    .flatMap((manager) => [
      { id: manager.id, name: manager.title, kind: "manager", tokens: manager.tokens ?? 0 },
      ...manager.agents.map((agent) => ({ id: agent.id, name: agent.title, kind: agent.who, tokens: agent.tokens ?? 0 })),
    ])
    .filter((consumer) => consumer.tokens > 0)
    .sort((a, b) => b.tokens - a.tokens)
    .slice(0, CONSUMERS_SHOWN),
);
const hue = computed(() => hueOf(props.project));
</script>

<template>
  <div class="card" :style="{ width: `${CARD_PX}px`, ...(hue != null ? { '--hue': String(hue) } : {}) }" @click.stop>
    <div class="head">
      <span class="tile" :class="{ legacy: !project.name }">{{ initialOf(project) }}</span>
      <div class="where">
        <div class="name">{{ project.name ?? "No project" }}<LabIcon v-if="project.focused" class="focused" name="focus" :size="11" /></div>
        <div class="mono">{{ project.path ?? "working folder unknown" }}</div>
      </div>
    </div>
    <div v-if="project.goal" class="goal">{{ project.goal }}</div>

    <section>
      <h3 :class="{ amber: demands.length }">Waiting for you · {{ demands.length }}</h3>
      <ul v-if="demands.length" class="demands">
        <li v-for="demand in demands" :key="demand.kind + (demand.agent ?? demand.conversation ?? '')" :class="demand.kind">{{ demand.text }}</li>
      </ul>
      <p v-else class="quiet">Nothing. It can run without you.</p>
    </section>

    <section>
      <h3>Resources</h3>
      <dl>
        <dt>Machine</dt>
        <dd>
          <span :class="{ violet: running.agents + running.managers > 0 }">{{ running.agents + running.managers }} running</span>
          <template v-if="running.paused"> · {{ running.paused }} paused</template>
          · {{ project.worktrees ?? 0 }} worktrees
        </dd>
        <template v-if="usage">
          <dt>Window</dt>
          <dd>
            <div class="bar" :title="`This project ${percent(usage.share)}, everything ${percent(usage.windowUsed)}`">
              <span class="all" :style="{ width: `${Math.min(1, usage.windowUsed) * 100}%` }" />
              <span class="mine" :class="{ over: usage.cap != null && usage.share > usage.cap }" :style="{ width: `${Math.min(1, usage.share) * 100}%` }" />
              <span v-if="usage.cap != null" class="cap" :style="{ left: `${usage.cap * 100}%` }" />
            </div>
            {{ percent(usage.share) }} of {{ usage.window }}<span class="dim"> · all {{ percent(usage.windowUsed) }}<template v-if="usage.resetsAt"> · resets {{ clockLabel(usage.resetsAt, now) }}</template></span>
          </dd>
          <dt>Weekly</dt><dd>{{ percent(usage.weeklyShare) }} of the week</dd>
          <dt>Today</dt><dd>{{ tokensLabel(usage.tokens) }} tokens <span class="dim">· ≈ ${{ usage.costUsd.toFixed(2) }} at API prices</span></dd>
          <dt>Cap</dt><dd :class="{ amber: usage.cap != null && usage.share > usage.cap }">{{ usage.cap != null ? `${percent(usage.cap)} of the window` : "none" }}</dd>
        </template>
        <template v-else><dt>Usage</dt><dd class="dim">Not reported by this conversation's harness.</dd></template>
      </dl>
    </section>

    <section v-if="consumers.length">
      <h3>Biggest consumers today</h3>
      <div v-for="consumer in consumers" :key="consumer.id" class="consumer">
        <span class="cname">{{ consumer.name }}</span><span class="ckind">{{ consumer.kind }}</span><span class="ctokens">{{ tokensLabel(consumer.tokens) }}</span>
      </div>
    </section>

    <div v-if="project.name" class="levers">
      <button type="button" :class="{ on: project.focused }" @click="$emit('setFocus', !project.focused)"><LabIcon name="focus" :size="12" />{{ project.focused ? "Unfocus" : "Focus" }}</button>
      <button type="button" :disabled="running.agents === 0" @click="$emit('pauseAll')"><LabIcon name="pause" :size="12" />Pause agents</button>
      <button type="button" @click="$emit('cap')"><LabIcon name="cap" :size="12" />{{ usage?.cap != null ? "Change cap" : "Set cap" }}</button>
    </div>
  </div>
</template>

<style scoped>
.card { padding:12px; border:1px solid var(--line-strong); border-radius:12px; background:var(--panel-solid); box-shadow:0 12px 32px rgba(0,0,0,.35); font:12px/1.4 var(--sans); color:var(--ink); display:flex; flex-direction:column; gap:10px; box-sizing:border-box; }
.head { display:flex; align-items:center; gap:8px; }
.tile { flex:none; width:24px; height:24px; border-radius:6px; font:600 12px/24px var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.tile.legacy { color:var(--muted); background:var(--line); }
.where { min-width:0; }
.name { display:flex; align-items:center; gap:5px; font-weight:600; overflow-wrap:anywhere; }
.focused { color:var(--cyan); }
.mono { font:10.5px var(--mono); color:var(--muted); overflow-wrap:anywhere; }
.goal { font-size:13px; font-weight:600; line-height:1.3; }
section { display:flex; flex-direction:column; gap:5px; padding-top:8px; border-top:1px solid var(--line); }
h3, dt { font-size:10px; font-weight:500; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
h3.amber { color:var(--amber); font-weight:600; }
.demands { display:flex; flex-direction:column; gap:3px; padding-left:14px; }
.demands li::marker { color:var(--amber); }
.quiet { color:var(--muted); }
dl { display:grid; grid-template-columns:58px 1fr; gap:5px 8px; align-items:baseline; }
dd { min-width:0; }
.dim { color:var(--muted); }
.violet { color:var(--violet-dim); }
.amber { color:var(--amber); font-weight:600; }
.bar { position:relative; height:6px; margin:4px 0 3px; border-radius:3px; background:var(--line); }
.bar .all, .bar .mine { position:absolute; inset:0 auto 0 0; border-radius:3px; }
.bar .all { background:var(--line-strong); }
.bar .mine { background:var(--ink); }
.bar .mine.over { background:var(--amber); }
.bar .cap { position:absolute; top:-3px; width:1px; height:12px; background:var(--ink); }
.consumer { display:grid; grid-template-columns:1fr auto 38px; gap:6px; align-items:baseline; font-size:11.5px; }
.cname { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ckind { font-size:10.5px; color:var(--muted); }
.ctokens { text-align:right; font-variant-numeric:tabular-nums; }
.levers { display:flex; gap:6px; padding-top:10px; border-top:1px solid var(--line); }
.levers button { display:inline-flex; align-items:center; gap:4px; height:24px; padding:0 7px; white-space:nowrap; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); color:var(--ink); font:11px var(--sans); cursor:pointer; }
.levers button:hover:not(:disabled), .levers button.on { border-color:var(--muted); }
.levers button:disabled { opacity:.45; cursor:default; }
</style>
