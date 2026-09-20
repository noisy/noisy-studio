import type { Meta, StoryObj } from '@storybook/vue3';
import VoiceAvatar from './VoiceAvatar.vue';
import AvatarSetPicker from './AvatarSetPicker.vue';
import { AVATAR_SETS, AVATAR_VOICES } from '../avatars/catalog';

const meta: Meta = { title: 'Dashboard/VoiceAvatars', parameters: { layout: 'fullscreen' } };
export default meta;
export const AllSets: StoryObj = {
  render: () => ({
    components: { VoiceAvatar },
    setup: () => ({ sets: AVATAR_SETS, voices: AVATAR_VOICES }),
    template: `<main style="height:100dvh;overflow:auto;box-sizing:border-box;padding:24px;background:var(--bg0);color:var(--ink)">
      <h1 style="font-size:22px">Voice avatar families</h1>
      <p style="margin:8px 0 24px;color:var(--muted)">{{ voices.length }} voices · {{ sets.length }} styles · 72 px and 44 px previews</p>
      <section v-for="set in sets" :key="set.id" style="margin-bottom:32px">
        <h2 style="font-size:16px;margin-bottom:12px">{{ set.name }} — {{ set.description }}</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:14px">
          <div v-for="voice in voices" :key="voice" style="display:grid;gap:6px">
            <div style="display:flex;align-items:end;gap:4px"><VoiceAvatar :voice="voice" :set="set.id" :size="72" /><VoiceAvatar :voice="voice" :set="set.id" :size="44" /></div>
            <span style="font-size:12px;color:var(--muted)">{{ voice }}</span>
          </div>
        </div>
      </section>
    </main>`,
  }),
};
export const ChooseSet: StoryObj = {
  render: () => ({ components: { AvatarSetPicker }, template: '<div style="height:100dvh;overflow:auto;box-sizing:border-box;padding:24px;max-width:1040px"><AvatarSetPicker /></div>' }),
};
export const UnknownVoice: StoryObj = {
  render: () => ({ components: { VoiceAvatar }, template: '<div style="padding:24px"><VoiceAvatar voice="future-voice" :size="72" /><p>A future voice keeps a readable fallback.</p></div>' }),
};
