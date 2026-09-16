import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ModelDownloadProgress from './ModelDownloadProgress.vue';

describe('model download feedback', () => {
  it('shows measured bytes and leaves unknown totals indeterminate', () => {
    const wrapper = mount(ModelDownloadProgress, {props: {downloads: [
      {name:'model1',label:'Voice model',state:'downloading',done_bytes:136_000_000,total_bytes:326_000_000,detail:''},
      {name:'model2',label:'Recognition model',state:'downloading',done_bytes:0,total_bytes:0,detail:''},
    ]}});
    expect(wrapper.text()).toContain('136.0 MB / 326.0 MB · 41%');
    expect(wrapper.findAll('progress').map(p => p.attributes('value'))).toEqual(['136000000', undefined]);
  });
  it('replaces progress with completion and actionable failure feedback', async () => {
    const wrapper = mount(ModelDownloadProgress, {props: {downloads: [
      {name:'model1',label:'Voice model',state:'done',done_bytes:326_000_000,total_bytes:326_000_000,detail:''},
      {name:'model2',label:'Recognition model',state:'error',done_bytes:0,total_bytes:0,detail:'Connection lost. Retry download.'},
    ]}});
    expect(wrapper.findAll('progress')).toHaveLength(0);
    expect(wrapper.text()).toContain('Downloaded');
    expect(wrapper.text()).toContain('Connection lost. Retry download.');
  });
});
