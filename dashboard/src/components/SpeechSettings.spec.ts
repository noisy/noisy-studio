import { mount, flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SpeechSettings from './SpeechSettings.vue';
const sampleStart = vi.hoisted(() => vi.fn());
vi.mock('../composables/useSpeechSample', async () => {
  const { ref } = await import('vue');
  return { useSpeechSample: () => ({start:sampleStart, cancel:vi.fn(), finish:vi.fn(), recording:ref(false), error:ref('')}) };
});
import { speechFixture } from './speechSettings.fixture';
const api = vi.hoisted(() => ({getSpeechSettings:vi.fn(),restoreSpeechSettings:vi.fn(),updateSpeechSettings:vi.fn(),previewSpeechVoice:vi.fn(),getStatus:vi.fn().mockResolvedValue({muted:true}),setMuted:vi.fn()}));
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
  it.each(['cancel', 'unmount'])('does not start a microphone sample after %s during its status check',async(action)=>{
    let resolveStatus!: (value:{muted:boolean})=>void;
    const wrapper=mount(SpeechSettings);await flushPromises();
    api.getStatus.mockReturnValueOnce(new Promise(resolve=>{resolveStatus=resolve;}));
    await wrapper.findAll('button').filter(b=>b.text()==='Change')[0]!.trigger('click');
    await wrapper.findAll('button').find(b=>b.text()==='Try my microphone')!.trigger('click');
    if(action==='cancel') await wrapper.findAll('button').find(b=>b.text()==='Cancel')!.trigger('click');
    else wrapper.unmount();
    resolveStatus({muted:true});await flushPromises();
    expect(sampleStart).not.toHaveBeenCalled();
    if(action==='cancel')wrapper.unmount();
  });
  it('shows actual current voices instead of proposed assignments',async()=>{
    const fixture=speechFixture();fixture.current_voice_labels={lux:'Emma · UK'};
    api.getSpeechSettings.mockResolvedValue(fixture);
    const wrapper=await openVoices();
    expect(wrapper.get('label[for="speech-voice-lux"]').text()).toContain('Emma · UK →');
    wrapper.unmount();
  });

  it('describes the active batch mode even when the provider supports streaming',async()=>{
    api.getStatus.mockResolvedValueOnce({muted:true,recognition_mode:'batch',speech_output_mode:'batch'});
    const wrapper=mount(SpeechSettings);await flushPromises();
    expect(wrapper.text()).toContain('Text appears after you finish speaking.');
    expect(wrapper.text()).toContain('The full reply is generated before playback.');
    expect(wrapper.text()).not.toContain('Text appears while you speak.');
    wrapper.unmount();
  });

  it('restores a valid backup only after an explicit recovery action',async()=>{
    api.getSpeechSettings.mockRejectedValueOnce(Object.assign(new Error('Saved settings are invalid.'),{recovery:{revision:'damaged1',can_restore:true}}));
    api.restoreSpeechSettings.mockResolvedValue(speechFixture());
    const wrapper=mount(SpeechSettings);await flushPromises();
    expect(api.restoreSpeechSettings).not.toHaveBeenCalled();
    await wrapper.findAll('button').find(b=>b.text()==='Restore saved backup')!.trigger('click');await flushPromises();
    expect(api.restoreSpeechSettings).toHaveBeenCalledWith('damaged1');
    expect(wrapper.text()).toContain('damaged file was preserved');
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });

});
