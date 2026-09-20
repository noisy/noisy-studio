import type { Meta, StoryObj } from '@storybook/vue3';
import Bubble from './Bubble.vue';
import { accentPalettes, resolveAccent } from '../styles/accentPalettes';

const meta: Meta = { title: 'Dashboard/AccentPalettes', parameters: { layout: 'fullscreen' } };
export default meta;

export const Comparison: StoryObj = {
  render: () => ({
    components: { Bubble },
    setup: () => ({ palettes: accentPalettes }),
    template: `<main style="padding:28px; color:var(--ink); height:100vh; overflow:auto; max-width:1280px">
      <h1 style="font-size:24px; margin:0 0 8px">Choose your accent</h1>
      <p style="color:var(--muted); margin:0 0 24px">Ten coordinated palettes. Use the Accent toolbar to preview any dashboard or companion story.</p>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:20px">
        <section v-for="palette in palettes" :key="palette.value" :data-accent="palette.value" style="padding:24px; border:1px solid var(--line); border-radius:16px; background:var(--panel)">
          <h2 style="margin:0 0 18px; font-size:18px; color:var(--amber)">{{ palette.title }}</h2>
          <div style="display:flex; flex-direction:column; gap:12px">
            <Bubble side="left" accent="amber" who="You" text="Can you fix the search and run the tests?" compact />
            <Bubble side="right" accent="violet" who="Claude" text="Both tests pass. The fix is ready." compact />
          </div>
          <div style="margin-top:24px; padding-top:20px; border-top:1px solid var(--line)">
            <span style="font-size:12px; color:var(--amber)">YOUR NEXT SESSION COULD SOUND DIFFERENT</span>
            <h3 style="font-size:22px; margin:10px 0 16px">Less typing. More conversation.</h3>
            <span style="display:inline-block; padding:10px 16px; border-radius:8px; background:var(--amber); color:var(--bg0); font-weight:600">Get started</span>
            <span style="display:inline-block; margin-left:14px; color:var(--green)">● Online</span>
          </div>
        </section>
      </div>
    </main>`,
  }),
};

export const Website: StoryObj = {
  render: (_, context) => ({
    setup: () => ({ url: `http://127.0.0.1:5201/?accent=${resolveAccent(context.globals.accent)}` }),
    template: `<div><p style="margin:0; padding:12px 20px; color:var(--muted)">Live local website · change Accent in the Storybook toolbar · requires the website dev server on port 5201</p><iframe :src="url" title="Website accent preview" style="display:block; width:100%; height:calc(100vh - 52px); border:0" /></div>`,
  }),
};
