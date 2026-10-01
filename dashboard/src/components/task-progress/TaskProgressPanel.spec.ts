import { mount } from '@vue/test-utils';
import { ref } from 'vue';
import { expect, it, vi } from 'vitest';
import TaskProgressPanel from './TaskProgressPanel.vue';
vi.mock('../../api/client', () => ({reviewTask:vi.fn().mockResolvedValue(undefined)}));
vi.mock('../../composables/useTaskProgress', () => ({ useTaskProgress: () => ({
  snapshot: ref({ threads: { 'thread-1': { 'task-1': { report: {
    task_id:'task-1', revision:1, title:'New onboarding flow', state:'done', completed:1,total:1,
    review:{label:'Review onboarding',url:'https://example.com/onboarding'},
  },review_state:'unopened',updated_at:100,stale:false } } } }), error:ref(''), refresh:vi.fn(),
}) }));
it.each([undefined,'thread-1'])('opens review externally in the %s panel without mounting the in-app review', async agent => {
  const wrapper=mount(TaskProgressPanel,{props:{agent,status:{agent_labels:{'thread-1':'Design'}} as any,offline:false,utterances:[]}});
  const link=wrapper.get('a[aria-label="Review onboarding"]');
  expect({href:link.attributes('href'),target:link.attributes('target'),rel:link.attributes('rel')}).toEqual({href:window.location.origin+window.location.pathname+'?review_agent=thread-1&review_task=task-1&review_revision=1',target:'_blank',rel:'noopener noreferrer'});
  link.element.addEventListener('click', event => event.preventDefault());
 await link.trigger('click');
  expect(wrapper.find('iframe').exists()).toBe(false);
  expect(wrapper.findAll('button').map(button => button.text())).not.toContain('Feedback');
  expect(wrapper.emitted('reviewOpen')).toBeUndefined();
  wrapper.unmount();
});
