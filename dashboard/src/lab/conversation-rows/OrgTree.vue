<script setup lang="ts">
// The conversation list as an org tree, project first: each project says
// what it is achieving, what it costs and what waits for you; its managers
// and their delegated agents hang underneath. Conversations without project
// data gather under "No project"; settled and ended ones fold away under
// "Settled". The list owns the overlays (one snooze menu, one details card)
// and turns row actions into its own events. Lab: actions are emitted only.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ProjectBlock from "./ProjectBlock.vue";
import SettledRow from "./SettledRow.vue";
import { arrange, type OrgAction, type Project } from "./orgModel";

// Geometry and timing knobs.
const PROJECT_GAP_PX = 10;
const CARD_OPEN_DELAY_MS = 500;
const CARD_CLOSE_DELAY_MS = 200;

const props = withDefaults(defineProps<{
  projects: Project[];
  now: number; // epoch s
  micId: string | null; // the conversation receiving your speech
  viewedId: string | null; // the conversation shown in the frame
  settledOpen?: boolean;
  openMenu?: string | null; // a conversation whose snooze menu starts open
  openCard?: string | null; // a project whose details card starts open
  pinnedHover?: string[]; // rows drawn as hovered (static stories)
}>(), { settledOpen: false, openMenu: null, openCard: null, pinnedHover: () => [] });

const emit = defineEmits<{
  select: [conversation: string];
  settle: [conversation: string];
  restore: [conversation: string];
  snooze: [conversation: string, until: number];
  pause: [agent: string];
  resume: [agent: string];
  stop: [agent: string];
  review: [agent: string];
  focus: [project: string, focused: boolean];
  pauseProject: [project: string];
  cap: [project: string];
}>();

const arranged = computed(() => arrange(props.projects));
const blocks = computed(() => [...arranged.value.projects, ...(arranged.value.unassigned ? [arranged.value.unassigned] : [])]);

const settledShown = ref(props.settledOpen);
const menuFor = ref(props.openMenu);
const cardFor = ref(props.openCard);
watch(() => props.settledOpen, (open) => { settledShown.value = open; });
watch(() => props.openMenu, (id) => { menuFor.value = id; });
watch(() => props.openCard, (id) => { cardFor.value = id; });

// The details card opens after a hover delay and lingers briefly, so the
// pointer can travel into it.
let cardTimer = 0;
function scheduleCard(project: string | null, delay: number) {
  clearTimeout(cardTimer);
  cardTimer = window.setTimeout(() => { cardFor.value = project; }, delay);
}

function onAct(action: OrgAction) {
  switch (action.type) {
    case "peek": return scheduleCard(action.project, cardFor.value ? 0 : CARD_OPEN_DELAY_MS);
    case "unpeek": return scheduleCard(null, CARD_CLOSE_DELAY_MS);
    case "holdPeek": return clearTimeout(cardTimer);
    case "toggleSnooze": menuFor.value = menuFor.value === action.conversation ? null : action.conversation; return;
    case "snooze": menuFor.value = null; return emit("snooze", action.conversation, action.until);
    case "select": return emit("select", action.conversation);
    case "settle": return emit("settle", action.conversation);
    case "restore": return emit("restore", action.conversation);
    case "pause": return emit("pause", action.agent);
    case "resume": return emit("resume", action.agent);
    case "stop": return emit("stop", action.agent);
    case "review": return emit("review", action.agent);
    case "focus": return emit("focus", action.project, action.focused);
    case "pauseProject": return emit("pauseProject", action.project);
    case "cap": return emit("cap", action.project);
  }
}

// The menu closes on Escape or a click anywhere outside it.
function onPointerDown(event: PointerEvent) {
  const target = event.target as Element | null;
  if (menuFor.value && !target?.closest(".menu-overlay, [data-snooze-toggle]")) menuFor.value = null;
}
function onKey(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  menuFor.value = null;
  cardFor.value = null;
}
onMounted(() => { window.addEventListener("pointerdown", onPointerDown); window.addEventListener("keydown", onKey); });
onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", onPointerDown);
  window.removeEventListener("keydown", onKey);
  clearTimeout(cardTimer);
});
</script>

<template>
  <div class="org-tree" :style="{ '--project-gap': `${PROJECT_GAP_PX}px` }">
    <ProjectBlock v-for="project in blocks" :key="project.id" :project="project" :now="now"
      :mic-id="micId" :viewed-id="viewedId" :menu-for="menuFor" :peek="cardFor === project.id" :pinned="pinnedHover"
      @act="onAct" />
    <p v-if="!blocks.length && !arranged.settled.length" class="empty">No conversations yet. Start Claude Code or Codex in a project and it appears here.</p>

    <template v-if="arranged.settled.length">
      <button type="button" class="section" :aria-expanded="settledShown" @click="settledShown = !settledShown">
        <span class="chev" :class="{ open: settledShown }">▸</span> Settled <b>{{ arranged.settled.length }}</b>
      </button>
      <template v-if="settledShown">
        <SettledRow v-for="{ project, manager } in arranged.settled" :key="manager.id" :project="project" :manager="manager" :now="now"
          :forced="pinnedHover.includes(manager.id)" @select="emit('select', manager.id)" @restore="emit('restore', manager.id)" />
      </template>
    </template>
  </div>
</template>

<style scoped>
.org-tree { display:flex; flex-direction:column; gap:var(--project-gap); font:13px var(--sans); color:var(--ink); }
.section { display:flex; align-items:center; gap:6px; margin:4px 0 0; padding:4px 8px; border:0; border-radius:6px; background:transparent; font:10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); cursor:pointer; text-align:left; }
.section:hover { background:var(--surface-hover); }
.section b { font-weight:500; color:var(--ink); letter-spacing:0; }
.chev { display:inline-block; font-size:10px; transition:transform .12s; }
.chev.open { transform:rotate(90deg); }
.empty { padding:12px 8px; font-size:12px; color:var(--muted); }
</style>
