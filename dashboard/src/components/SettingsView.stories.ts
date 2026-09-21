import type { Meta, StoryObj } from "@storybook/vue3";
import SettingsView from "./SettingsView.vue";

const meta: Meta<typeof SettingsView> = {
  component: SettingsView,
  title: "Dashboard/SettingsView",
};
export default meta;

export const Configured: StoryObj<typeof SettingsView> = {
  args: { apiKeyHint: "····kRc9" },
  render: (args) => ({
    components: { SettingsView },
    setup: () => ({ args }),
    template: `<div style="max-width:720px"><SettingsView v-bind="args" /></div>`,
  }),
};

export const NativeAudio: StoryObj<typeof SettingsView> = {
  args: { apiKeyHint: "configured", devices: [{ name: "System microphone", default: true }], selectedDevice: "" },
  render: (args) => ({
    components: { SettingsView }, setup: () => ({ args }),
    template: `<div style="max-width:760px"><SettingsView v-bind="args" /></div>`,
    mounted() { (this.$el as HTMLElement).querySelectorAll<HTMLButtonElement>(".tabbtn").forEach((b) => { if (b.textContent?.trim() === "Audio") b.click(); }); },
  }),
};

// Settings > Hotkeys (#104): the tab is HUD/Hotkeys tab; here only the
// pointer in Audio and the tab switch are of interest.
export const HotkeysTab: StoryObj<typeof SettingsView> = {
  args: { apiKeyHint: "····kRc9", hotkeys: { configured: true, permission: "granted", armed: true, stored: { hold: "F8", toggle: "F15", scratch: "escape", tab1: "F1" }, problems: {} } },
  render: (args) => ({
    components: { SettingsView },
    setup: () => ({ args }),
    template: `<div style="max-width:760px"><SettingsView v-bind="args" /></div>`,
    mounted() { (this.$el as HTMLElement).querySelectorAll<HTMLButtonElement>(".tabbtn").forEach((b) => { if (b.textContent?.trim() === "Hotkeys") b.click(); }); },
  }),
};
