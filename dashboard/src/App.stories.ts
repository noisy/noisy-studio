import type { Meta, StoryObj } from '@storybook/vue3';
import App from './App.vue';
import { resetScenario, type Scenario } from './storybook/daemon.fixture';
const meta:Meta = {
  title:'Product/Dashboard', component:App, parameters:{layout:'fullscreen'},
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
