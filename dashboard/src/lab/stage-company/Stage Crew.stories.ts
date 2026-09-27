import type { Meta, StoryObj } from '@storybook/vue3';
import CompanyStage from './CompanyStage.vue';
import { departments } from './cast';
const meta = {
  title: 'Lab/Stage Crew', component: CompanyStage,
  parameters: { layout: 'fullscreen', docs: { description: { component: 'Flat Stage crew: equal department leads with smaller specialist portraits. No CEO, chart, or connector lines. Colorful working portraits and desaturated idle portraits also have textual status. Synthetic fixtures only; no live integration.' } } },
  args: { departments, speaking: 'design-1', variant: 'heads' },
  argTypes: { variant: { control: 'select', options: ['heads', 'caption', 'constellation'] }, speaking: { control: 'select', options: ['', ...departments.flatMap(d => [d.lead.id, ...d.workers.map(p => p.id)])] } },
} satisfies Meta<typeof CompanyStage>;
export default meta;
type Story = StoryObj<typeof meta>;
export const JustFaces: Story = {};
export const WithCaption: Story = { args: { variant: 'caption' } };
export const LooseConstellations: Story = { args: { variant: 'constellation' } };
