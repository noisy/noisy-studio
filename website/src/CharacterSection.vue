<script setup lang="ts">
import { ref } from "vue";
import CharacterReadout from "@dashboard/components/CharacterReadout.vue";
import VoiceAvatar from "@dashboard/components/VoiceAvatar.vue";
import type { Character } from "@dashboard/types";
const presets = [
  {
    name: "The colleague",
    line: "Straight answers. A joke when it earns one.",
    character: {
      humor: 75,
      honesty: 80,
      verbosity: 40,
      talkative: 40,
      voice: "lux",
      speed: 1.05,
    },
  },
  {
    name: "The deadpan butler",
    line: "Precise. Dry. Faintly unimpressed.",
    character: {
      humor: 20,
      honesty: 100,
      verbosity: 20,
      talkative: 10,
      voice: "atlas",
      speed: 0.9,
    },
  },
  {
    name: "The hype gremlin",
    line: "Every green test is a personal victory.",
    character: {
      humor: 90,
      honesty: 60,
      verbosity: 80,
      talkative: 90,
      voice: "cosmo",
      speed: 1.35,
    },
  },
  {
    name: "Mission control",
    line: "Facts first. Ready for the next step.",
    character: {
      humor: 0,
      honesty: 100,
      verbosity: 0,
      talkative: 0,
      voice: "orion",
      speed: 1,
    },
  },
];
const selected = ref<number | null>(0);
const character = ref<Character>({ ...presets[0].character });
function pick(index: number) {
  selected.value = index;
  character.value = { ...presets[index].character };
}
function update(patch: Partial<Character>) {
  selected.value = null;
  character.value = { ...character.value, ...patch };
}
</script>
<template>
  <section id="character" class="section character-section">
    <div class="wrap character-layout">
      <div>
        <p class="eyebrow">A little personality goes a long way</p>
        <h2>Same task.<br /><em>Different character.</em></h2>
        <p class="section-intro">
          A dry reviewer. An enthusiastic test runner. Choose a starting point,
          then adjust how your agent communicates.
        </p>
        <div class="preset-list" role="group" aria-label="Character presets">
          <button
            v-for="(preset, index) in presets"
            :key="preset.name"
            type="button"
            :aria-pressed="selected === index"
            @click="pick(index)"
          >
            <span>{{ preset.name }}</span
            ><small>{{ preset.line }}</small
            ><span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
      <div class="character-demo">
        <div class="character-person">
          <VoiceAvatar :voice="character.voice" :size="88" set="editorial" />
          <div>
            <span>{{
              selected === null ? "Your own character" : presets[selected].name
            }}</span
            ><small>{{ character.voice }} · Voice</small>
          </div>
        </div>
        <CharacterReadout :character="character" @change="update" />
        <p class="demo-note">Try the controls. This demo stays on this page.</p>
      </div>
    </div>
  </section>
</template>
<style scoped>
.character-section {
  background: #202125;
  border-block: 1px solid #35353d;
}
.character-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--layout-gap);
  align-items: center;
}
.preset-list {
  max-width: 600px;
  display: grid;
  gap: 8px;
  margin-top: 30px;
}
.preset-list button {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 3px 12px;
  text-align: left;
  padding: 16px 18px;
  background: transparent;
  color: var(--ink);
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
}
.preset-list button > span:first-child {
  font-weight: 550;
  font-size: 15px;
}
.preset-list small {
  grid-column: 1;
  grid-row: 2;
  color: var(--muted);
  font-size: 12px;
}
.preset-list button > span:last-child {
  grid-column: 2;
  grid-row: 1/3;
  align-self: center;
  color: var(--amber);
}
.preset-list button[aria-pressed="true"] {
  background: #323037;
  border-color: #645b6c;
}
.preset-list button:hover {
  background: #2b2b32;
}
.character-demo {
  width: 100%;
  max-width: 360px;
  justify-self: center;
  padding: 20px;
  background: #26282d;
  border: 1px solid #50505a;
  border-radius: 18px;
  box-shadow: 0 30px 60px #0002;
}
.character-person {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 25px;
  margin-bottom: 25px;
  border-bottom: 1px solid var(--line-strong);
}
.character-person span {
  font-size: 18px;
  letter-spacing: -0.4px;
}
.character-person small {
  display: block;
  text-transform: capitalize;
  color: var(--muted);
  margin-top: 5px;
  font-size: 12px;
}
.demo-note {
  margin-top: 22px;
  font-size: 11px;
  text-align: center;
}
@media (max-width: 900px) {
  .character-layout {
    gap: 35px;
  }
  .character-demo {
    padding: 22px;
  }
}
@media (max-width: 600px) {
  .character-layout {
    grid-template-columns: 1fr;
    gap: 30px;
  }
  .character-person span {
    font-size: 17px;
  }
}
</style>
