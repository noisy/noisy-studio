import { ref } from 'vue';
import type { Meta, StoryObj } from '@storybook/vue3';
import AudioControls from './AudioControls.vue';
import { AUDIO_CONTROL_IDS, DEFAULT_AUDIO_CONTROLS, type AudioControlId, type AudioChange } from './audioControls';
import type { DaemonStatus } from '../types';
export default {title:'Dashboard/AudioControls',component:AudioControls} satisfies Meta<typeof AudioControls>;
function preview(all = false) {
  return () => ({components:{AudioControls},setup(){
    const visible=ref<AudioControlId[]>(all ? [...AUDIO_CONTROL_IDS] : [...DEFAULT_AUDIO_CONTROLS]);
    const settings=ref(false);
    const cues=ref(true);
    const status=ref({input_device:'',language:'en',detection_mode:'auto',tts_mode:'live',mode:'live',end_silence_ms:2000,mic_sensitivity:50,smart_turn:0} as DaemonStatus);
    function change({id,value}:AudioChange){
      if(id==='cues'){cues.value=value==='on';return;}
      const keys={microphone:'input_device',language:'language',turn:'detection_mode',agent:'tts_mode',recognition:'mode',silence:'end_silence_ms',sensitivity:'mic_sensitivity',smart:'smart_turn'};
      status.value={...status.value,[keys[id]]:['silence','sensitivity','smart'].includes(id)?Number(value):value};
    }
    return {visible,settings,cues,status,change};
  },template:`<div style="display:flex;gap:24px;align-items:start;flex-wrap:wrap"><div style="width:268px;padding:12px;border:1px solid var(--line);box-sizing:border-box"><AudioControls :status="status" :visible="visible" :cues-enabled="cues" @change="change" @open-settings="settings=true" /></div><div v-if="settings" style="width:680px;padding:16px;border:1px solid var(--line)"><AudioControls settings :status="status" :visible="visible" :cues-enabled="cues" @change="change" @visibility="visible=$event" /></div></div>`});
}
export const Defaults:StoryObj={render:preview()};
export const AllControls:StoryObj={render:preview(true)};

export const WideSettings: StoryObj<typeof AudioControls> = {
  args: {status:null,visible:[...DEFAULT_AUDIO_CONTROLS],settings:true},
  render: args => ({components:{AudioControls},setup:()=>({args}),template:'<div style="width:1100px;max-width:100%"><AudioControls v-bind="args" /></div>'}),
};
export const NarrowSettings: StoryObj<typeof AudioControls> = {
  args: {status:null,visible:[...DEFAULT_AUDIO_CONTROLS],settings:true},
  render: args => ({components:{AudioControls},setup:()=>({args}),template:'<div style="width:360px;max-width:100%"><AudioControls v-bind="args" /></div>'}),
};

export const PushToTalkSilence: StoryObj<typeof AudioControls> = {
  args: {status:{detection_mode:'ptt',end_silence_ms:2000} as DaemonStatus,visible:['silence'],settings:true},
};

export const PushToTalkSilenceDashboard: StoryObj<typeof AudioControls> = {
  args: {status:{detection_mode:'ptt',end_silence_ms:2000} as DaemonStatus,visible:['silence']},
  render: args => ({components:{AudioControls},setup:()=>({args}),template:'<div style="width:244px"><AudioControls v-bind="args" /></div>'}),
};
