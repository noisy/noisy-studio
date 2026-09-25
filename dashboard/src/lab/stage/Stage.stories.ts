import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';
import StagePrototype, { type StagePerson } from './StagePrototype.vue';

const people: StagePerson[] = [
  { id: 'a1', name: 'Atlas', voice: 'atlas' },
  { id: 'a2', name: 'Luna', voice: 'luna' },
  { id: 'a3', name: 'Lux', voice: 'lux' },
  { id: 'a4', name: 'Orion', voice: 'orion' },
  { id: 'a5', name: 'Iris', voice: 'iris' },
  { id: 'a6', name: 'Ara', voice: 'ara' },
];
const lines = [
  { id: 1, person: 'a1', text: 'What if we stopped looking for the perfect plan and picked the most interesting question?' },
  { id: 2, person: 'a2', text: 'I like that. Which part of today surprised you?' },
  { id: 3, person: 'a3', text: 'For me, it was how much better a small conversation feels when nobody is rushing to finish it.' },
];
const meta = {
  title: 'Lab/Stage', component: StagePrototype,
  parameters: { layout: 'fullscreen', docs: { description: { component: 'Isolated visual prototype. Portrait focus and hiding never change microphone routing. Captions and transcript use synthetic examples; no live conversations or agent coordination.' } } },
  args: { people: people.slice(0,3), speaking: 'a3', lines },
  argTypes: { speaking: { control: 'select', options: ['', ...people.map(p => p.id)] }, initialDisplay: { control: 'select', options: ['heads','caption','thread'] } },
  render: args => ({
    components: { StagePrototype },
    setup() { const exited = ref(false); return { args, exited }; },
    template: `<StagePrototype v-if="!exited" v-bind="args" @exit="exited = true" /><div v-else style="min-height:100vh;background:#10211f;color:#d9e4cc;display:grid;place-content:center;text-align:center;font-family:system-ui"><p>Back to the dashboard</p><p style="font-size:12px;opacity:.65">Prototype only — your live dashboard was not changed.</p><button style="padding:12px;border-radius:8px;cursor:pointer" @click="exited = false">Return to Stage</button></div>`,
  }),
} satisfies Meta<typeof StagePrototype>;
export default meta;
type Story = StoryObj<typeof meta>;
export const ThreePeople: Story = {};
export const OnePerson: Story = { args: { people: people.slice(0,1), speaking: 'a1' } };
export const SixPeople: Story = { args: { people } };
export const ManyPeople: Story = { args: { people: [...people, ...people.map((p,i) => ({ ...p, id: `b${i}`, name: ['Kepler','Vega','Rex','Nova','Sol','Echo'][i] }))] } };
export const OfflineAndMuted: Story = { args: { people: people.map((p,i) => ({ ...p, offline: i === 1, muted: i === 4 })) } };
export const LongNames: Story = { args: { people: people.slice(0,3).map((p,i) => ({ ...p, name: ['Architecture and product thinking','A very thoughtful conversation about tomorrow','Release preparation and last-minute discoveries'][i] })) } };
export const ReducedMotion: Story = { args: { people, reducedMotion: true } };
export const Empty: Story = { args: { people: [], speaking: '', lines: [] } };
export const CurrentCaption: Story = { args: { initialDisplay: 'caption' } };
export const SharedTranscript: Story = { args: { initialDisplay: 'thread' } };
export const NarrowScreen: Story = { parameters: { viewport: { defaultViewport: 'mobile1' } } };
