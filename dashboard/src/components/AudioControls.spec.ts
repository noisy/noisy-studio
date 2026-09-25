import { mount } from '@vue/test-utils';
import { describe,it,expect } from 'vitest';
import AudioControls from './AudioControls.vue';
import { DEFAULT_AUDIO_CONTROLS, AUDIO_CONTROL_IDS } from './audioControls';
import type { DaemonStatus } from '../types';
describe('AudioControls',()=>{
  it('defaults message length to ten minutes and allows changing it in push-to-talk',async()=>{
    const w=mount(AudioControls,{props:{status:{detection_mode:'ptt'} as DaemonStatus,visible:[],settings:true}});
    const row=w.findAll('.audio-row').find(r=>r.text().includes('Maximum voice message length'))!;
    expect((row.get('select').element as HTMLSelectElement).value).toBe('600000');
    await row.get('select').setValue('900000');
    expect(w.emitted('change')).toEqual([[{id:'length',value:'900000'}]]);
  });
  it('shows the defaults and opens settings without changing audio',async()=>{
    const w=mount(AudioControls,{props:{status:null,visible:[...DEFAULT_AUDIO_CONTROLS]}});
    expect(w.findAll('.audio-row').map(r=>r.find('label').text())).toEqual(['Microphone','Language','Turn detection']);
    await w.get('[aria-label="Open all audio controls"]').trigger('click');
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
    expect(w.find('[aria-label="Open all audio controls"]').exists()).toBe(true);
  });
  it.each([false,true])('keeps end silence editable during push to talk (settings=%s)',async(settings)=>{
    const w=mount(AudioControls,{props:{status:{detection_mode:'ptt'} as DaemonStatus,visible:['silence'],settings}});
    expect(w.findAll('.audio-row').find(r=>r.text().includes('End silence'))!.findAll('option').map(o=>o.attributes('value'))).toEqual(['0','500','1000','1500','2000','3000','4000','5000','6000','7000','8000','9000','10000']);
    const select = w.findAll('.audio-row').find(r=>r.text().includes('End silence'))!.get('select');
    expect(select.attributes('disabled')).toBeUndefined();
    expect(w.text()).toContain('Applies only when Turn detection is Auto.');
    if (!settings) {
      expect(w.get('.control-label .notice-icon button').attributes('aria-label')).toContain('End silence:');
      expect(w.find('.dashboard-notice').exists()).toBe(false);
    }
    await select.setValue('10000');
    expect(w.emitted('change')).toEqual([[{id:'silence',value:'10000'}]]);
    await w.setProps({status:{detection_mode:'auto',end_silence_ms:10000} as DaemonStatus});
    expect(w.text()).not.toContain('Applies only when Turn detection is Auto.');
    expect((select.element as HTMLSelectElement).value).toBe('10000');
  });
});
