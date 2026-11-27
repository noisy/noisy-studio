<script setup lang="ts">
// Lab board for one conversation-row option: its notes, then the left
// column at its real width in dark and light, as a realistic desk (four
// managers + Settled) and as labelled specimens of the remaining states,
// with the snooze menu and the details card open as overlays.
import { computed, ref, type Component } from "vue";
import DetailsCard from "./DetailsCard.vue";
import RowDesk from "./RowDesk.vue";
import RowQuiet from "./RowQuiet.vue";
import RowTree from "./RowTree.vue";
import SnoozeMenu from "./SnoozeMenu.vue";
import { DESK, MENU_ROW, SECTION_TITLES, SPECIMENS, type LabRow } from "./fixtures";
import { OPTION_NOTES, type OptionKey } from "./optionNotes";

// Geometry knobs: the production left column, and the hover-card delay.
const COLUMN_PX = 268;
const DETAILS_DELAY_MS = 500;

const props = withDefaults(defineProps<{ option: OptionKey; themes?: ("dark" | "light")[]; notes?: boolean }>(), {
  themes: () => ["dark", "light"],
  notes: true,
});

const ROWS: Record<OptionKey, Component> = { a: RowQuiet, b: RowDesk, c: RowTree };
const GAPS: Record<OptionKey, number> = { a: 2, b: 6, c: 4 };
const row = computed(() => ROWS[props.option]);
const notes = computed(() => OPTION_NOTES[props.option]);

type Item = { kind: "row"; row: LabRow } | { kind: "heading"; title: string; count: number };
const deskItems = computed<Item[]>(() => {
  const rows = (section: LabRow["section"]) => DESK.filter((r) => r.section === section);
  const heading = (title: string, count: number): Item[] => (count ? [{ kind: "heading", title, count }] : []);
  const asItems = (list: LabRow[]): Item[] => list.map((r) => ({ kind: "row", row: r }));
  const settled = rows("settled");
  const top: Item[] = notes.value.sectioned
    ? [...asItems(rows("yourTurn")), ...heading(SECTION_TITLES.working, rows("working").length), ...asItems(rows("working"))]
    : asItems(DESK.filter((r) => r.section !== "settled"));
  return [...top, ...heading(SECTION_TITLES.settled, settled.length), ...asItems(settled)];
});
// Hovered row first (its card opens to the right), menu row last (its
// dropdown opens below, where nothing else needs to be seen).
const specimens = computed(() => [SPECIMENS.find((r) => r.id === "hover")!, ...SPECIMENS.filter((r) => r.id !== "hover"), MENU_ROW]);

// Overlays: the snooze menu opens from the Snooze button, the card after a
// hover delay. The static board starts with both open on their specimens.
const menuFor = ref<string | null>(MENU_ROW.id);
const detailsFor = ref<string | null>("hover");
let detailsTimer = 0;
function enter(id: string) {
  clearTimeout(detailsTimer);
  detailsTimer = window.setTimeout(() => { detailsFor.value = id; }, DETAILS_DELAY_MS);
}
function leave() { clearTimeout(detailsTimer); }
const toggleMenu = (id: string) => { menuFor.value = menuFor.value === id ? null : id; };
</script>

<template>
  <div class="board" :style="{ '--column': COLUMN_PX + 'px', '--gap': GAPS[option] + 'px' }">
    <header v-if="notes" class="notes">
      <h1>{{ notes.name }}</h1>
      <p class="pitch">{{ notes.pitch }}</p>
      <div class="grid">
        <section><h2>Always visible</h2><ul><li v-for="line in notes.always" :key="line">{{ line }}</li></ul></section>
        <section><h2>Hover only</h2><ul><li v-for="line in notes.hover" :key="line">{{ line }}</li></ul></section>
        <section><h2>Section-specific</h2><ul><li v-for="line in notes.section" :key="line">{{ line }}</li></ul></section>
        <section><h2>Details card / tooltip</h2><ul><li v-for="line in notes.card" :key="line">{{ line }}</li></ul></section>
        <section><h2>Dropped from T3</h2><ul><li v-for="line in notes.droppedFromT3" :key="line">{{ line }}</li></ul></section>
      </div>
    </header>

    <div v-for="theme in themes" :key="theme" class="band" :class="`theme-${theme}`">
      <div class="block">
        <div class="cap">{{ theme }} · desk</div>
        <div class="column">
          <template v-for="item in deskItems" :key="item.kind === 'row' ? item.row.id : item.title">
            <div v-if="item.kind === 'heading'" class="section"><span class="chev">▾</span> {{ item.title }} <b>{{ item.count }}</b></div>
            <div v-else class="slot" @mouseenter="enter(item.row.id)" @mouseleave="leave">
              <component :is="row" :row="item.row" @snooze="toggleMenu" />
            </div>
          </template>
        </div>
      </div>

      <div class="block">
        <div class="cap">{{ theme }} · states</div>
        <div class="specimens">
          <div v-for="spec in specimens" :key="spec.id" class="specimen">
            <span class="label">{{ spec.caption }}</span>
            <div class="column slot" @mouseenter="enter(spec.id)" @mouseleave="leave">
              <component :is="row" :row="spec" @snooze="toggleMenu" />
              <SnoozeMenu v-if="menuFor === spec.id" class="overlay-menu" @pick="menuFor = null" />
              <DetailsCard v-if="detailsFor === spec.id" class="overlay-card" :row="spec" :compact="option === 'b'" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.board { min-height:100vh; background:#0d0e10; padding:24px; font:13px var(--sans); color:#d9dbe0; }
.notes { max-width:1080px; margin-bottom:20px; }
h1 { font-size:20px; font-weight:600; margin-bottom:4px; }
.pitch { max-width:760px; color:#a3a8b2; margin-bottom:14px; }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px; }
h2 { font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:#8a909b; margin-bottom:6px; }
ul { padding-left:14px; font-size:11.5px; line-height:1.45; color:#c4c8cf; }
li { margin-bottom:4px; }
.band { display:flex; gap:44px; align-items:flex-start; padding:20px 24px 270px; margin-bottom:16px; border-radius:14px; background:var(--bg0); color:var(--ink); }
.cap { margin-bottom:10px; font:600 10px var(--mono); letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
.column { width:var(--column); display:flex; flex-direction:column; gap:var(--gap); }
.slot { position:relative; }
.specimens { display:flex; flex-direction:column; gap:10px; }
.specimen { display:flex; align-items:flex-start; gap:12px; }
.label { width:110px; padding-top:8px; text-align:right; font:10px var(--mono); color:var(--muted); }
.overlay-menu { position:absolute; top:calc(100% - 2px); right:0; z-index:6; }
.overlay-card { position:absolute; top:0; left:calc(100% + 10px); z-index:5; }
.section { display:flex; align-items:center; gap:6px; margin:12px 10px 4px; font:10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.section b { font-weight:500; color:var(--ink); letter-spacing:0; }
.chev { font-size:11px; }
/* The dashboard has no light theme yet: this token set is a lab proposal. */
.theme-light {
  color-scheme: light;
  --bg0:#f3f4f6; --bg1:#ffffff; --panel:#ffffff; --panel-solid:#ffffff; --surface-hover:#e7e9ed;
  --line:#dcdfe4; --line-strong:#b4b9c2; --ink:#1c1f24; --muted:#5d6470;
  --brand-accent:#1f8a83; --amber:#1f8a83; --violet:#6a52b8; --violet-dim:#7a68b8;
  --green:#2a8656; --red:#c24545;
}
</style>
