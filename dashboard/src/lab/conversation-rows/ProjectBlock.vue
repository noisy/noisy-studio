<script setup lang="ts">
// One project: a header that says what it is achieving and what it costs,
// then its manager conversations, each with its delegated agents hanging
// underneath. Finished agents fold into "+N done". Overlays (snooze menu,
// details card) are positioned here but owned by the list.
import { computed, ref } from "vue";
import AgentRow from "./AgentRow.vue";
import LabIcon from "./LabIcon.vue";
import ManagerRow from "./ManagerRow.vue";
import ProjectCard from "./ProjectCard.vue";
import ResourceStrip from "./ResourceStrip.vue";
import SnoozeMenu from "./SnoozeMenu.vue";
import { demandsOf, hueOf, initialOf, orderAgents, runningOf, type OrgAction, type Project } from "./orgModel";

// Geometry knobs.
const TILE_PX = 22;
const DEMAND_SLOT_PX = 20;

const props = defineProps<{
  project: Project; now: number; micId: string | null; viewedId: string | null;
  menuFor: string | null; peek: boolean; pinned: string[];
}>();
const emit = defineEmits<{ act: [action: OrgAction] }>();

const legacy = computed(() => !props.project.name);
const demands = computed(() => demandsOf(props.project, props.now));
const running = computed(() => runningOf(props.project));
const busy = computed(() => running.value.agents + running.value.managers);
const hue = computed(() => hueOf(props.project));
const demandTitle = computed(() => demands.value.map((demand) => demand.text).join("\n"));

const showDone = ref(new Set<string>());
function toggleDone(manager: string) {
  const next = new Set(showDone.value);
  if (!next.delete(manager)) next.add(manager);
  showDone.value = next;
}
const act = (action: OrgAction) => emit("act", action);
const peekAction = (type: "peek" | "unpeek" | "holdPeek") => act({ type, project: props.project.id });
// Tabbing into the card's own buttons keeps it open.
function focusLeft(event: FocusEvent) {
  const header = event.currentTarget as HTMLElement;
  if (!header.contains(event.relatedTarget as Node | null)) peekAction("unpeek");
}
</script>

