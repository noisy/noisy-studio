import type { Meta, StoryObj } from '@storybook/vue3';
import { onMounted, onBeforeUnmount } from 'vue';
import HotkeySection from '../../../website/src/HotkeySection.vue';
import KeyboardHotkeyDemo from '../../../website/src/KeyboardHotkeyDemo.vue';
import CrewSection from '../../../website/src/CrewSection.vue';
import websiteStyles from '../../../website/src/style.css?inline';

const meta = {
  title: 'Website/WebsiteHotkeys',
  component: HotkeySection,
  parameters: { layout: 'fullscreen' },
  render: args => ({ components: { HotkeySection }, setup: () => ({ args }), template: '<HotkeySection v-bind="args" />' }),
} satisfies Meta<typeof HotkeySection>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Section: Story = { name: 'Complete section' };
export const Animation: Story = { name: 'Keyboard animation', render: () => ({ components: { KeyboardHotkeyDemo }, template: '<div style="padding:32px;background:#16191d;min-height:100vh;box-sizing:border-box"><div style="max-width:960px;margin:auto"><KeyboardHotkeyDemo /></div></div>' }) };
export const Static: Story = { name: 'Static / reduced motion', args: { staticPreview: true } };
export const AfterCrew: Story = { name: 'Below Meet your crew', render: () => ({
  components: { CrewSection, HotkeySection },
  setup() {
    const style = document.createElement('style');
    style.textContent = websiteStyles + '\nhtml, body, #storybook-root { height:auto; overflow:visible; }';
    onMounted(() => document.head.append(style)); onBeforeUnmount(() => style.remove());
  }, template: '<CrewSection /><HotkeySection />',
}) };
