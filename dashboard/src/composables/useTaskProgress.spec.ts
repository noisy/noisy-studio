import {mount,flushPromises} from '@vue/test-utils';
import {afterEach,expect,it,vi} from 'vitest';
import {useTaskProgress} from './useTaskProgress';
import {getTaskProgress} from '../api/client';
import type {TaskSnapshot} from '../components/task-progress/types';
vi.mock('../api/client',()=>({getTaskProgress:vi.fn()}));
afterEach(()=>{vi.useRealTimers();vi.clearAllMocks();});
it('ignores stale responses after refresh and aborts when the panel unmounts',async()=>{
 vi.useFakeTimers();let first!:(value:TaskSnapshot)=>void;let second!:(value:TaskSnapshot)=>void;
 vi.mocked(getTaskProgress).mockImplementationOnce(()=>new Promise(resolve=>{first=resolve})).mockImplementationOnce(()=>new Promise(resolve=>{second=resolve}));
 let progress!:ReturnType<typeof useTaskProgress>;const wrapper=mount({setup(){progress=useTaskProgress();return()=>null;}});
 void progress.refresh();second({threads:{'thread-2':{}},error:null});await flushPromises();first({threads:{'thread-1':{}},error:null});await flushPromises();
 expect(progress.snapshot.value.threads).toEqual({'thread-2':{}});
 const signals=vi.mocked(getTaskProgress).mock.calls.map(call=>call[0]);expect(signals[0]?.aborted).toBe(true);
 wrapper.unmount();expect(signals[1]?.aborted).toBe(true);await vi.advanceTimersByTimeAsync(15000);expect(getTaskProgress).toHaveBeenCalledTimes(2);
});

it('shares one feed across sibling panels when the dashboard provides it', async () => {
 vi.useFakeTimers();vi.mocked(getTaskProgress).mockResolvedValue({threads:{},error:null});
 const {provideTaskProgress}=await import('./useTaskProgress');
 const {defineComponent,h}=await import('vue');
 const Child=defineComponent({setup(){useTaskProgress();return()=>null;}});
 const wrapper=mount(defineComponent({setup(){provideTaskProgress();return()=>h('div',[h(Child),h(Child)]);}}));
 await flushPromises();expect(getTaskProgress).toHaveBeenCalledTimes(1);
 wrapper.unmount();await vi.advanceTimersByTimeAsync(15000);expect(getTaskProgress).toHaveBeenCalledTimes(1);
});
