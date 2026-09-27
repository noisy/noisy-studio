import {mount,flushPromises} from '@vue/test-utils';
import {beforeEach,expect,it,vi} from 'vitest';
import TaskReview from './TaskReview.vue';
import {setActiveAgent,reviewTask} from '../../api/client';
import type {DaemonStatus} from '../../types';
import type {ReviewTarget} from './types';
vi.mock('../../api/client',()=>({setActiveAgent:vi.fn(),reviewTask:vi.fn(),setSettings:vi.fn()}));
const target:ReviewTarget={agent:'thread-1',task:{report:{task_id:'task-1',revision:1,title:'Preview audio controls',state:'done',completed:3,total:3,participant:'child-1',role:'Dashboard agent',model:null,review:{label:'Preview',url:'http://localhost:6038/preview'}},updated_at:100,review_state:'unopened',stale:false}};
const status={active_agent:'thread-1',agent_labels:{'thread-1':'Bug fixing'},agent_voices:{'thread-1':'ara'},muted:false,detection_mode:'ptt',ptt_held:false,recording:false} as unknown as DaemonStatus;
beforeEach(()=>{vi.clearAllMocks();vi.mocked(setActiveAgent).mockResolvedValue('thread-1');vi.mocked(reviewTask).mockResolvedValue();HTMLDialogElement.prototype.showModal=vi.fn();HTMLDialogElement.prototype.close=vi.fn();});
function render(overrides:Partial<DaemonStatus>={}){return mount(TaskReview,{props:{target,status:{...status,...overrides},offline:false,utterances:[]},global:{stubs:{VoiceAvatar:true}}});}
it('selects the parent recipient and records opening without approving',async()=>{
 const wrapper=render();await flushPromises();
 expect(setActiveAgent).toHaveBeenCalledWith('thread-1');
 expect(vi.mocked(reviewTask).mock.calls).toEqual([['thread-1','task-1',1,'opened']]);
 await wrapper.get('.approve').trigger('click');
 expect(vi.mocked(reviewTask).mock.calls).toHaveLength(1);
 await wrapper.findAll('.confirmation button')[1]!.trigger('click');await flushPromises();
 expect(vi.mocked(reviewTask).mock.calls.at(-1)).toEqual(['thread-1','task-1',1,'approve']);
 wrapper.unmount();
});
it('does not record when the daemon refuses the intended recipient',async()=>{
 vi.mocked(setActiveAgent).mockResolvedValue('thread-2');const wrapper=render();await flushPromises();
 expect(wrapper.get('.talk').attributes('disabled')).toBeDefined();expect(reviewTask).not.toHaveBeenCalled();expect(wrapper.emitted('startPtt')).toBeUndefined();wrapper.unmount();
});
it('does not switch recipients during an existing recording',async()=>{
 const wrapper=render({recording:true});await flushPromises();expect(setActiveAgent).not.toHaveBeenCalled();expect(wrapper.text()).toContain('Finish the current recording');wrapper.unmount();
});
it('releases the shared PTT lease when the recipient changes',async()=>{
 const wrapper=render();await flushPromises();await wrapper.get('.talk').trigger('keydown',{key:' ',code:'Space'});expect(wrapper.emitted('startPtt')).toHaveLength(1);
 const before=wrapper.emitted('stopPtt')?.length??0;await wrapper.setProps({status:{...status,active_agent:'thread-2'}});
 expect((wrapper.emitted('stopPtt')?.length??0)>before).toBe(true);expect(wrapper.get('.talk').attributes('disabled')).toBeDefined();wrapper.unmount();
});
it('does not show successful approval when the artifact revision changed',async()=>{
 const wrapper=render();await flushPromises();vi.mocked(reviewTask).mockRejectedValueOnce(new Error('The task changed; reopen the current result before reviewing'));
 await wrapper.findAll('.confirmation button')[1]!.trigger('click');await flushPromises();expect(wrapper.get('.approve').text()).toBe('Approve…');expect(wrapper.text()).toContain('The task changed');wrapper.unmount();
});
