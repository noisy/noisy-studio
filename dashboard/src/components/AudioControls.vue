<script setup lang="ts">
// Every audio control, as one Settings > Audio form. The dashboard no longer
// carries a compact copy, so there is no "show on dashboard" choice either.
import { computed, useId } from 'vue';
import type { DaemonStatus, InputDevice } from '../types';
import { audioControls, type AudioChange } from './audioControls';
const props = withDefaults(defineProps<{status: DaemonStatus | null; devices?: InputDevice[]; cuesEnabled?: boolean}>(), {devices:()=>[],cuesEnabled:true});
const emit = defineEmits<{change:[change:AudioChange]; refreshDevices:[]}>();
const MAX_WIDTH = 680;
const prefix = useId();
const controls = computed(()=>audioControls(props.status,props.devices,props.cuesEnabled));
</script>
<template>
  <div class="audio-controls" :style="{ '--audio-max-width': MAX_WIDTH + 'px' }">
    <h3>Audio controls</h3>
    <div v-for="c in controls" :key="c.id" class="audio-row" :title="c.notice || (c.disabled ? 'Used in Auto mode' : c.help)">
      <div>
        <div class="control-label"><label :id="`${prefix}-${c.id}-label`" :for="c.buttons ? undefined : `${prefix}-${c.id}`">{{c.label}}</label></div>
        <p :id="`${prefix}-${c.id}-help`" class="help" :class="{notice:!!c.notice}">{{c.notice || c.help}}</p>
      </div>
      <div v-if="c.buttons" class="choices" role="group" :aria-labelledby="`${prefix}-${c.id}-label`">
        <button v-for="o in c.options" :key="o.value" type="button" :disabled="o.disabled || c.disabled" :aria-pressed="c.value === o.value" @click="emit('change',{id:c.id,value:o.value})">{{o.label}}</button>
      </div>
      <select v-else :id="`${prefix}-${c.id}`" :value="c.value" :disabled="c.disabled" :aria-describedby="`${prefix}-${c.id}-help`" @focus="c.id === 'microphone' && emit('refreshDevices')" @change="emit('change',{id:c.id,value:($event.target as HTMLSelectElement).value})">
        <option v-for="o in c.options" :key="o.value" :value="o.value">{{o.label}}</option>
      </select>
    </div>
  </div>
</template>
<style scoped>
.audio-controls{font-size:13px;color:var(--ink);width:100%;max-width:var(--audio-max-width);min-width:0;box-sizing:border-box;container-type:inline-size}
h3{font-size:15px;margin:0 0 8px}
button,select{font:inherit;color:inherit;background:var(--panel-solid);border:1px solid var(--line);border-radius:3px;padding:4px 5px;min-height:28px;min-width:0}
button{cursor:pointer}select{width:100%;text-overflow:ellipsis}
button:focus-visible,select:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
.audio-row{display:grid;grid-template-columns:minmax(120px,1fr) 180px;gap:12px;align-items:center;padding:14px 0;border-top:1px solid var(--line)}
.choices{display:flex;gap:4px;font-size:11px}.choices button{flex:1;white-space:nowrap}
.choices button[aria-pressed=true]{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 12%,transparent)}
:disabled{opacity:.5;cursor:default}
p{color:var(--muted);line-height:1.5}
.control-label{display:flex;align-items:center;gap:3px}
.help{font-size:12px;margin:5px 0 0}.notice{color:#f4c542}
@container(max-width:460px){.audio-row{grid-template-columns:minmax(0,1fr) 150px}}
@container(max-width:300px){.audio-row{grid-template-columns:minmax(0,1fr)}}
</style>
