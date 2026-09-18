import { mount, flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SpeechSettings from './SpeechSettings.vue';
import { speechFixture } from './speechSettings.fixture';
const api = vi.hoisted(() => ({getSpeechSettings:vi.fn(),updateSpeechSettings:vi.fn(),previewSpeechVoice:vi.fn(),getStatus:vi.fn().mockResolvedValue({muted:true}),setMuted:vi.fn()}));
vi.mock('../api/client',()=>api);
beforeEach(()=>{vi.clearAllMocks();api.getSpeechSettings.mockResolvedValue(speechFixture());});
async function openVoices() {const wrapper=mount(SpeechSettings);await flushPromises();await wrapper.findAll('button').filter(b=>b.text()==='Change')[1]!.trigger('click');await wrapper.findAll('button').find(b=>b.text().includes('Kokoro'))!.trigger('click');return wrapper;}
describe('speech selection',()=>{
  it('cancel leaves active choices untouched',async()=>{const wrapper=await openVoices();await wrapper.findAll('button').find(b=>b.text()==='Cancel')!.trigger('click');expect(api.updateSpeechSettings).not.toHaveBeenCalled();wrapper.unmount();});
  it('applies the reviewed voice assignments explicitly',async()=>{api.updateSpeechSettings.mockResolvedValue(speechFixture());const wrapper=await openVoices();await wrapper.get('#speech-voice-lux').setValue('bf_emma');await wrapper.findAll('button').find(b=>b.text()==='Use for agent voices')!.trigger('click');expect(api.updateSpeechSettings).toHaveBeenCalledWith({operation:'apply',choice:'kokoro:1',revision:'fixture1',bindings:{lux:'bf_emma',rex:'am_adam',luna:'bf_emma'}});wrapper.unmount();});
  it('failed apply keeps the draft available for correction',async()=>{api.updateSpeechSettings.mockRejectedValue(new Error('Download first'));const wrapper=await openVoices();await wrapper.findAll('button').find(b=>b.text()==='Use for agent voices')!.trigger('click');await flushPromises();expect(wrapper.get('[role="alert"]').text()).toContain('Download first');expect(wrapper.find('#speech-voice-lux').exists()).toBe(true);wrapper.unmount();});
  it('routes credential setup to System settings',async()=>{
    const fixture=speechFixture();
    fixture.engines.find(e=>e.id==='grok:tts')!.state='setup';
    api.getSpeechSettings.mockResolvedValue(fixture);
    const wrapper=mount(SpeechSettings);await flushPromises();
    await wrapper.findAll('button').filter(b=>b.text()==='Change')[1]!.trigger('click');
    await wrapper.findAll('button').find(b=>b.text()==='Open System settings')!.trigger('click');
    expect(wrapper.emitted('configure')).toEqual([[]]);wrapper.unmount();
  });
  it('explains missing runtime support without sending users to credential settings',async()=>{
    api.getSpeechSettings.mockResolvedValue(speechFixture('setup'));
    const wrapper=await openVoices();
    expect(wrapper.text()).toContain('Use a desktop build with offline support');
    expect(wrapper.text()).not.toContain('Open System settings');
    expect(wrapper.findAll('button').find(b=>b.text()==='Use for agent voices')!.attributes('disabled')).toBeDefined();
    wrapper.unmount();
  });
});
