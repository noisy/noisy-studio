import type { Meta, StoryObj } from '@storybook/vue3';
import CompanyStage from './CompanyStage.vue';
import { ceo, departments } from './cast';
const meta = {
  title: 'Lab/Company Stage', component: CompanyStage,
  parameters: { layout: 'fullscreen', docs: { description: { component: 'Fictional company cast. CEO, department leads, and smaller specialist portraits. Presentation prototypes only: no live hierarchy, microphone routing, or agent coordination.' } } },
  args: { ceo, departments, speaking: 'design-1', variant: 'company' },
  argTypes: { variant: { control: 'select', options: ['company', 'spotlight', 'poster'] }, speaking: { control: 'select', options: ['', ceo.id, ...departments.flatMap(d => [d.lead.id, ...d.workers.map(p => p.id)])] } },
} satisfies Meta<typeof CompanyStage>;
export default meta;
type Story = StoryObj<typeof meta>;
export const CompanyPortrait: Story = {};
export const DepartmentSpotlight: Story = { args: { variant: 'spotlight' } };
export const OnAirPoster: Story = { args: { variant: 'poster' } };
