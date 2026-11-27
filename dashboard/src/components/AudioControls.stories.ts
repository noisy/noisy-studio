import { ref } from 'vue';
import type { Meta, StoryObj } from '@storybook/vue3';
import AudioControls from './AudioControls.vue';
import type { AudioChange } from './audioControls';
import type { DaemonStatus } from '../types';
export default {title:'Dashboard/AudioControls',component:AudioControls} satisfies Meta<typeof AudioControls>;

// Settings > Audio: every control, wired to a local status so clicks show.
function interactive(width: number): StoryObj {
  return {render:() => ({components:{AudioControls},setup(){
    const cues=ref(true);
    const status=ref({input_device:'',language:'en',detection_mode:'auto',tts_mode:'live',mode:'live',end_silence_ms:2000,mic_sensitivity:50,smart_turn:0} as DaemonStatus);
    function change({id,value}:AudioChange){
      if(id==='cues'){cues.value=value==='on';return;}
      const keys={microphone:'input_device',language:'language',turn:'detection_mode',agent:'tts_mode',recognition:'mode',length:'max_utterance_ms',silence:'end_silence_ms',sensitivity:'mic_sensitivity',smart:'smart_turn'};
      status.value={...status.value,[keys[id]]:['length','silence','sensitivity','smart'].includes(id)?Number(value):value};
    }
    return {cues,status,change,width:width+'px'};
  },template:`<div :style="{width,maxWidth:'100%'}"><AudioControls :status="status" :cues-enabled="cues" @change="change" /></div>`})};
}
export const Wide=interactive(1100);
export const Narrow=interactive(360);

export const PushToTalkSilence: StoryObj<typeof AudioControls> = {
  args: {status:{detection_mode:'ptt',end_silence_ms:2000} as DaemonStatus},
};
