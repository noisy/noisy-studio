import {effectScope,nextTick} from 'vue';
import {it,expect,afterEach} from 'vitest';
import {useAudioControlVisibility} from './useAudioControlVisibility';
afterEach(()=>localStorage.clear());
it('persists an explicitly empty selection instead of restoring defaults',async()=>{
 const scope=effectScope();
 const visible=scope.run(()=>useAudioControlVisibility())!;
 visible.value=[];
 await nextTick();
 const restored=scope.run(()=>useAudioControlVisibility())!;
 expect(restored.value).toEqual([]);
 scope.stop();
});