<template>
  <div class="project" :style="{ '--tile': `${TILE_PX}px`, '--demand-slot': `${DEMAND_SLOT_PX}px`, ...(hue != null ? { '--hue': String(hue) } : {}) }">
    <div class="header" tabindex="0" :class="{ legacy, forced: pinned.includes(project.id) }"
      @mouseenter="peekAction('peek')" @mouseleave="peekAction('unpeek')" @focusin="peekAction('peek')" @focusout="focusLeft">
      <span class="tile">{{ initialOf(project) }}</span>
      <div class="htext">
        <div class="hl1">
          <span class="name clip">{{ project.name ?? "No project" }}</span>
          <span class="focus-slot" :title="project.focused ? 'Focused: first in line for your attention and the plan' : undefined"><LabIcon v-if="project.focused" name="focus" :size="11" /></span>
          <span class="demand-slot"><span v-if="demands.length" class="pill" :title="demandTitle">{{ demands.length }}</span></span>
        </div>
        <div class="hl2 clip">{{ project.goal ?? (legacy ? "Folder unknown: an older harness or daemon" : "No goal stated") }}</div>
        <ResourceStrip v-if="!legacy" :running="busy" :usage="project.usage" />
      </div>
      <div v-if="!legacy" class="hactions">
        <button type="button" :class="{ on: project.focused }" @click.stop="act({ type: 'focus', project: project.id, focused: !project.focused })"><LabIcon name="focus" :size="12" />{{ project.focused ? "Unfocus" : "Focus" }}</button>
        <button v-if="running.agents" type="button" @click.stop="act({ type: 'pauseProject', project: project.id })"><LabIcon name="pause" :size="12" />Pause</button>
      </div>
      <ProjectCard v-if="peek" class="card-overlay" :project="project" :now="now"
        @mouseenter="peekAction('holdPeek')" @mouseleave="peekAction('unpeek')"
        @set-focus="(focused) => act({ type: 'focus', project: project.id, focused })"
        @pause-all="act({ type: 'pauseProject', project: project.id })" @cap="act({ type: 'cap', project: project.id })" />
    </div>

    <div class="body">
      <template v-for="manager in project.managers" :key="manager.id">
        <div class="manager-slot">
          <ManagerRow :manager="manager" :now="now" :mic="micId === manager.id" :viewed="viewedId === manager.id"
            :forced="pinned.includes(manager.id)" :menu-open="menuFor === manager.id"
            @select="act({ type: 'select', conversation: manager.id })"
            @snooze="act({ type: 'toggleSnooze', conversation: manager.id })"
            @settle="act({ type: 'settle', conversation: manager.id })" />
          <SnoozeMenu v-if="menuFor === manager.id" class="menu-overlay" :now="now"
            @pick="(until) => act({ type: 'snooze', conversation: manager.id, until })" />
        </div>
        <div v-if="manager.agents.length" class="agents">
          <AgentRow v-for="agent in orderAgents(manager.agents).open" :key="agent.id" :agent="agent" :forced="pinned.includes(agent.id)"
            @pause="act({ type: 'pause', agent: agent.id })" @resume="act({ type: 'resume', agent: agent.id })"
            @stop="act({ type: 'stop', agent: agent.id })" @review="act({ type: 'review', agent: agent.id })" />
          <template v-if="showDone.has(manager.id)">
            <AgentRow v-for="agent in orderAgents(manager.agents).done" :key="agent.id" :agent="agent" />
          </template>
          <button v-if="orderAgents(manager.agents).done.length" type="button" class="more" @click="toggleDone(manager.id)">
            {{ showDone.has(manager.id) ? "Hide done" : `+${orderAgents(manager.agents).done.length} done` }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.project { display:flex; flex-direction:column; }
.header { position:relative; display:flex; align-items:flex-start; gap:8px; padding:6px 8px 6px 4px; border-radius:8px; outline:none; cursor:default; }
.header:hover, .header.forced, .header:focus-visible { background:var(--surface-hover); }
.tile { flex:none; width:var(--tile); height:var(--tile); margin-top:1px; border-radius:6px; font:600 12px/var(--tile) var(--sans); text-align:center; color:#fff; background:hsl(var(--hue, 0) 42% 44%); }
.legacy .tile { color:var(--muted); background:var(--line); }
.htext { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }
.hl1 { display:flex; align-items:center; gap:4px; min-width:0; height:18px; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.name { flex:1; font:600 13px var(--sans); color:var(--ink); }
.legacy .name { font-style:italic; font-weight:500; color:var(--muted); }
.focus-slot { flex:none; display:grid; place-items:center; width:12px; color:var(--cyan); }
.demand-slot { flex:none; display:flex; justify-content:flex-end; min-width:var(--demand-slot); }
.pill { min-width:18px; height:16px; padding:0 5px; border-radius:8px; box-sizing:border-box; font:700 10px/16px var(--sans); text-align:center; color:var(--bg0); background:var(--amber); }
.hl2 { font:11px var(--sans); color:var(--muted); }
.hactions { position:absolute; top:24px; right:6px; display:flex; gap:4px; padding-left:18px; background:linear-gradient(to right, transparent, var(--surface-hover) 18px); opacity:0; pointer-events:none; }
.header:hover .hactions, .header.forced .hactions, .header:focus-within .hactions { opacity:1; pointer-events:auto; }
.hactions button { display:inline-flex; align-items:center; gap:4px; height:19px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); color:var(--ink); font:10.5px var(--sans); cursor:pointer; }
.hactions button:hover, .hactions button.on { border-color:var(--muted); }
/* The tree: one guide from the project tile, one from each manager. */
.body { display:flex; flex-direction:column; gap:2px; margin-left:calc(4px + var(--tile) / 2); padding-left:4px; border-left:1px solid var(--line); }
.manager-slot { position:relative; }
.agents { display:flex; flex-direction:column; margin:0 0 4px 12px; padding-left:4px; border-left:1px solid var(--line); }
.more { align-self:flex-start; height:20px; margin-left:6px; padding:0 6px; border:0; border-radius:5px; background:transparent; color:var(--muted); font:11px var(--sans); cursor:pointer; }
.more:hover { background:var(--surface-hover); color:var(--ink); }
/* Overlays on the z-axis: solid, shadowed, never pushing the column. */
.menu-overlay { position:absolute; top:calc(100% - 2px); right:0; z-index:6; }
.card-overlay { position:absolute; top:0; left:calc(100% + 10px); z-index:5; cursor:auto; }
</style>
