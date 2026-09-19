<script setup lang="ts">
import VoiceSelector from "./VoiceSelector.vue";
import VoiceAvatar from "./VoiceAvatar.vue";

// Voice identity, quick mute, and the voice picker for the viewed session.
const props = defineProps<{
  voice: string;
  voiceLabels?: Record<string, string>;
  speaking?: boolean;
  muted?: boolean;
}>();

defineEmits<{ change: [voice: string]; "toggle-mute": [] }>();

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
      <button
        class="mutebtn" :aria-pressed="!!muted"
        :class="{ on: muted }"
        :title="muted ? 'Unmute this conversation' : 'Mute this conversation'"
        @click.stop="$emit('toggle-mute')"
      >{{ muted ? "Unmute" : "Mute" }}</button>
    </div>
    <VoiceSelector :voice="voice" :voice-labels="voiceLabels" @change="(v) => $emit('change', v)" />
  </div>
</template>

<style scoped>

.persona { display:flex; flex-direction:column; gap:14px; }
.frame { position:relative; display:flex; align-items:center; gap:8px; }
.portrait { display:flex; flex:none; border:0; background:none; border-radius:18px; }
.mutebtn { margin-left:auto; min-width:76px; min-height:48px; padding:10px 12px; font:14px var(--sans); background:var(--bg1); border:1px solid var(--line); color:var(--ink); }
.mutebtn:hover { border-color:var(--line-strong); }
.mutebtn.on { color:var(--red); border-color:var(--red); }
.muted .portrait { filter:grayscale(.7); }
.onair { position:absolute; left:0; bottom:-5px; font:10px var(--sans); padding:2px 5px; background:var(--panel-solid); color:var(--green); border:1px solid var(--line); border-radius:4px; }

</style>
