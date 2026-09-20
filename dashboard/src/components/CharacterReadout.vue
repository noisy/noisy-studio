<script setup lang="ts">
/** Conversation-specific character settings with native keyboard controls. */
import { computed, ref, watch } from "vue";
import type { Character } from "../types";
import TraitDial from "./TraitDial.vue";
import { traitWord } from "./characterMath";

const props = defineProps<{ character: Character }>();
const emit = defineEmits<{ change: [patch: Partial<Character>] }>();

type Trait = "humor" | "honesty" | "verbosity" | "talkative";

// Editing preview: values follow the pointer instantly; the daemon's answer
// (next poll) becomes the truth and clears the preview.
const preview = ref<Partial<Character>>({});
watch(
  () => props.character,
  () => {
    preview.value = {};
  },
);
const shown = computed<Character>(() => ({ ...props.character, ...preview.value }));

const TRAITS: { key: Trait; label: string; color: string }[] = [
  { key: "humor", label: "Humor", color: "var(--cyan)" },
  { key: "honesty", label: "Honesty", color: "var(--green)" },
  { key: "verbosity", label: "Verbosity", color: "var(--amber)" },
  { key: "talkative", label: "Talkative", color: "var(--violet)" },
];

const dials = computed(() =>
  TRAITS.map((t) => {
    const value = shown.value[t.key];
    return { ...t, value, word: traitWord(t.key, value) };
  }),
);

function setTrait(trait: Trait, value: number) {
  preview.value = { ...preview.value, [trait]: value };
}
function commitTrait(trait: Trait) {
  const value = preview.value[trait];
  if (value != null) emit("change", { [trait]: value });
}

function setSpeed(event: Event) {
  const speed = Number((event.target as HTMLInputElement).value);
  preview.value = { ...preview.value, speed };
  emit("change", { speed });
}
</script>

<template>
  <div>
    <div class="gauges">
      <TraitDial
        v-for="d in dials"
        :key="d.key"
        :value="d.value"
        :label="d.label"
        :word="d.word"
        :color="d.color"
        @input="setTrait(d.key, $event)"
        @commit="commitTrait(d.key)"
      />
    </div>

    <label class="charline">
      <span class="speed-heading"><span>Speed</span><span class="sv">{{ shown.speed.toFixed(2) }}×</span></span>
      <input type="range" min="0.7" max="1.5" step="0.05" :value="shown.speed" aria-label="Speed" @change="setSpeed" />
      <span class="sr">0.70× — 1.50×</span>
    </label>
  </div>
</template>

<style scoped>
.gauges { display:grid; gap:16px; }
.charline { display:flex; flex-direction:column; gap:5px; margin-top:20px; font-size:12px; }
.speed-heading { display:flex; justify-content:space-between; gap:8px; }
.sv { color:var(--muted); font:11px var(--mono); }
input { width:100%; height:22px; }
.sr { color:var(--muted); font-size:11px; }
</style>
