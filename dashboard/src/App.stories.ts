import type { Meta, StoryObj } from '@storybook/vue3';
import App from './App.vue';
import { speechFixture } from './components/speechSettings.fixture';
import { resetScenario, setSpeechSettingsFixture, type Scenario } from './storybook/daemon.fixture';
const meta:Meta = {
  title: 'Dashboard/App', component:App, parameters:{layout:'fullscreen'},
};
export default meta;
function story(scenario:Scenario):StoryObj {
  return {render:()=>{ resetScenario(scenario); return {components:{App},template:'<App />'}; }};
}
export const Conversation=story('conversation');
export const LocalSpeech=story('local-speech');
export const Recording=story('recording');
export const Speaking=story('speaking');
export const Queued=story('queued');
export const Muted=story('muted');
export const Offline=story('offline');
export const Error=story('error');
export const Empty=story('empty');
// The last tab was closed: the pane goes with it, no tab-less conversation (#101).
export const LastTabClosed=story('no-tabs');
export const Setup=story('setup');
export const Shutdown=story('shutdown');
export const LongContent=story('long');

// A full dashboard, including the extra push-to-talk action, at laptop height.
export const Laptop:StoryObj = {
  ...story('conversation'),
  parameters: {
    viewport: {
      defaultViewport: 'laptop',
      viewports: {
        laptop: { name: 'Laptop 1280 × 800', styles: { width: '1280px', height: '800px' }, type: 'desktop' },
      },
    },
  },
};

export const RecoverSpeechSettings:StoryObj = {
  render: () => {
    resetScenario('setup');
    setSpeechSettingsFixture(speechFixture(), Object.assign(new globalThis.Error('Saved speech settings are unreadable or invalid. No fallback engine was selected.'), {recovery:{revision:'damaged-fixture',can_restore:true}}));
    return {components:{App},template:'<App />'};
  },
};

// The app has no instance badge; source endpoints clearly identify development.
function instanceStory(port: string): StoryObj {
  return {render: () => {
    resetScenario('conversation');
    return {components: {App}, setup: () => ({port}), template: '<App :instance-port="port" />'};
  }};
}
export const NativeApp = instanceStory('9765');
export const DevInstance = instanceStory('7765');
export const SourceCompatibilityPort = instanceStory('8765');

export const ProviderPlanLimits: StoryObj = {
  parameters: { docs: { description: { story: 'Production compact component with synthetic registered-provider readings. No live quota requests.' } } },
  render: () => {
    const now = Date.now() / 1000;
    resetScenario('conversation', {
      version: __APP_VERSION__, latest_version: __APP_VERSION__,
      provider_usage: [
        { provider: 'claude', label: 'Claude', scope: 'connection', sampled_at: now, message: '', windows: [
          { label: 'Session', used_percent: 76, resets_at: now + 2520, stale: false },
          { label: 'Weekly', used_percent: 48, resets_at: now + 288000, stale: false },
        ] },
        { provider: 'codex', label: 'Codex', scope: 'connection', sampled_at: now, message: '', windows: [
          { label: 'Weekly', used_percent: 91, resets_at: now + 7200, stale: false },
        ] },
      ],
    });
    return { components: { App }, template: '<App />' };
  },
};
