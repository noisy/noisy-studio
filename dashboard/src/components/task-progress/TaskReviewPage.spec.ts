import { mount } from '@vue/test-utils';
import { ref } from 'vue';
import { expect, it, vi } from 'vitest';
import TaskReviewPage from './TaskReviewPage.vue';
vi.mock('../../composables/useTaskProgress',()=>({useTaskProgress:()=>({
 snapshot:ref({threads:{'thread-1':{'task-1':{report:{task_id:'task-1',title:'Onboarding flow',revision:2,state:'done',review:{label:'Review',url:'https://example.com'}}}}}}),error:ref(''),refresh:vi.fn()
})}));
it('requires opening the current revision before offering its approval controls',()=>{
 const wrapper=mount(TaskReviewPage,{props:{agent:'thread-1',taskId:'task-1',revision:1,status:null,offline:false,utterances:[]},global:{stubs:{TaskReview:true}}});
 expect(wrapper.find('task-review-stub').exists()).toBe(false);
 expect(wrapper.text()).toContain('This task has changed');
 expect(wrapper.get('a').attributes('href')).toBe('https://example.com/');
 wrapper.unmount();
});

it('keeps old wrapper URLs usable without mounting an iframe',()=>{
 const wrapper=mount(TaskReviewPage,{props:{agent:'thread-1',taskId:'task-1',revision:2,status:null,offline:false,utterances:[]},global:{stubs:{TaskReview:true}}});
 expect(wrapper.find('task-review-stub').exists()).toBe(false);
 expect(wrapper.get('a').attributes('href')).toBe('https://example.com/');
 wrapper.unmount();
});
