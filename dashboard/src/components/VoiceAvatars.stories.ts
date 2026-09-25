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

function atlas(setId: typeof AVATAR_SETS[number]['id']): StoryObj {
  return { render: () => ({
    components: { VoiceAvatar },
    setup: () => ({ setId, voices: [...AVATAR_VOICES, '', ''] }),
    template: `<main style="padding:24px;background:#b5d8cd;color:#18202a;width:max-content">
      <h2>{{ setId }} · 96 px · 28 assigned voices, two unused cells</h2>
      <div style="display:grid;grid-template-columns:repeat(6,112px);gap:12px">
        <div v-for="(voice,i) in voices" :key="i"><VoiceAvatar v-if="voice" :voice="voice" :set="setId" :size="96" /><div v-else style="width:96px;height:96px;border:1px dashed #667">Unused</div><p>{{ voice }}</p></div>
      </div>
    </main>`,
  }) };
}
export const IllustratedGrid = atlas('editorial');
export const MatteGrid = atlas('matte');
export const MineralGrid = atlas('mineral');
export const BlobsGrid = atlas('blobs');
export const AnimalsGrid = atlas('animals');
export const RobotsGrid = atlas('robots');
export const AgentsGrid = atlas('agents');

import { avatarFrameStyle, avatarImageStyle } from '../avatars/catalog';
export const IllustratedPngComparison: StoryObj = {
  render: () => ({
    components: { VoiceAvatar },
    setup: () => ({ voices: AVATAR_VOICES, avatarFrameStyle, avatarImageStyle,
      png: new URL('../assets/voice-avatars/editorial.png', import.meta.url).href }),
    template: `<main style="padding:24px;background:#b5d8cd;color:#18202a;width:max-content">
      <h2>Illustrated portraits · WebP / PNG · 96 px</h2>
      <div style="display:grid;grid-template-columns:repeat(6,210px);gap:12px">
        <div v-for="(voice,i) in voices" :key="voice">
          <VoiceAvatar :voice="voice" set="editorial" :size="96" />
          <span style="position:relative;display:inline-block;width:96px;height:96px;overflow:hidden;border-radius:24%;background:#2c394b">
            <span :style="{position:'absolute',overflow:'hidden',...avatarFrameStyle('editorial',i)}">
              <img :src="png" :style="{position:'absolute',maxWidth:'none',...avatarImageStyle('editorial',i)}" />
            </span>
          </span><p>{{ voice }}</p>
        </div>
      </div>
    </main>`,
  }),
};
