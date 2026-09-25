<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import { AVATAR_SETS, avatarImageStyle, avatarFrameStyle, avatarCell, type AvatarSetId } from '../avatars/catalog';
import { useAvatarSet } from '../composables/useAvatarSet';

const props = withDefaults(defineProps<{ voice: string; size?: number; set?: AvatarSetId }>(), { size: 48 });
const { avatarSet } = useAvatarSet();
const failedImage = ref('');
const cell = computed(() => avatarCell(props.voice));
const artwork = computed(() => AVATAR_SETS.find(set => set.id === (props.set ?? avatarSet.value)) ?? AVATAR_SETS[0]);
const showArtwork = computed(() => cell.value !== null && failedImage.value !== artwork.value.image);
watchEffect(() => {
  if (import.meta.env.DEV && cell.value === null) {
    console.warn(`[VoiceAvatar] No artwork for voice "${props.voice}"; showing a monogram. Add it to the avatar catalog.`);
  }
});
function imageFailed() {
  failedImage.value = artwork.value.image;
  if (import.meta.env.DEV) console.warn(`[VoiceAvatar] Could not load ${artwork.value.id}; showing a monogram.`);
}
const imageStyle = computed(() => avatarImageStyle(artwork.value.id, cell.value ?? 0));
const palettes = [
  { background: "#2c394b", color: "#c4d8f7" },
  { background: "#3a3248", color: "#ded0f3" },
  { background: "#2c3c35", color: "#bedfca" },
  { background: "#423728", color: "#ecd3aa" },
  { background: "#423136", color: "#edc6ce" },
  { background: "#2b3c40", color: "#bddde3" },
];
const palette = computed(() => {
  const hash = [...props.voice.toLowerCase()].reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0);
  return palettes[(hash >>> 0) % palettes.length];
});
const monogram = computed(() => props.voice.trim().slice(0, 3).toUpperCase() || "—");
</script>

<template>
  <span class="voice-avatar" aria-hidden="true" :style="{
    ...palette, width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.27)}px`,
  }">
    <span v-if="showArtwork" class="avatar-crop" :style="avatarFrameStyle(artwork.id, cell ?? 0)">
    <img :src="artwork.image" :style="imageStyle" alt="" draggable="false" @error="imageFailed" />
    </span>
    <template v-else>{{ monogram }}</template>
  </span>
</template>

<style scoped>
.voice-avatar { position:relative; overflow:hidden; display: inline-flex; align-items: center; justify-content: center; flex: none; border-radius: 24%; font-family: var(--sans); font-weight: 650; line-height: 1; user-select: none; }
.avatar-crop { position:absolute; overflow:hidden; }
.voice-avatar img { position:absolute; max-width:none; object-fit:fill; pointer-events:none; }
</style>
