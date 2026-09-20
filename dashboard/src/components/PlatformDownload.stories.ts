import type { Meta, StoryObj } from '@storybook/vue3';
import PlatformDownload from '../../../website/src/PlatformDownload.vue';

const meta: Meta<typeof PlatformDownload> = {
  title: 'Website/PlatformDownload',
  component: PlatformDownload,
  parameters: { layout: 'fullscreen', docs: { description: { component: 'Design preview: release URL is unset. Notification submissions are Storybook actions only; no email is sent or stored.' } } },
  argTypes: { platform: { control: 'select', options: ['mac', 'windows', 'linux'] }, onNotify: { action: 'notification preview' } },
  render: args => ({
    components: { PlatformDownload }, setup: () => ({ args }),
    template: `<main style="min-height:100vh;box-sizing:border-box;background:var(--bg0);color:var(--ink);padding:clamp(24px,5vw,70px);font-family:var(--sans)"><div style="max-width:1040px;margin:auto"><p style="font-size:14px;color:var(--muted);margin:0 0 48px">Noisy Studio / Platform download</p><div style="display:flex;flex-wrap:wrap;align-items:center;gap:48px"><div style="flex:1;min-width:240px"><p style="font-size:11px;letter-spacing:.13em;color:var(--brand-accent)">YOUR VOICE, IN THE WORKFLOW</p><h1 style="font-size:clamp(32px,4vw,48px);line-height:1.13;letter-spacing:-.04em;margin:18px 0">Your next session<br>could sound different.</h1><p style="max-width:340px;line-height:1.65;color:var(--muted)">Hear the progress. Give direction. Keep your attention on the work.</p></div><div style="flex:1;min-width:min(100%,320px)"><PlatformDownload v-bind="args" /></div></div></div></main>`,
  }),
};
export default meta;
type Story = StoryObj<typeof meta>;
export const Mac: Story = { name: 'macOS visitor', args: { platform: 'mac' } };
export const Windows: Story = { name: 'Windows visitor', args: { platform: 'windows' } };
export const Linux: Story = { name: 'Linux visitor', args: { platform: 'linux' } };
