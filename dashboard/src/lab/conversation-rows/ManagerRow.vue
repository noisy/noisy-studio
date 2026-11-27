<script setup lang="ts">
// A manager conversation: two lines in fixed slots. Left, the mic slot
// (green mic on the conversation that receives your speech, empty
// otherwise); right, the wait/wake time and the ONE status signal. Hover
// lays Snooze and Settle over line 2, so nothing reflows.
import { computed } from "vue";
import LabIcon from "./LabIcon.vue";
import { cornerOf, isSnoozed, signalOf, type ManagerConversation } from "./orgModel";

// Geometry knobs.
const ROW_PX = 40;
const MIC_SLOT_PX = 16;
const SIGNAL_SLOT_PX = 22;
const TIME_SLOT_PX = 34;

const props = defineProps<{ manager: ManagerConversation; now: number; mic: boolean; viewed: boolean; forced?: boolean; menuOpen?: boolean }>();
defineEmits<{ select: []; snooze: []; settle: [] }>();

const signal = computed(() => signalOf(props.manager));
const snoozed = computed(() => isSnoozed(props.manager, props.now));
const corner = computed(() => cornerOf(props.manager, props.now));
const secondLine = computed(() => {
  const where = [props.manager.harness ?? "Unknown harness", props.manager.branch].filter(Boolean).join(" · ");
  return props.manager.status === "working" && props.manager.activity ? null : where;
});
const style = {
  "--row": `${ROW_PX}px`, "--mic-slot": `${MIC_SLOT_PX}px`, "--signal-slot": `${SIGNAL_SLOT_PX}px`, "--time-slot": `${TIME_SLOT_PX}px`,
};
</script>

<template>
  <div class="manager" :style="style" role="button" tabindex="0" :title="manager.title"
    :class="{ mic, viewed, snoozed, forced: forced || menuOpen }"
    @click="$emit('select')" @keydown.enter.self="$emit('select')">
    <span class="mic-slot" :aria-label="mic ? 'Receives your speech' : undefined"><LabIcon v-if="mic" name="mic" :size="13" /></span>
    <div class="text">
      <div class="l1">
        <span class="title clip">{{ manager.title }}</span>
        <span class="time" :class="{ wake: snoozed }"><LabIcon v-if="snoozed" name="snooze" :size="10" />{{ corner }}</span>
        <span class="signal" :data-signal="signal ?? 'none'">
          <svg v-if="signal === 'muted'" class="mute" viewBox="0 0 14 14" aria-label="muted">
            <path d="M2 5.2 L5 5.2 L8.2 2.6 L8.2 11.4 L5 8.8 L2 8.8 Z" fill="currentColor" />
            <path d="M10 5 13 9 M13 5 10 9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          </svg>
          <span v-else-if="signal === 'speaking'" class="eq" aria-label="speaking"><i /><i /><i /></span>
          <span v-else-if="signal === 'queued'" class="count" :aria-label="`${manager.queued} to hear`">{{ manager.queued }}</span>
          <span v-else-if="signal === 'working'" class="dots" aria-label="working"><i /><i /><i /></span>
        </span>
      </div>
      <div class="l2 clip">
        <template v-if="secondLine !== null">{{ secondLine }}</template>
        <span v-else class="activity">{{ manager.activity }}</span>
      </div>
    </div>
    <div class="actions">
      <button type="button" data-snooze-toggle :class="{ on: menuOpen }" @click.stop="$emit('snooze')"><LabIcon name="snooze" :size="12" />Snooze</button>
      <button type="button" @click.stop="$emit('settle')"><LabIcon name="settle" :size="12" />Settle</button>
    </div>
  </div>
</template>

<style scoped>
.manager { position:relative; display:flex; align-items:center; gap:6px; height:var(--row); padding:0 8px 0 4px; border:1px solid transparent; border-radius:8px; color:var(--ink); font:13px var(--sans); cursor:pointer; outline:none; box-sizing:border-box; }
.manager:hover, .manager.forced, .manager:focus-visible { background:var(--surface-hover); }
.manager.viewed { background:var(--surface-hover); border-color:var(--line-strong); }
/* The mic recipient: an inset green edge (no size change) + the mic glyph. */
.manager.mic { box-shadow:inset 2px 0 0 var(--green); }
.mic-slot { flex:none; display:grid; place-items:center; width:var(--mic-slot); align-self:flex-start; margin-top:5px; color:var(--green); }
.text { flex:1; min-width:0; display:flex; flex-direction:column; gap:1px; }
.l1 { display:flex; align-items:center; gap:4px; min-width:0; }
.clip { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.title { flex:1; font-weight:600; }
.time { flex:none; display:inline-flex; align-items:center; justify-content:flex-end; gap:2px; min-width:var(--time-slot); font-size:11px; font-variant-numeric:tabular-nums; color:var(--muted); }
.signal { flex:none; display:inline-flex; align-items:center; justify-content:flex-end; width:var(--signal-slot); height:16px; }
.l2 { font-size:11px; color:var(--muted); }
.activity { color:var(--violet-dim); }
.snoozed .title, .snoozed .l2 { opacity:.55; }
.mute { width:14px; height:14px; color:var(--red); }
.eq { display:flex; gap:2px; align-items:center; height:12px; }
.eq i { width:2px; height:9px; border-radius:1px; background:var(--green); animation:eq 1s ease-in-out infinite; }
.eq i:nth-child(2) { height:12px; animation-delay:.2s; }
.eq i:nth-child(3) { animation-delay:.4s; }
.count { min-width:18px; height:16px; padding:0 5px; border-radius:8px; box-sizing:border-box; font:600 10px/16px var(--sans); text-align:center; color:var(--bg0); background:var(--amber); }
.dots { display:flex; gap:3px; }
.dots i { width:4px; height:4px; border-radius:50%; background:var(--violet); animation:dot 1.4s ease-in-out infinite; }
.dots i:nth-child(2) { animation-delay:.2s; }
.dots i:nth-child(3) { animation-delay:.4s; }
/* Over line 2, so the title, wait time and signal stay readable. */
.actions { position:absolute; bottom:2px; right:6px; display:flex; gap:4px; padding-left:18px; background:linear-gradient(to right, transparent, var(--surface-hover) 18px); opacity:0; pointer-events:none; }
.manager:hover .actions, .manager.forced .actions, .manager:focus-within .actions { opacity:1; pointer-events:auto; }
.actions button { display:inline-flex; align-items:center; gap:4px; height:17px; padding:0 7px; border:1px solid var(--line-strong); border-radius:6px; background:var(--panel-solid); color:var(--ink); font:10.5px var(--sans); cursor:pointer; }
.actions button:hover, .actions button.on { border-color:var(--muted); }
@keyframes eq { 50% { transform:scaleY(.5); } }
@keyframes dot { 0%, 100% { opacity:.35; } 40% { opacity:1; } }
@media (prefers-reduced-motion: reduce) { .eq i, .dots i { animation:none; } }
</style>
