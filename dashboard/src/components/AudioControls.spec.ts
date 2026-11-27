import { mount } from '@vue/test-utils';
import { describe,it,expect } from 'vitest';
import AudioControls from './AudioControls.vue';
import { AUDIO_CONTROL_IDS } from './audioControls';
import type { DaemonStatus } from '../types';
describe('AudioControls',()=>{
  it('lists every audio control, with no dashboard visibility switches',()=>{
    const w=mount(AudioControls,{props:{status:null}});
    expect(w.findAll('.audio-row')).toHaveLength(AUDIO_CONTROL_IDS.length);
    expect(w.find('input[role="switch"]').exists()).toBe(false);
  });
  it('defaults message length to ten minutes and allows changing it in push-to-talk',async()=>{
    const w=mount(AudioControls,{props:{status:{detection_mode:'ptt'} as DaemonStatus}});
    const row=w.findAll('.audio-row').find(r=>r.text().includes('Maximum voice message length'))!;
    expect((row.get('select').element as HTMLSelectElement).value).toBe('600000');
    await row.get('select').setValue('900000');
    expect(w.emitted('change')).toEqual([[{id:'length',value:'900000'}]]);
  });
  it('changes binary controls with one click and respects unavailable streaming',async()=>{
    const w=mount(AudioControls,{props:{status:{speech_live_available:false} as DaemonStatus}});
    const row=w.findAll('.audio-row').find(r=>r.text().includes('Agent speech'))!;
    expect(row.findAll('button')[1].attributes('disabled')).toBeDefined();
    await row.findAll('button')[0].trigger('click');
    expect(w.emitted('change')).toEqual([[{id:'agent',value:'batch'}]]);
  });
  it('keeps end silence editable during push to talk and says when it applies',async()=>{
    const w=mount(AudioControls,{props:{status:{detection_mode:'ptt'} as DaemonStatus}});
    const row=()=>w.findAll('.audio-row').find(r=>r.text().includes('End silence'))!;
    expect(row().findAll('option').map(o=>o.attributes('value'))).toEqual(['0','500','1000','1500','2000','3000','4000','5000','6000','7000','8000','9000','10000']);
    expect(row().get('select').attributes('disabled')).toBeUndefined();
    expect(w.text()).toContain('Applies only when Turn detection is Auto.');
    await row().get('select').setValue('10000');
    expect(w.emitted('change')).toEqual([[{id:'silence',value:'10000'}]]);
    await w.setProps({status:{detection_mode:'auto',end_silence_ms:10000} as DaemonStatus});
    expect(w.text()).not.toContain('Applies only when Turn detection is Auto.');
    expect((row().get('select').element as HTMLSelectElement).value).toBe('10000');
  });
});
