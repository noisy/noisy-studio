import { mount } from '@vue/test-utils';
import { expect, it } from 'vitest';
import StagePrototype from './Stage.vue';

const people = [
  { id: 'a1', name: 'Atlas', voice: 'atlas' },
  { id: 'a2', name: 'Luna', voice: 'luna' },
  { id: 'a3', name: 'Lux', voice: 'lux' },
];
it('keeps positions stable when speaking changes or a portrait is hidden, without routing events', async () => {
  const wrapper = mount(StagePrototype, { props: { people, speaking: 'a1' } });
  const original = wrapper.get('[data-person="a3"]').attributes('style');
  await wrapper.get('[aria-label="Focus on Lux"]').trigger('click');
  await wrapper.setProps({ speaking: 'a3', people: [...people].reverse() });
  await wrapper.get('[aria-controls="stage-people"]').trigger('click');
  await wrapper.findAll('input')[2].setValue(false);

  expect(wrapper.find('[data-person="a1"]').exists()).toBe(false);
  expect(wrapper.get('[data-person="a3"]').attributes('style')).toBe(original);
  expect(wrapper.get('[data-person="a3"]').classes()).toContain('speaking');
  expect(wrapper.get('[aria-label="Focus on Lux"]').attributes('aria-pressed')).toBe('true');
  expect(wrapper.emitted('select')).toBeUndefined();
  expect(wrapper.emitted('change-recipient')).toBeUndefined();
  wrapper.unmount();
});
it('restores all hidden people and closes the picker before leaving with Escape', async () => {
  const wrapper = mount(StagePrototype, { props: { people: people.slice(0,1) } });
  await wrapper.get('[aria-controls="stage-people"]').trigger('click');
  await wrapper.get('input').setValue(false);
  expect(wrapper.text()).toContain('Make room for someone');
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  expect(wrapper.emitted('exit')).toBeUndefined();
  await wrapper.vm.$nextTick();
  await wrapper.findAll('button').find(button => button.text() === 'Show everyone')!.trigger('click');
  expect(wrapper.find('[data-person="a1"]').exists()).toBe(true);
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  expect(wrapper.emitted('exit')).toHaveLength(1);
  wrapper.unmount();
});
it('starts with heads only and shows a caption only when chosen', async () => {
  const wrapper = mount(StagePrototype, { props: { people, speaking: 'a2', lines: [{ id: 1, person: 'a2', text: 'A little breathing room.' }] } });
  expect(wrapper.find('.stage-caption').exists()).toBe(false);
  await wrapper.findAll('button').find(button => button.text() === 'Caption')!.trigger('click');
  expect(wrapper.get('.stage-caption').text()).toContain('A little breathing room.');
  wrapper.unmount();
});
