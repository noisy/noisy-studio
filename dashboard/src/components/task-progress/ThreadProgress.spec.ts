import { mount } from '@vue/test-utils';
import { afterEach, expect, it, vi } from 'vitest';
import ThreadProgress from './ThreadProgress.vue';
import type { ReportedTask } from './types';
const task: ReportedTask = { report: { task_id:'task-1',revision:1,title:'Mobile reconnect',state:'working',completed:1,total:4,participant:'child-1',role:null,model:'Unused model',review:null },started_at:100,updated_at:150,review_state:'unopened',stale:false };
afterEach(() => vi.useRealTimers());
it('counts from task start independently of report updates and leaves unknown starts unknown', async () => {
  vi.useFakeTimers(); vi.setSystemTime(160000);
  const wrapper = mount(ThreadProgress, { props: { tasks: [task] } });
  expect(wrapper.text()).toContain('1m 00s');
  await wrapper.setProps({ tasks: [{ ...task, updated_at: 160 }] });
  await vi.advanceTimersByTimeAsync(1000);
  expect(wrapper.text()).toContain('1m 01s');
  await wrapper.setProps({ tasks: [{ ...task, started_at: null }] });
  expect(wrapper.get('small').text()).toBe('—');
  wrapper.unmount();
});
it('keeps ready results out of progress and omits model and subagent labels', () => {
  const ready: ReportedTask = { ...task,report:{ ...task.report,task_id:'task-2',title:'Onboarding flow',state:'done',review:{ label:'Review',url:'http://localhost:6041' } } };
  const wrapper = mount(ThreadProgress, { props: { tasks: [{...task,started_at:null},ready] } });
  expect(wrapper.findAll('article').map(row => row.text())).toEqual(['Mobile reconnect—25%']);
  wrapper.unmount();
});
