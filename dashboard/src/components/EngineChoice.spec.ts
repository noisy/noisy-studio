import { mount, flushPromises } from '@vue/test-utils';
import { afterEach, expect, it, vi } from 'vitest';
import EngineChoice from './EngineChoice.vue';
const api = vi.hoisted(() => ({getProviders:vi.fn(),setProviders:vi.fn()}));
vi.mock('../api/client',()=>api);
afterEach(()=>{vi.useRealTimers();vi.clearAllMocks();});

it('shows preparation progress after a rejected apply and lets the user apply once ready',async()=>{
  vi.useFakeTimers();
  const info={catalog:[{name:'local',ready:true}],active:{stt:'grok',tts:'grok'},downloads:[] as object[]};
  api.getProviders.mockImplementation(async()=>({...info,downloads:[...info.downloads]}));
  api.setProviders.mockRejectedValueOnce(new Error('{"error":"Preparing local models"}'));
  const wrapper=mount(EngineChoice);await flushPromises();
  info.downloads=[{name:'whisper-base',label:'Whisper base',state:'downloading',done_bytes:0,total_bytes:0,detail:''}];

  await wrapper.findAll('button').find(b=>b.text().includes('Local · Offline'))!.trigger('click');
  await flushPromises();
  expect(wrapper.text()).toContain('DOWNLOADING');
  expect(wrapper.findAll('button').find(b=>b.text()==='Preparing local engines…')!.attributes('disabled')).toBeDefined();

  info.downloads=[{name:'whisper-base',label:'Whisper base',state:'done',done_bytes:0,total_bytes:0,detail:''}];
  await vi.advanceTimersByTimeAsync(1000);await flushPromises();
  api.setProviders.mockImplementationOnce(async()=>{info.active={stt:'local',tts:'local'};});
  await wrapper.findAll('button').find(b=>b.text()==='Use local engines')!.trigger('click');await flushPromises();
  expect(api.setProviders).toHaveBeenLastCalledWith({stt:'local',tts:'local'});
  expect(wrapper.text()).toContain('Local voice is set up');
  wrapper.unmount();
  const calls=api.getProviders.mock.calls.length;
  await vi.advanceTimersByTimeAsync(1000);
  expect(api.getProviders).toHaveBeenCalledTimes(calls);
});
