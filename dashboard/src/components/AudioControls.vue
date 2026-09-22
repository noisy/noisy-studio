<script setup lang="ts">
import { computed, useId } from 'vue';
import type { DaemonStatus, InputDevice } from '../types';
import { audioControls, DEFAULT_AUDIO_CONTROLS, type AudioControlId, type AudioChange } from './audioControls';
const props = withDefaults(defineProps<{status: DaemonStatus | null; devices?: InputDevice[]; cuesEnabled?: boolean; visible: AudioControlId[]; settings?: boolean}>(), {devices:()=>[],cuesEnabled:true,settings:false});
const emit = defineEmits<{change:[change:AudioChange]; visibility:[ids:AudioControlId[]]; refreshDevices:[]; openSettings:[]}>();
const prefix = useId();
const controls = computed(()=>audioControls(props.status,props.devices,props.cuesEnabled).filter(c=>props.settings || props.visible.includes(c.id)));
function toggle(id: AudioControlId, checked: boolean) { emit('visibility', checked ? [...props.visible,id] : props.visible.filter(v=>v!==id)); }
</script>
<template>
  <div class="audio-controls" :class="{settings}">
    <header v-if="!settings"><span>Audio controls</span><button type="button" aria-label="Open audio settings" @click="emit('openSettings')">Settings ↗</button></header>
    <template v-else><h3>Audio controls</h3><p>All controls are available here. Choose which also appear on your dashboard.</p><div class="visibility-heading">Show on dashboard</div></template>
    <div v-for="c in controls" :key="c.id" class="audio-row" :title="c.disabled ? 'Used in Auto mode' : c.help">
      <div><label :id="`${prefix}-${c.id}-label`" :for="c.buttons ? undefined : `${prefix}-${c.id}`">{{c.label}}</label><p v-if="settings" class="help">{{c.help}}</p></div>
      <div v-if="c.buttons" class="choices" role="group" :aria-labelledby="`${prefix}-${c.id}-label`"><button v-for="o in c.options" :key="o.value" type="button" :disabled="o.disabled || c.disabled" :aria-pressed="c.value === o.value" @click="emit('change',{id:c.id,value:o.value})">{{o.label}}</button></div>
      <select v-else :id="`${prefix}-${c.id}`" :value="c.value" :disabled="c.disabled" @focus="c.id === 'microphone' && emit('refreshDevices')" @change="emit('change',{id:c.id,value:($event.target as HTMLSelectElement).value})"><option v-for="o in c.options" :key="o.value" :value="o.value">{{o.label}}</option></select>
      <label v-if="settings" class="visibility"><input type="checkbox" :checked="visible.includes(c.id)" :aria-label="`Show ${c.label} on dashboard`" @change="toggle(c.id,($event.target as HTMLInputElement).checked)">Show</label>
    </div>
    <p v-if="!settings && !controls.length">Choose controls to show in Settings.</p>
    <button v-if="settings" type="button" @click="emit('visibility',[...DEFAULT_AUDIO_CONTROLS])">Restore default visibility</button>
  </div>
</template>
<style scoped>
.audio-controls{font-size:11px;color:var(--ink)}header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px}header span{font-size:13px;font-weight:600}button,select{font:inherit;color:inherit;background:var(--panel-solid);border:1px solid var(--line);border-radius:3px;padding:4px 5px;min-height:28px;min-width:0}button{cursor:pointer}select{width:100%;text-overflow:ellipsis}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}.audio-row{display:grid;grid-template-columns:80px minmax(0,1fr);gap:6px;align-items:center;margin:6px 0}.choices{display:flex;gap:4px}.choices button{flex:1;white-space:nowrap}.choices button[aria-pressed=true]{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 12%,transparent)}:disabled{opacity:.5;cursor:default}p{color:var(--muted);line-height:1.5}.settings{font-size:13px}.settings .audio-row{grid-template-columns:minmax(120px,1fr) 160px 110px;gap:12px;padding:14px 0;border-top:1px solid var(--line);margin:0}.help{font-size:12px;margin:5px 0 0}.visibility{display:flex;align-items:center;gap:6px;font-size:12px}.visibility-heading{text-align:right;font-size:12px;margin:12px 0 4px}h3{font-size:15px;margin:0}.settings .choices{font-size:11px}@media(max-width:650px){.settings .audio-row{grid-template-columns:minmax(100px,1fr) 150px}.visibility{grid-column:1/-1}.visibility-heading{display:none}}
</style>
