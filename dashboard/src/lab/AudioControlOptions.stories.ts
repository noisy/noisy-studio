import { computed, nextTick, ref } from 'vue';
import type { Meta, StoryObj } from '@storybook/vue3';
import './audioControlOptions.css';
import { END_SILENCE_MS } from '../components/audioControls';

export default {title:'Lab/AudioControlOptions',parameters:{layout:'fullscreen'}} satisfies Meta;

export const ProviderAvailability:StoryObj={
  render:()=>({setup(){
    const engine=ref('grok');
    const picker=ref<HTMLSelectElement|null>(null);
    const modes=ref<Record<string,string>>({stt:'live',tts:'live'});
    const turn=ref('auto');
    const silence=ref(2000);
    const cases={
      grok:{name:'Grok',stt:'Grok recognition',tts:'Grok speech',live:true,smart:true,language:'Recognition detects speech language automatically; the language choice controls formatting. Speech has its own documented language list.',detail:'Some speech languages may work beyond the documented list, with varying accuracy.'},
      local:{name:'Whisper + Kokoro',stt:'Whisper base',tts:'Kokoro',live:false,smart:false,language:'Whisper base supports multiple recognition languages. This app’s Kokoro integration provides English speech.',detail:'For example, Polish recognition does not mean this speech engine can reply in Polish.'},
      english:{name:'English-only Whisper + macOS voice',stt:'Whisper base.en',tts:'macOS voice',live:false,smart:false,language:'Whisper base.en recognizes English. Speech language depends on the selected macOS voice.',detail:'The macOS adapter does not accept a language override. Unknown voice language support is not treated as universal support.'},
    };
    const active=computed(()=>cases[engine.value as keyof typeof cases]);
    async function changeEngine(){await nextTick();picker.value?.focus();picker.value?.scrollIntoView({block:'nearest'});}
    return {engine,picker,modes,turn,silence,silenceOptions:END_SILENCE_MS,active,changeEngine};
  },template:`<main class="audio-options-lab"><h1>Audio controls · provider availability</h1><p>Interactive design only. Changing this example does not change your audio providers.</p><section class="availability-preview"><label class="example-picker">Example setup <select ref="picker" v-model="engine"><option value="grok">Grok</option><option value="local">Whisper + Kokoro</option><option value="english">English-only Whisper + macOS voice</option></select></label><h2>Audio controls</h2><p>Controls remain visible. Explanations and navigation stay readable when a control is unavailable.</p>
    <div class="availability-row"><div><h3>Language</h3><p>Language support varies by model.</p><details class="language-details"><summary>Details</summary><div class="language-explanation"><p>{{active.language}}</p><p>{{active.detail}}</p><button class="text-link" @click="changeEngine">Change speech or recognition engine →</button></div></details></div><select aria-label="Language (illustrative)" disabled><option>Current language retained</option></select></div>
    <div class="availability-row"><div><h3>Turn detection</h3><p>Auto and Push to talk are provided by Noisy Studio and remain available with every engine.</p></div><div class="option-pair"><button :aria-pressed="turn==='auto'" @click="turn='auto'">Auto</button><button :aria-pressed="turn==='ptt'" @click="turn='ptt'">Push to talk</button></div></div>
    <div class="availability-row"><div><h3>End silence</h3><p :class="{ 'auto-warning': turn==='ptt' }">{{turn==='ptt' ? 'Applies only when Turn detection is Auto.' : 'Pause before ending an Auto turn.'}}</p></div><select aria-label="End silence" v-model="silence"><option v-for="ms in silenceOptions" :key="ms" :value="ms">{{ms/1000}}s</option></select></div>
    <div v-for="direction in ['tts','stt']" :key="direction" class="availability-row"><div><h3>{{direction==='tts'?'Agent speech':'Your speech'}}</h3><p v-if="active.live">{{direction==='tts'?active.tts:active.stt}} supports Batch and Live.</p><p v-else>{{direction==='tts'?active.tts:active.stt}} generates complete results. Live is unavailable. <button class="text-link" @click="changeEngine">Change {{direction==='tts'?'speech':'recognition'}} engine →</button></p></div><div class="option-pair"><button :aria-pressed="!active.live || modes[direction]==='batch'" :disabled="!active.live" @click="modes[direction]='batch'">Batch</button><button :aria-pressed="active.live && modes[direction]==='live'" :disabled="!active.live" @click="modes[direction]='live'">Live</button></div></div>
    <div class="availability-row"><div><h3>Smart turn</h3><p v-if="!active.smart">Unavailable with {{active.stt}}. <button class="text-link" @click="changeEngine">Change recognition engine →</button></p><p v-else-if="turn==='ptt'">Used in Auto mode. Switch Turn detection to Auto to use Smart turn.</p><p v-else-if="modes.stt!=='live'">Requires Live recognition. Switch Your speech to Live to use Smart turn.</p><p v-else>Grok can detect when your thought is complete during a pause.</p></div><select aria-label="Smart turn" :disabled="!active.smart || turn==='ptt' || modes.stt!=='live'"><option>Off</option><option>0.5</option><option>0.7</option><option>0.9</option></select></div>
    </section></main>`}),
};
