import type { Meta, StoryObj } from '@storybook/vue3';
import Website from '../../../website/src/App.vue';
import { onMounted, onBeforeUnmount } from 'vue';
import websiteStyles from '../../../website/src/style.css?inline';

const meta = {
  title: 'Website/LandingPage',
  component: Website,
  args: { dashboardPreviewUrl: './iframe.html?id=product-dashboard--conversation&viewMode=story' },
  render: args => ({ components: { Website }, setup() {
    const style = document.createElement('style');
    style.textContent = websiteStyles + '\nhtml, body, #storybook-root { height: auto; overflow: visible; }';
    onMounted(() => document.head.append(style));
    onBeforeUnmount(() => style.remove());
    return { args };
  }, template: '<Website v-bind="args" />' }),
  parameters: { layout: 'fullscreen', docs: { description: { component: 'Full website preview with platform-specific calls to action. Downloads and notifications are design previews only.' } } },
  argTypes: { previewPlatform: { control: 'select', options: ['mac', 'windows', 'linux'] } },
} satisfies Meta<typeof Website>;
export default meta;
type Story = StoryObj<typeof meta>;
export const ComingSoon: Story = { name: 'Current website · Coming soon', args: {} };
export const Mac: Story = { name: 'macOS visitor', args: { previewPlatform: 'mac' } };
export const Windows: Story = { name: 'Windows visitor', args: { previewPlatform: 'windows' } };
export const Linux: Story = { name: 'Linux visitor', args: { previewPlatform: 'linux' } };
