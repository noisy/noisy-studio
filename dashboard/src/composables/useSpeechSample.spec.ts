import { defineComponent } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';
import { afterEach, expect, it, vi } from 'vitest';
import { useSpeechSample } from './useSpeechSample';

function harness() {
  let sample!: ReturnType<typeof useSpeechSample>;
  const onSample = vi.fn().mockResolvedValue(undefined);
  const wrapper = mount(defineComponent({setup() {sample=useSpeechSample(onSample);return {};},template:'<div />'}));
  return {sample, onSample, wrapper};
}
const response = (data: unknown) => ({ok:true,json:async()=>data});
afterEach(() => {vi.unstubAllGlobals();vi.useRealTimers();});

it('finishes a bounded native sample and sends it for recognition', async () => {
  vi.useFakeTimers();
  const fetcher = vi.fn().mockResolvedValueOnce(response({id:'sample-1'})).mockResolvedValueOnce(response({audio:'native-wav'}));
  vi.stubGlobal('fetch',fetcher);
  const {sample,onSample,wrapper}=harness();
  await sample.start();
  await vi.advanceTimersByTimeAsync(15000);
  expect(JSON.parse(fetcher.mock.calls[1]![1].body)).toEqual({action:'finish',id:'sample-1'});
  expect(onSample).toHaveBeenCalledWith('native-wav');
  wrapper.unmount();
});
it('cancels a native sample whose start response arrived after unmount', async () => {
  let complete!: (value: unknown) => void;
  const fetcher = vi.fn().mockImplementationOnce(()=>new Promise(resolve=>{complete=resolve;})).mockResolvedValue(response({}));
  vi.stubGlobal('fetch',fetcher);
  const {sample,onSample,wrapper}=harness();
  const pending=sample.start(); await flushPromises();
  wrapper.unmount(); complete(response({id:'sample-2'})); await pending;
  expect(JSON.parse(fetcher.mock.calls[1]![1].body)).toEqual({action:'cancel',id:'sample-2'});
  expect(onSample).not.toHaveBeenCalled();
});
