import type { Meta, StoryObj } from '@storybook/vue3';
import SpeechSettings from './SpeechSettings.vue';
import { speechFixture } from './speechSettings.fixture';
import { setSpeechSettingsFixture } from '../storybook/daemon.fixture';
const meta: Meta<typeof SpeechSettings> = {title: 'Settings/Speech', component: SpeechSettings};
export default meta;
type Story = StoryObj<typeof SpeechSettings>;
function story(state: Parameters<typeof speechFixture>[0] = 'ready', direction?: 'stt' | 'tts', width = 940): Story {
  return {render: () => ({components: {SpeechSettings}, setup() {setSpeechSettingsFixture(speechFixture(state)); return {width};}, template:'<div :style="{maxWidth: width + `px`, padding: `24px`}"><SpeechSettings /></div>'}),
    play: async ({canvasElement}) => {
      if (!direction) return;
      const buttons = () => [...canvasElement.querySelectorAll('button')];
      for (let i=0; i<30 && !buttons().some(b=>b.textContent?.trim()==='Change'); i++) await new Promise(r=>setTimeout(r,30));
      buttons().filter(b=>b.textContent?.trim()==='Change')[direction==='stt'?0:1]?.click();
      await new Promise(r=>setTimeout(r,30));
      buttons().find(b=>b.textContent?.includes(direction==='tts'?'Kokoro':'Whisper base'))?.click();
    }};
}
export const Overview = story();
export const Recognition = story('ready','stt');
export const VoiceReassignment = story('ready','tts');
export const DownloadNeeded = story('download','stt');
export const Downloading = story('downloading','stt');
export const DownloadFailed = story('error','tts');
export const MissingOfflineSupport = story('setup','stt');
export const Narrow = story('ready','tts',380);
export const ThirdProvider: Story = {render: () => ({components:{SpeechSettings},setup(){const info=speechFixture();info.engines.push({...info.engines[1]!,id:'example:tts',provider:'example',label:'Example provider',state:'setup',detail:'Fixture only: tests a third provider without special UI code.'});setSpeechSettingsFixture(info);},template:'<SpeechSettings />'})};
