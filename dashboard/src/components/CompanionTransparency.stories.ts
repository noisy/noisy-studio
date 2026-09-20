import type { Meta, StoryObj } from '@storybook/vue3';
import CompanionPreview from '../storybook/CompanionPreview.vue';
import { resetScenario } from '../storybook/daemon.fixture';

const meta: Meta<typeof CompanionPreview> = {
  title: 'Lab/CompanionTransparency',
  component: CompanionPreview,
  parameters: { layout: 'fullscreen' },
  args: { backdrop: 'light', width: 420, height: 280 },
  argTypes: {
    backdrop: { control: 'select', options: ['light', 'dark', 'colorful'] },
    width: { control: { type: 'range', min: 280, max: 600, step: 20 } },
    height: { control: { type: 'range', min: 200, max: 500, step: 20 } },
  },
  render: args => {
    resetScenario('conversation');
    return { components: { CompanionPreview }, setup: () => ({ args }), template: '<CompanionPreview v-bind="args" />' };
  },
};
export default meta;
type Story = StoryObj<typeof meta>;
export const Light: Story = {};
export const Dark: Story = { args: { backdrop: 'dark' } };
export const Colorful: Story = { args: { backdrop: 'colorful' } };
export const SmallestWindow: Story = { args: { width: 280, height: 200 } };
export const UserSizedWindow: Story = { args: { height: 500 }, parameters: { docs: { description: { story: 'The user-sized window keeps its full height when switching between populated and empty conversations. Hover reveals the fixed frame and drag bar.' } } } };
