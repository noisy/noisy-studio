import { mount, flushPromises } from '@vue/test-utils';
import { beforeEach, expect, it, vi } from 'vitest';
import ReviewItem from './ReviewItem.vue';
import { reviewTask } from '../../api/client';
import type { ReportedTask } from './types';
vi.mock('../../api/client', () => ({reviewTask:vi.fn().mockResolvedValue(undefined)}));
const task: ReportedTask = {report:{task_id:'task-1',revision:2,title:'New onboarding flow',state:'done',completed:1,total:1,participant:null,role:null,model:null,review:{label:'Review onboarding',url:'https://gitlab.com/example/project',direct:true}},review_state:'unopened',updated_at:100,stale:false};
beforeEach(() => { vi.mocked(reviewTask).mockReset().mockResolvedValue(undefined); });
it('opens the whole item directly and reveals decisions only after saving the visit', async () => {
 const wrapper=mount(ReviewItem,{props:{agent:'thread-1',task,offline:false}});
 expect(wrapper.findAll('button')).toHaveLength(0);
 const link=wrapper.get('a');
 expect(link.attributes('href')).toBe(task.report.review!.url);
 expect(link.text()).toContain(task.report.title);
 link.element.addEventListener('click', event => event.preventDefault());
 await link.trigger('click'); await flushPromises();
 expect(reviewTask).toHaveBeenCalledWith('thread-1','task-1',2,'opened');
 expect(wrapper.findAll('button').map(b=>b.text())).toEqual(['Approve','Reject']);
 await wrapper.findAll('button')[1]!.trigger('click'); await flushPromises();
 expect(reviewTask).toHaveBeenLastCalledWith('thread-1','task-1',2,'reject');
 expect(wrapper.findAll('button')).toHaveLength(0);
});
it('keeps wrapper navigation for existing reports', () => {
 const wrapper=mount(ReviewItem,{props:{agent:'thread-1',task:{...task,report:{...task.report,review:{...task.report.review!,direct:undefined}}},offline:false}});
 expect(wrapper.get('a').attributes('href')).toContain('review_revision=2');
});
it('does not reveal decisions when saving the visit fails', async () => {
 vi.mocked(reviewTask).mockRejectedValue(new Error('Task changed'));
 const wrapper=mount(ReviewItem,{props:{agent:'thread-1',task,offline:false}});
 wrapper.get('a').element.addEventListener('click', event => event.preventDefault());
 await wrapper.get('a').trigger('click'); await flushPromises();
 expect(wrapper.get('[role="alert"]').text()).toBe('Task changed');
 expect(wrapper.findAll('button')).toHaveLength(0);
});
it('restores opened controls and leaves approval explicit', async () => {
 const wrapper=mount(ReviewItem,{props:{agent:'thread-1',task:{...task,review_state:'opened'},offline:false}});
 expect(reviewTask).not.toHaveBeenCalled();
 await wrapper.findAll('button')[0]!.trigger('click'); await flushPromises();
 expect(reviewTask).toHaveBeenCalledWith('thread-1','task-1',2,'approve');
});
