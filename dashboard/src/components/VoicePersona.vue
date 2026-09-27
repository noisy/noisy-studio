<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from "vue";
import CharacterReadout from "./CharacterReadout.vue";
import type { Character } from "../types";
import VoiceSelector from "./VoiceSelector.vue";
import VoiceAvatar from "./VoiceAvatar.vue";

// Voice identity, quick mute, and the voice picker for the viewed session.
const props = defineProps<{
  voice: string;
  character?: Character | null;
  voiceLabels?: Record<string, string>;
  speaking?: boolean;
  muted?: boolean;
  pending?: boolean;
  error?: string;
}>();

defineEmits<{ change: [voice: string]; "toggle-mute": []; characterChange: [patch: Partial<Character>] }>();

const popup = ref<"voice" | "character" | null>(null);
const characterTrigger = ref<HTMLButtonElement | null>(null);
const characterPanel = ref<HTMLElement | null>(null);
const availableHeight = ref(360);
function measure() {
  const button = characterTrigger.value;
  if (!button) return;
  const bottom = Math.min(window.innerHeight, button.closest(".convo-rail")?.getBoundingClientRect().bottom ?? window.innerHeight);
  availableHeight.value = Math.max(80, bottom - button.getBoundingClientRect().bottom - 14);
}
async function toggleCharacter() {
  popup.value = popup.value === "character" ? null : "character";
  if (popup.value !== "character") return;
  measure();
  await nextTick();
  characterPanel.value?.querySelector<HTMLElement>("input, button")?.focus({ preventScroll: true });
}
function dismiss(event: Event) {
  if (popup.value !== "character" || !(event.target instanceof Node)) return;
  if (characterPanel.value?.contains(event.target) || characterTrigger.value?.contains(event.target)) return;
  popup.value = null;
}
function escape(event: KeyboardEvent) {
  if (event.key === "Escape" && popup.value === "character") {
    popup.value = null;
    characterTrigger.value?.focus({ preventScroll: true });
  }
}
onMounted(() => {
  document.addEventListener("pointerdown", dismiss);
  document.addEventListener("focusin", dismiss);
  document.addEventListener("keydown", escape);
  window.addEventListener("resize", measure);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", dismiss);
  document.removeEventListener("focusin", dismiss);
  document.removeEventListener("keydown", escape);
  window.removeEventListener("resize", measure);
});
</script>

<template>
  <div class="persona" :class="{ speaking, muted }">
    <div class="frame">
      <button class="portrait"
        :aria-label="muted ? 'Unmute this conversation' : 'Mute this conversation'"
        :aria-pressed="!!muted" @click="$emit('toggle-mute')">
        <VoiceAvatar :voice="voice" :size="96" />
      </button>
      <span v-if="speaking && !muted" class="onair">Speaking</span>
      <div class="identity-actions">
      <button
        class="mutebtn" :aria-pressed="!!muted"
        :class="{ on: muted }"
        :title="muted ? 'Unmute this conversation' : 'Mute this conversation'"
        @click.stop="$emit('toggle-mute')"
      >{{ muted ? "Unmute" : "Mute" }}</button>
      <button v-if="character" ref="characterTrigger" class="character-button" :aria-expanded="popup === 'character'" aria-haspopup="dialog" @click="toggleCharacter">Character</button>
      </div>
    </div>
    <div v-if="popup === 'character' && character" ref="characterPanel" class="character-popover" role="dialog" aria-label="Character settings" :style="{ maxHeight: availableHeight + 'px' }">
      <CharacterReadout :character="character" @change="$emit('characterChange', $event)" />
    </div>
    <VoiceSelector :open="popup === 'voice'" @update:open="popup = $event ? 'voice' : popup === 'voice' ? null : popup" :voice="voice" :voice-labels="voiceLabels" @change="(v) => $emit('change', v)" />
    <p v-if="pending" class="save-feedback" role="status">Saving…</p>
    <p v-else-if="error" class="save-feedback" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>

.save-feedback { margin:0; font:12px var(--sans); color:var(--ink); }
.persona { position:relative; display:flex; flex-direction:column; gap:12px; }
.frame { position:relative; display:grid; grid-template-columns:96px minmax(0,1fr); align-items:start; gap:12px; }
.portrait { display:flex; flex:none; border:0; background:none; border-radius:18px; }
.mutebtn { width:100%; min-width:0; min-height:48px; padding:10px 12px; font:14px var(--sans); background:var(--bg1); border:1px solid var(--line); color:var(--ink); }
.mutebtn:hover { border-color:var(--line-strong); }
.mutebtn.on { color:var(--red); border-color:var(--red); }
.muted .portrait { filter:grayscale(.7); }
.onair { position:absolute; left:0; bottom:-5px; font:10px var(--sans); padding:2px 5px; background:var(--panel-solid); color:var(--green); border:1px solid var(--line); border-radius:4px; }

.identity-actions { display:flex; flex-direction:column; gap:4px; }
.character-button { min-height:44px; padding:8px 10px; border:1px solid var(--line); border-radius:7px; background:var(--bg1); color:var(--ink); font:12px var(--sans); cursor:pointer; }
.character-button:hover, .character-button[aria-expanded="true"] { border-color:var(--brand-accent); }
.character-popover { position:absolute; top:102px; left:0; right:0; z-index:25; box-sizing:border-box; overflow-y:auto; overscroll-behavior:contain; scrollbar-width:thin; padding:12px; border:1px solid var(--line-strong); border-radius:8px; background:var(--panel-solid, #071626); box-shadow:0 12px 28px #0006; }
button:focus-visible { outline:2px solid var(--brand-accent); outline-offset:2px; }
</style>
