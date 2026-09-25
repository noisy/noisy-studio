import { mount } from '@vue/test-utils';
import { beforeEach, expect, it } from 'vitest';
import StageLive from './StageLive.vue';
import Stage from './Stage.vue';
import { STAGE_PREFERENCES_KEY } from '../stage/preferences';
import type { DaemonStatus } from '../types';
const status = { agents: { a1: 1, a2: 2 }, active_agent: 'a1', agent_labels: { a1: 'Release work', a2: 'Ideas' }, agent_voices: { a1: 'lux', a2: 'luna' }, playing_utterance_id: 0, speaking_agents: [] } as unknown as DaemonStatus;
beforeEach(() => localStorage.removeItem(STAGE_PREFERENCES_KEY));
it('persists hidden portraits, name mode and display across remount without changing recipient', async () => {
  const wrapper = mount(StageLive, { props: { status, utterances: [], offline: false } });
  await wrapper.get('[aria-controls="stage-people"]').trigger('click');
  await wrapper.get('input').setValue(false);
  await wrapper.get('select').setValue('conversation');
  await wrapper.findAll('button').find(b => b.text() === 'Transcript')!.trigger('click');
  wrapper.unmount();
  const restored = mount(StageLive, { props: { status, utterances: [], offline: false } });

  expect(restored.find('[data-person="a1"]').exists()).toBe(false);
  expect(restored.get('[data-person="a2"]').text()).toContain('Ideas');
  expect(restored.find('.stage-thread').exists()).toBe(true);
  expect(status.active_agent).toBe('a1');
  expect(JSON.parse(localStorage.getItem(STAGE_PREFERENCES_KEY)!)).toEqual({ hidden:['a1'], labels:'conversation', display:'thread' });
  restored.unmount();
});
it('falls back safely for damaged preferences and clears speaking while disconnected', () => {
  localStorage.setItem(STAGE_PREFERENCES_KEY, '{broken');
  const wrapper = mount(StageLive, { props: { status, utterances: [], offline: true } });
  expect(wrapper.getComponent(Stage).props()).toMatchObject({ initialDisplay:'heads', initialHidden:[], labelMode:'persona', speaking:'', caption:null });
  expect(wrapper.get('[role="status"]').text()).toContain('Connection lost');
  wrapper.unmount();
});
