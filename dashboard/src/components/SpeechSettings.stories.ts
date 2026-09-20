import type { Meta, StoryObj } from '@storybook/vue3';
import SpeechSettings from './SpeechSettings.vue';
import { speechFixture } from './speechSettings.fixture';
import { setSpeechSettingsFixture } from '../storybook/daemon.fixture';
const meta: Meta<typeof SpeechSettings> = {title: 'Dashboard/SpeechSettings', component: SpeechSettings};
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

export const SharedSystemVoice: Story = {render: () => ({
  components: {SpeechSettings},
  setup() {
    const info = speechFixture();
    info.engines.push({id:'macos:say',provider:'local',direction:'tts',label:'macOS voice',location:'On this Mac',model:'say',live:false,description:'Uses the system voice. All agents share one voice.',languages:'Depends on the selected macOS voice',state:'ready',detail:'Uses the installed macOS voice; no model download.',voices:[{id:'system',label:'macOS system voice'}],bindings:{lux:'system',rex:'system',luna:'system'}});
    info.active.tts = 'macos:say';
    setSpeechSettingsFixture(info);
  },
  template: '<div style="width:min(940px,100%);box-sizing:border-box;padding:24px"><SpeechSettings /></div>',
})};


export const UnsupportedLanguage: Story = {render: () => ({
  components: {SpeechSettings},
  setup() {
    const info=speechFixture();
    const engine=info.engines.find(e=>e.id==='kokoro:1')!;
    engine.state='unsupported';
    engine.detail='Kokoro currently supports English in this app. Keep your current engine for Polish.';
    setSpeechSettingsFixture(info);
  },
  template:'<div style="width:min(940px,100%);box-sizing:border-box;padding:24px"><SpeechSettings /></div>',
})};


export const RecoverSavedSettings: Story = {render: () => ({
  components:{SpeechSettings},
  setup() {
    setSpeechSettingsFixture(speechFixture(), Object.assign(new Error('Saved speech settings are unreadable or invalid. No fallback engine was selected.'), {recovery:{revision:'damaged-fixture',can_restore:true}}));
  },
  template:'<div style="width:min(940px,100%);box-sizing:border-box;padding:24px"><SpeechSettings /></div>',
})};
