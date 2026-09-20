import type { Meta, StoryObj } from '@storybook/vue3';
import CompanionView from './CompanionView.vue';
import { resetScenario, type Scenario } from '../storybook/daemon.fixture';

const meta: Meta = { title: 'Widget/CompanionView', component: CompanionView, parameters: { layout: 'fullscreen' } };
export default meta;
function story(scenario: Scenario): StoryObj {
  return { render: () => {
    resetScenario(scenario);
    return { components: { CompanionView }, template: '<div style="height:100dvh"><CompanionView /></div>' };
  } };
}
export const Conversation = story('conversation');
export const Recording = story('recording');
export const Muted = story('muted');
