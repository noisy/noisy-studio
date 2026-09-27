import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import VoicePersona from './VoicePersona.vue';

describe('VoicePersona mute controls', () => {
  it.each(['lux', 'unknown-voice'])('keeps the %s portrait an accessible mute action', async voice => {
    const wrapper = mount(VoicePersona, { props: { voice, muted: true } });
    const portrait = wrapper.get('button[aria-label="Unmute this conversation"]');
    expect(portrait.attributes('aria-pressed')).toBe('true');
    await portrait.trigger('click');
    expect(wrapper.emitted('toggle-mute')).toEqual([[]]);
  });
});

it('keeps voice and character overlays exclusive and forwards character edits', async () => {
  const wrapper = mount(VoicePersona, { attachTo: document.body, props: {
    voice: 'ara', character: { voice: 'ara', speed: 1, humor: 50, honesty: 80, verbosity: 30, talkative: 40 },
  } });
  await wrapper.get('[aria-label="Choose voice"]').trigger('click');
  expect(wrapper.find('.voicelist').exists()).toBe(true);
  await wrapper.get('.character-button').trigger('click');
  expect([wrapper.find('.voicelist').exists(), wrapper.find('[role="dialog"]').exists()]).toEqual([false, true]);
  await wrapper.get('input[type="range"]').setValue('65');
  expect(wrapper.emitted('characterChange')).toBeTruthy();
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  await wrapper.vm.$nextTick();
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  expect(document.activeElement).toBe(wrapper.get('.character-button').element);
  wrapper.unmount();
});
