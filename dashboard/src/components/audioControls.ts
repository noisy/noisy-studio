import type { DaemonStatus, InputDevice } from '../types';
export const AUDIO_PANEL_WIDTH = 268;
export const AUDIO_CONTROL_IDS = ['microphone', 'language', 'turn', 'agent', 'recognition', 'cues', 'length', 'silence', 'sensitivity', 'smart'] as const;
export type AudioControlId = typeof AUDIO_CONTROL_IDS[number];
export type AudioChange = { id: AudioControlId; value: string };
export const DEFAULT_AUDIO_CONTROLS: AudioControlId[] = ['microphone', 'language', 'turn'];
export const END_SILENCE_MS = [0, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000];
const languages = { '': 'Auto-detect', en: 'English', pl: 'Polski', de: 'Deutsch', es: 'Español', fr: 'Français', 'pt-BR': 'Português (BR)', it: 'Italiano', ja: '日本語', zh: '中文' };
const choices = (values: Record<string, string>) => Object.entries(values).map(([value, label]) => ({value, label, disabled: false}));
export function audioControls(status: DaemonStatus | null, devices: InputDevice[], cues: boolean) {
  const s = status;
  const modes = (live: boolean | undefined) => [{value:'batch',label:'Batch',disabled:false},{value:'live',label:'Live',disabled:live === false}];
  const microphones = devices.map(d => ({ value: d.value ?? d.name, label: d.name, disabled:false }));
  if (s?.input_device && !microphones.some(d => d.value === s.input_device)) microphones.unshift({value:s.input_device,label:s.input_device,disabled:false});
  return [
    {id:'microphone',label:'Microphone',help:'Choose the input device. The list refreshes when opened.',value:s?.input_device ?? '',options:[...choices({'':'System default'}),...microphones]},
    {id:'language',label:'Language',help:'Language used for recognition and synthesis.',value:s?.language ?? '',options:choices(languages)},
    {id:'turn',label:'Turn detection',help:'Speak naturally or hold a button to talk.',value:s?.detection_mode ?? 'auto',options:choices({auto:'Auto',ptt:'Push to talk'}),buttons:true},
    {id:'agent',label:'Agent speech',help:'Play the complete reply or stream audio as it arrives.',value:s?.speech_output_mode ?? s?.tts_mode ?? 'batch',options:modes(s?.speech_live_available),buttons:true},
    {id:'recognition',label:'Your speech',help:'Transcribe after your turn or while you speak.',value:s?.recognition_mode ?? s?.mode ?? 'batch',options:modes(s?.recognition_live_available),buttons:true},
    {id:'cues',label:'Sound cues',help:'Play short sounds for conversation events.',value:cues ? 'on':'off',options:choices({on:'On',off:'Off'}),buttons:true},
    {id:'length',label:'Maximum voice message length',help:'Finish and send a recording at this limit, in Auto or Push to talk mode.',value:String(s?.max_utterance_ms ?? 600000),options:[1,3,5,10,15,30,60].map(minutes=>({value:String(minutes*60000),label:`${minutes} min`,disabled:false}))},
    {id:'silence',label:'End silence',help:'Pause before ending an Auto turn. Zero closes at the first detected pause.',value:String(s?.end_silence_ms ?? 2000),options:END_SILENCE_MS.map(ms=>({value:String(ms),label:`${ms/1000}s`,disabled:false})),notice:s?.detection_mode === 'ptt' ? 'Applies only when Turn detection is Auto.' : ''},
    {id:'sensitivity',label:'Sensitivity',help:'Lower values require a clearer voice in noisy rooms.',value:String(s?.mic_sensitivity ?? 50),options:choices({0:'Min',25:'Low',50:'Mid',75:'High',100:'Max'})},
    {id:'smart',label:'Smart turn',help:'Allow the recognition engine to detect a completed turn in Auto mode.',value:String(s?.smart_turn ?? 0),options:choices({0:'Off','0.5':'0.5','0.7':'0.7','0.9':'0.9'}),disabled:s?.detection_mode === 'ptt'},
  ].map(c=>({...c,id:c.id as AudioControlId}));
}
