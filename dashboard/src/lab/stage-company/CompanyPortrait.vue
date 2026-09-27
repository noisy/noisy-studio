<script setup lang="ts">
import VoiceAvatar from '../../components/VoiceAvatar.vue';
import type { CompanyPerson } from './cast';
withDefaults(defineProps<{ person: CompanyPerson; size?: number; speaking?: boolean }>(), { size: 76, speaking: false });
</script>
<template>
  <div class="portrait" :class="{ speaking }">
    <span class="frame"><VoiceAvatar :voice="person.voice" :size="size" set="editorial"/><span v-if="speaking" class="wave" aria-label="Speaking"><i/><i/><i/><i/></span></span>
    <strong>{{ person.name }}</strong><span class="role">{{ person.role }}</span>
  </div>
</template>
<style scoped>
.portrait{display:flex;flex-direction:column;align-items:center;text-align:center;position:relative;min-width:0;color:#ece9df}.frame{display:inline-flex;position:relative;border:1px solid #c4d5c526;border-radius:40%;padding:6px;background:#dce9d708;box-shadow:0 14px 30px #0003}.frame :deep(.voice-avatar){border-radius:35%}.portrait strong{font-size:13px;font-weight:550;margin-top:12px;line-height:1.3}.role{font-size:10px;color:#9aacaa;line-height:1.4;margin-top:4px}.speaking .frame{border-color:var(--accent,#d3eab8);box-shadow:0 0 0 5px #deedc50b,0 0 45px #cde8b921}.wave{position:absolute;bottom:-8px;left:50%;transform:translateX(-50%);display:flex;align-items:center;justify-content:center;gap:3px;width:32px;height:19px;background:var(--accent,#d3eab8);color:#172522;border:3px solid #122422;border-radius:20px}.wave i{height:8px;width:2px;background:currentColor;animation:voice .9s infinite alternate}.wave i:nth-child(2){height:12px;animation-delay:.3s}.wave i:nth-child(3){height:5px;animation-delay:.5s}@keyframes voice{to{transform:scaleY(.4)}}@media(prefers-reduced-motion:reduce){.wave i{animation:none}}
</style>
