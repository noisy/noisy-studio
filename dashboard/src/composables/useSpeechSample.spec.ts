import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSpeechSample } from './useSpeechSample';

function harness() {
  let sample!: ReturnType<typeof useSpeechSample>;
  const onSample = vi.fn().mockResolvedValue(undefined);
  const wrapper = mount(defineComponent({setup() {sample=useSpeechSample(onSample);return {};},template:'<div />'}));
  return {sample, onSample, wrapper};
}
afterEach(() => {vi.unstubAllGlobals();vi.useRealTimers();});

describe('microphone sample ownership', () => {
  it('releases a late microphone grant after cancellation without starting capture', async () => {
    const stop = vi.fn();
    let grant!: (stream: MediaStream) => void;
    const request = new Promise<MediaStream>(resolve => {grant=resolve;});
    vi.stubGlobal('navigator', {mediaDevices:{getUserMedia:()=>request}});
    const {sample, wrapper, onSample}=harness();
    const pending=sample.start();
    sample.cancel();
    grant({getTracks:()=>[{stop}]} as unknown as MediaStream);
    await pending;
    expect(stop).toHaveBeenCalledOnce();
    expect(sample.recording.value).toBe(false);
    expect(onSample).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('a stale stop event cannot stop the new sample or clear its duration limit', async () => {
    vi.useFakeTimers();
    const recorders: FakeRecorder[]=[];
    class FakeRecorder {
      state='inactive';
      onstop?: ()=>Promise<void>;
      constructor() {recorders.push(this);}
      start() {this.state='recording';}
      stop=vi.fn(()=>{this.state='inactive';});
    }
    vi.stubGlobal('MediaRecorder',FakeRecorder);
    vi.stubGlobal('navigator',{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop:vi.fn()}]})}});
    const {sample, wrapper, onSample}=harness();
    await sample.start();
    await sample.start();
    await recorders[0]!.onstop!();
    expect(sample.recording.value).toBe(true);
    await vi.advanceTimersByTimeAsync(15000);
    expect(recorders[1]!.stop).toHaveBeenCalledOnce();
    expect(onSample).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('releases microphone tracks if this browser cannot construct a recorder', async () => {
    const stop=vi.fn();
    vi.stubGlobal('navigator',{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop}]})}});
    vi.stubGlobal('MediaRecorder',class {constructor(){throw new Error('Unsupported recorder');}});
    const {sample,wrapper}=harness();
    await expect(sample.start()).rejects.toThrow('Unsupported recorder');
    expect(stop).toHaveBeenCalledOnce();
    wrapper.unmount();
  });
});
