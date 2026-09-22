import { mount } from '@vue/test-utils';
import { describe,it,expect } from 'vitest';
import AudioControls from './AudioControls.vue';
import { DEFAULT_AUDIO_CONTROLS, AUDIO_CONTROL_IDS } from './audioControls';
import type { DaemonStatus } from '../types';
describe('AudioControls',()=>{
  it('shows the defaults and opens settings without changing audio',async()=>{
    const w=mount(AudioControls,{props:{status:null,visible:[...DEFAULT_AUDIO_CONTROLS]}});
    expect(w.findAll('.audio-row').map(r=>r.find('label').text())).toEqual(['Microphone','Language','Turn detection']);
    await w.get('[aria-label="Open audio settings"]').trigger('click');
    expect(w.emitted()).toMatchObject({openSettings:[[]]});
    expect(w.emitted('change')).toBeUndefined();
  });
  it('changes binary controls with one click and respects unavailable streaming',async()=>{
    const w=mount(AudioControls,{props:{status:{speech_live_available:false} as DaemonStatus,visible:[...AUDIO_CONTROL_IDS]}});
    const row=w.findAll('.audio-row').find(r=>r.text().includes('Agent speech'))!;
    expect(row.findAll('button')[1].attributes('disabled')).toBeDefined();
    await row.findAll('button')[0].trigger('click');
    expect(w.emitted('change')).toEqual([[{id:'agent',value:'batch'}]]);
  });
  it('hides controls without altering their values and retains the empty-panel shortcut',async()=>{
    const w=mount(AudioControls,{props:{status:null,visible:['microphone'],settings:true}});
    await w.get('input[aria-label="Show Microphone on dashboard"]').setValue(false);
    expect(w.emitted('visibility')).toEqual([[[]]]);
    expect(w.emitted('change')).toBeUndefined();
    await w.setProps({settings:false,visible:[]});
    expect(w.findAll('.audio-row')).toHaveLength(0);
    expect(w.find('[aria-label="Open audio settings"]').exists()).toBe(true);
  });
  it('offers the requested silence range and disables it during push to talk',()=>{
    const w=mount(AudioControls,{props:{status:{detection_mode:'ptt'} as DaemonStatus,visible:['silence']}});
    expect(w.findAll('option').map(o=>o.attributes('value'))).toEqual(['0','500','1000','1500','2000','3000','4000','5000','6000','7000','8000','9000','10000']);
    expect(w.get('select').attributes('disabled')).toBeDefined();
  });
});
