<script setup lang="ts">
import VoiceAvatar from '../../components/VoiceAvatar.vue';
import type { CompanyPerson } from './cast';
withDefaults(defineProps<{ person: CompanyPerson; size?: number; speaking?: boolean; specialist?: boolean }>(), { size: 120, speaking: false, specialist: false });
</script>
<template>
  <div class="portrait" :class="{ speaking, idle: !person.working && !speaking, specialist }">
    <span class="frame"><VoiceAvatar :voice="person.voice" :size="size" set="editorial"/><span v-if="speaking" class="wave" aria-label="Speaking"><i/><i/><i/><i/></span><span v-else class="activity-marker" aria-hidden="true">{{ person.working ? '●' : '○' }}</span></span>
    <strong>{{ person.name }}</strong><span class="role">{{ person.role }}</span><span class="status">{{ speaking ? 'Speaking' : person.working ? 'Working' : 'Idle' }}</span>
  </div>
</template>
<style scoped>
.portrait{display:flex;flex-direction:column;align-items:center;text-align:center;position:relative;min-width:0;color:#ece9df}.frame{display:inline-flex;position:relative;border:1px solid #c4d5c53b;border-radius:40%;padding:8px;background:#dce9d708;box-shadow:0 14px 30px #0003}.frame :deep(.voice-avatar){border-radius:35%}.portrait strong{font-size:17px;font-weight:550;margin-top:15px;line-height:1.3}.role{font-size:11px;color:#a5b7ac;line-height:1.4;margin-top:4px}.status{font-size:10px;letter-spacing:.5px;color:#c6dcad;margin-top:7px}.idle .frame :deep(.voice-avatar){filter:grayscale(.95) saturate(.15);opacity:.65}.idle .status{color:#a0aaa3}.idle .frame{border-color:#aebdb022;box-shadow:none}.specialist .frame{padding:5px;border-radius:39%}.specialist strong{font-size:12px;margin-top:10px}.specialist .role{font-size:9px}.specialist .status{font-size:9px;margin-top:5px}.activity-marker{position:absolute;bottom:-6px;right:2px;font-size:12px;line-height:15px;color:#c9e6ae;background:#172b26;border:3px solid #172b26;border-radius:50%}.idle .activity-marker{color:#9aa69d}.speaking .frame{border-color:#d3eab8;box-shadow:0 0 0 5px #deedc50b,0 0 55px #cde8b926}.wave{position:absolute;bottom:-8px;left:50%;transform:translateX(-50%);display:flex;align-items:center;justify-content:center;gap:3px;width:34px;height:20px;background:#d3eab8;color:#172522;border:3px solid #122422;border-radius:20px}.wave i{height:8px;width:2px;background:currentColor;animation:voice .9s infinite alternate}.wave i:nth-child(2){height:12px;animation-delay:.3s}.wave i:nth-child(3){height:5px;animation-delay:.5s}@keyframes voice{to{transform:scaleY(.4)}}@media(prefers-reduced-motion:reduce){.wave i{animation:none}}
</style>
