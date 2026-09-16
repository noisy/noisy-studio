<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { VOICES } from "./characterMath";
import VoiceAvatar from "./VoiceAvatar.vue";

// The voice picker: a collapsed current pick that unfolds into a
// scrollable list (portrait thumb left, name right). Emits the new voice
// name; persisting it is the parent's business.
const props = defineProps<{ voice: string; voiceLabels?: Record<string, string> }>();
const emit = defineEmits<{ change: [voice: string] }>();

const THUMB_PX = 44;
const ROW_PX = THUMB_PX + 8;
const availableHeight = ref(364);
const listStyle = computed(() => ({
  "--thumb": `${THUMB_PX}px`, "--row": `${ROW_PX}px`,
  maxHeight: `${availableHeight.value}px`,
}));
const root = ref<HTMLElement | null>(null);
function measureAvailableHeight() {
  const button = trigger.value;
  if (button) {
    const rail = button.closest('.convo-rail');
    const bottom = Math.min(window.innerHeight, rail?.getBoundingClientRect().bottom ?? window.innerHeight);
    availableHeight.value = Math.max(ROW_PX, bottom - button.getBoundingClientRect().bottom - 8);
  }
}
async function toggle() {
  if (open.value) { close(); return; }
  measureAvailableHeight();
  open.value = true;
  await nextTick();
  const selected = root.value?.querySelector<HTMLButtonElement>('.row.sel');
  selected?.focus({ preventScroll: true });
  selected?.scrollIntoView?.({ block: 'nearest' });
}
function dismissOutside(event: PointerEvent) {
  if (open.value && event.target instanceof Node && !root.value?.contains(event.target)) open.value = false;
}
function updateOnResize() { if (open.value) measureAvailableHeight(); }
onMounted(() => {
  document.addEventListener('pointerdown', dismissOutside);
  window.addEventListener('resize', updateOnResize);
});
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', dismissOutside);
  window.removeEventListener('resize', updateOnResize);
});

const open = ref(false);
const trigger = ref<HTMLButtonElement | null>(null);
function close() {
  open.value = false;
  trigger.value?.focus();
}
function pick(name: string) {
  close();
  if (name !== props.voice) emit("change", name);
}
</script>

<template>
  <div ref="root" class="voiceselector">
    <button ref="trigger" class="voicecur" type="button" :aria-expanded="open" aria-label="Choose voice" @click="toggle" @keydown.escape="close">
      <span class="lbl">VOICE</span>
      <svg width="14" height="14" viewBox="0 0 14 14">
        <circle cx="7" cy="7" r="5.5" fill="none" stroke="var(--violet)" stroke-width="1" />
        <circle cx="7" cy="7" r="2" fill="var(--violet)" />
      </svg>
      <span class="vname">{{ (voiceLabels?.[voice] ?? voice).toUpperCase() || "—" }}</span>
      <span class="arrow">{{ open ? "▴" : "▾" }}</span>
    </button>
    <div v-if="open" class="voicelist" :style="listStyle">
      <button
        v-for="(gender, name) in VOICES"
        :key="name"
        class="row" :aria-pressed="name === voice" @keydown.escape.stop="close"
        :class="{ sel: name === voice }"
        :title="gender"
        @click="pick(name)"
      >
        <VoiceAvatar class="thumb" :voice="name" :size="THUMB_PX" />
        <span class="name">{{ (voiceLabels?.[name] ?? name).toUpperCase() }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.voiceselector { position: relative; }
.voicecur {
  width:100%;
  display: flex; align-items: center; gap: 10px;
  border: 1px solid var(--line-strong); padding: 7px 12px;
  background: color-mix(in srgb, var(--violet) 6%, transparent); cursor: pointer;
  border-radius: 8px;
}
.voicecur .lbl { font-size: 11px; letter-spacing: normal; color: var(--muted); }
.voicecur .vname { font-size: 13px; letter-spacing: normal; color: var(--cyan-hi); text-shadow: none; }
.voicecur .arrow { margin-left: auto; color: var(--cyan-dim); font-size: 11px; }
.voicelist {
  position: absolute;
  top:calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 20;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
  background: var(--panel-solid, #071626);
  border: 1px solid var(--line-strong);
  box-shadow: 0 12px 28px #0006;
  border-radius: 8px;
}
.row {
  width:100%; border:0; color:var(--ink); background:transparent; text-align:left; border-radius:0;
  display: flex;
  align-items: center;
  gap: 12px;
  height: var(--row);
  box-sizing: border-box;
  padding: 4px 12px 4px 4px;
  cursor: pointer;
  border-bottom: 1px solid color-mix(in srgb, var(--violet) 8%, transparent);
}
.row:last-child { border-bottom: none; }
.row:hover { background: color-mix(in srgb, var(--violet) 8%, transparent); }
.row.sel { background: color-mix(in srgb, var(--violet) 14%, transparent); }
.row.sel .name { color: var(--cyan-hi); text-shadow: none; }
.thumb {
  width: var(--thumb);
  height: var(--thumb);
  box-sizing: border-box;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.thumb.blank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: var(--cyan-dim);
}
.name { font-size: 15px; letter-spacing: normal; color: var(--muted); }
.row:hover .name { color: var(--cyan); }
</style>
