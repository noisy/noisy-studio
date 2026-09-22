import { computed, nextTick, ref } from 'vue';
import type { Meta, StoryObj } from '@storybook/vue3';
import AudioControls from '../components/AudioControls.vue';
import { DEFAULT_AUDIO_CONTROLS } from '../components/audioControls';
import './audioControlOptions.css';

export default {title:'Lab/AudioControlOptions',parameters:{layout:'fullscreen'}} satisfies Meta;

export const ShortcutComparison: StoryObj = {
  render:()=>({components:{AudioControls},setup(){
    const selected=ref('');
    const versions=[{name:'Plain text',text:'More'},{name:'Ellipsis',text:'More…'},{name:'Diagonal arrow',text:'More ↗'},{name:'Right arrow',text:'More →'},{name:'Sliders',text:'More',icon:true}];
    return {versions,selected,visible:DEFAULT_AUDIO_CONTROLS};
  },template:`<main class="audio-options-lab"><h1>Audio controls · shortcut comparison</h1><p>Same panel, same destination: Settings → Audio. Only the shortcut changes.</p><div class="shortcut-board"><article v-for="v in versions" :key="v.name"><h2>{{v.name}}</h2><section class="shortcut-card"><AudioControls :status="null" :visible="visible" @open-settings="selected=v.name"><template #shortcut><span class="shortcut-label">{{v.text}}<svg v-if="v.icon" aria-hidden="true" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor"><path d="M2 4h12M2 12h12"/><circle cx="6" cy="4" r="2" fill="var(--panel-solid)"/><circle cx="10" cy="12" r="2" fill="var(--panel-solid)"/></svg></span></template></AudioControls></section></article></div><p role="status">{{selected ? selected + ' selected — this shortcut opens all audio controls.' : 'Click a shortcut to compare its target and feel.'}}</p><p>Recommendation: More → signals navigation within the app. More ↗ retains the earlier appearance.</p></main>`}),
};

export const ProviderAvailability:StoryObj={
  render:()=>({setup(){
    const engine=ref('grok');
    const picker=ref<HTMLSelectElement|null>(null);
    const modes=ref<Record<string,string>>({stt:'live',tts:'live'});
    const turn=ref('auto');
    const cases={
      grok:{name:'Grok',stt:'Grok recognition',tts:'Grok speech',live:true,smart:true,language:'Recognition detects speech language automatically; the language choice controls formatting. Speech has its own documented language list.',detail:'Some speech languages may work beyond the documented list, with varying accuracy.'},
      local:{name:'Whisper + Kokoro',stt:'Whisper base',tts:'Kokoro',live:false,smart:false,language:'Whisper base supports multiple recognition languages. This app’s Kokoro integration provides English speech.',detail:'For example, Polish recognition does not mean this speech engine can reply in Polish.'},
      english:{name:'English-only Whisper + macOS voice',stt:'Whisper base.en',tts:'macOS voice',live:false,smart:false,language:'Whisper base.en recognizes English. Speech language depends on the selected macOS voice.',detail:'The macOS adapter does not accept a language override. Unknown voice language support is not treated as universal support.'},
    };
    const active=computed(()=>cases[engine.value as keyof typeof cases]);
    async function changeEngine(){await nextTick();picker.value?.focus();picker.value?.scrollIntoView({block:'nearest'});}
    return {engine,picker,modes,turn,active,changeEngine};
  },template:`<main class="audio-options-lab"><h1>Audio controls · provider availability</h1><p>Interactive design only. Changing this example does not change your audio providers.</p><section class="availability-preview"><label class="example-picker">Example setup <select ref="picker" v-model="engine"><option value="grok">Grok</option><option value="local">Whisper + Kokoro</option><option value="english">English-only Whisper + macOS voice</option></select></label><h2>Audio controls</h2><p>Controls remain visible. Explanations and navigation stay readable when a control is unavailable.</p>
    <div class="availability-row"><div><h3>Language</h3><p>{{active.language}}</p><p>{{active.detail}}</p><p>Different providers and models may support additional languages. <button class="text-link" @click="changeEngine">Change speech or recognition engine →</button></p></div><select aria-label="Language (illustrative)" disabled><option>Current language retained</option></select></div>
    <p class="design-note">Language design question: the current app shares one language choice. This preview shows explanatory copy; a combined picker must not silently discard a saved value or treat unknown support as unsupported.</p>
    <div class="availability-row"><div><h3>Turn detection</h3><p>Auto and Push to talk are provided by Noisy Studio and remain available with every engine.</p></div><div class="option-pair"><button :aria-pressed="turn==='auto'" @click="turn='auto'">Auto</button><button :aria-pressed="turn==='ptt'" @click="turn='ptt'">Push to talk</button></div></div>
    <div v-for="direction in ['tts','stt']" :key="direction" class="availability-row"><div><h3>{{direction==='tts'?'Agent speech':'Your speech'}}</h3><p v-if="active.live">{{direction==='tts'?active.tts:active.stt}} supports Batch and Live.</p><p v-else>{{direction==='tts'?active.tts:active.stt}} generates complete results. Live is unavailable. <button class="text-link" @click="changeEngine">Change {{direction==='tts'?'speech':'recognition'}} engine →</button></p></div><div class="option-pair"><button :aria-pressed="!active.live || modes[direction]==='batch'" :disabled="!active.live" @click="modes[direction]='batch'">Batch</button><button :aria-pressed="active.live && modes[direction]==='live'" :disabled="!active.live" @click="modes[direction]='live'">Live</button></div></div>
    <div class="availability-row"><div><h3>Smart turn</h3><p v-if="!active.smart">Unavailable with {{active.stt}}. <button class="text-link" @click="changeEngine">Change recognition engine →</button></p><p v-else-if="turn==='ptt'">Used in Auto mode. Switch Turn detection to Auto to use Smart turn.</p><p v-else-if="modes.stt!=='live'">Requires Live recognition. Switch Your speech to Live to use Smart turn.</p><p v-else>Grok can detect when your thought is complete during a pause.</p></div><select aria-label="Smart turn" :disabled="!active.smart || turn==='ptt' || modes.stt!=='live'"><option>Off</option><option>0.5</option><option>0.7</option><option>0.9</option></select></div>
    </section></main>`}),
};
