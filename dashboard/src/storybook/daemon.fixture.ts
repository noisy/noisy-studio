/** Storybook-only daemon. Never sends network requests or plays real audio. */
import type { Character, DaemonStatus, SettingsPatch, Utterance } from '../types';
import type { DiagnosticChecks, ProvidersInfo } from '../api/client';
export type Scenario = 'conversation' | 'recording' | 'speaking' | 'queued' | 'muted' | 'offline' | 'error' | 'empty' | 'setup' | 'shutdown' | 'long' | 'no-tabs' | 'local-speech';
let scenario: Scenario = 'conversation';
let status: DaemonStatus;
let messages: Utterance[] = [];
let character: Character;
let providers: ProvidersInfo | null;
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));
export function setProviderFixture(info: ProvidersInfo | null) { providers=clone(info); }
export function resetScenario(next: Scenario) {
  scenario = next;
  providers = {active:{tts:'grok',stt:'grok'},catalog:[{name:'grok',label:'Grok (xAI)',kind:'cloud-api',directions:['tts','stt'],streaming:{tts:true,stt:true},ready:true,fields:[]},{name:'local',label:'On this device',kind:'local',directions:['tts','stt'],streaming:{tts:false,stt:false},ready:true,fields:[]}]};
  const now = Date.now() / 1000;
  status = {
    listening:true, muted:next === 'muted', voice_muted:next === 'muted', api_key_set:next !== 'setup', voice_ready:next !== 'setup', api_key_hint:'demo-only',
    stt_latency_ms:410, tts_latency_ms:820, recording:next === 'recording', claude_speaking:next === 'speaking', playing_utterance_id:next === 'speaking' ? 4 : 0,
    speaking_agents:next === 'speaking' ? ['codex'] : [], queued:next === 'queued' ? 2 : 0,
    session_cost_usd:{user:.0214,claude:.1187}, usage:{stt_seconds:764,tts_chars:18432}, credits_usd:4.21,
    mode:'batch',tts_mode:'live',recognition_live_available:next !== 'local-speech',speech_live_available:next !== 'local-speech',recognition_mode:next === 'local-speech' ? 'batch' : undefined,speech_output_mode:next === 'local-speech' ? 'batch' : undefined,end_silence_ms:1500,mic_sensitivity:50,smart_turn:.7,smart_turn_mode:'soft',detection_mode:'ptt',ptt_held:false,
    input_device:'',output_device:'system',browser_audio:false,tab_audio:false,hotkeys:{configured:true,permission:'granted',armed:true,bindings:{hold:'F8',toggle:'F15',scratch:'escape',tab1:'F1',tab2:'F2'},stored:{hold:'F8',toggle:'F15',scratch:'escape',tab1:'F1',tab2:'F2'},problems:{}},activity:{},language:'en',
    agents:next === 'no-tabs' ? {} : {codex:1,claude:2,docs:3}, agent_labels:next === 'no-tabs' ? {} : {codex:next === 'long' ? 'codex / investigate-checkout-performance-and-retry-handling' : 'Codex',claude:'Code review',docs:'Documentation'},
    agent_voices:{codex:'lux',claude:'eve',docs:'rex'},active_agent:next === 'no-tabs' ? null : 'codex',muted_agents:[], queued_by_agent:{claude:2},
    version:'2.17.0',latest_version:'2.17.0', shutdown_at:next === 'shutdown' ? now+180 : undefined,
    agents_meta:next === 'no-tabs' ? {} : {codex:{label:'Codex',online:true,activated_at:1,offline_since:null},claude:{label:'Code review',online:true,activated_at:2,offline_since:null},docs:{label:'Documentation',online:false,activated_at:3,offline_since:now-60}}
  };
  if(next === 'long') status.agents_meta!.codex.label=status.agent_labels.codex;
  character={humor:40,honesty:100,brevity:80,chatty:40,voice:'lux',speed:1.1};
  const texts=[
    'How is the payment retries work going?',
    'The backoff logic is ready. I found one edge case: queued events could disappear during a redeploy. I’m checking that path now.',
    'Keep those events in the queue, and add a test for the redeploy case.',
    'Done. Events now survive a redeploy, and the new test covers the retry path. The dashboard also shows how many events are waiting.'
  ];
  if(next === 'long') texts[3] = ('The event remains queued until the consumer confirms delivery. '+ 'https://example.test/reports/'+ 'long-path-without-breaks-'.repeat(12)+'\n').repeat(8);
  messages=next === 'empty' || next === 'setup' || next === 'no-tabs' ? [] : texts.map((text,i)=>({id:i+1,role:i%2 ? 'claude' : 'user',text,status:i%2 ? 'played' : 'delivered to Codex',voice:i%2 ? 'lux' : undefined,detail:i%2 ? 'Speech · 0.8s' : 'Transcribed · 0.4s',cost_usd:.001,agent:'codex',started_at:now-180+i*30,updated_at:now-180+i*30,committed_at:now-180+i*30}));
  if(next === 'recording') messages.push({id:5,role:'user',text:'Great. Next, let’s look at the slow dashboard query…',status:'recording...',detail:'Capturing your voice',cost_usd:0,agent:'codex',started_at:now,updated_at:now,committed_at:0});
  if(next === 'speaking') messages[3].status='speaking...';
  if(next === 'queued' || next === 'muted') messages.filter(m=>m.role==='claude').forEach(m=>m.status='unheard');
  localStorage.setItem('noisy-coding.audio-cues', JSON.stringify({enabled:false,recordingHum:false,cues:{}}));
}
export async function getStatus() { if(scenario==='offline') throw new Error('Simulated offline'); return clone(status); }
// Browser previews cannot request native macOS permissions.
export async function requestHotkeyPermission() { return clone(status.hotkeys); }
export async function getUtterances() { return clone(messages); }
export async function getCharacter() { return clone(character); }
export async function getEvents(sinceSeq=0) { return scenario==='error' && sinceSeq < 1 ? [{seq:1,ts:Date.now()/1000,kind:'tts_error',detail:'Voice service unavailable. Retry playback when the connection returns.'}] : []; }
export async function setMuted(muted:boolean) { status.muted=muted; }
export async function setVoiceMuted(muted:boolean) { status.voice_muted=muted; }
export async function setMode(mode:'batch'|'live') { status.mode=mode; }
export async function setSettings(patch:SettingsPatch) { Object.assign(status,patch); }
export async function setCharacter(patch:Partial<Character>) { Object.assign(character,patch); }
export async function setAgentMuted(agent:string,muted:boolean) { status.muted_agents=muted ? [...status.muted_agents!,agent] : status.muted_agents!.filter(a=>a!==agent); }
export async function setActiveAgent(name:string) { status.active_agent=name; }
export async function dismissAgent(name:string) { delete status.agents[name]; delete status.agent_labels[name]; }
export async function reorderAgents(names:string[]) { names.forEach((name,i)=>{status.agents_meta![name].manual_pos=i;}); }
export async function setPtt(held:boolean) { status.ptt_held=held; status.recording=held; }
export async function cancelTranscript(id:number) { messages=messages.filter(m=>m.id!==id); }
export async function speakText(_text:string,id:number) { status.playing_utterance_id=id; status.claude_speaking=true; status.speaking_agents=['codex']; }
export async function stopPlayback() { status.playing_utterance_id=0; status.claude_speaking=false; status.speaking_agents=[]; }
export const interruptPlayback=stopPlayback;
let paused=false;
export async function togglePlaybackPause() { paused=!paused; return {paused}; }
export async function skipUnheard() { messages.filter(m=>m.status==='unheard').forEach(m=>m.status='played'); return {skipped:2}; }
export async function scheduleShutdown(seconds=300) { status.shutdown_at=Date.now()/1000+seconds; return {shutdown_at:status.shutdown_at}; }
export async function cancelShutdown() { status.shutdown_at=0; }
export async function postponeShutdown(seconds=60) { status.shutdown_at=(status.shutdown_at || Date.now()/1000)+seconds; }
export async function getDevices() { return [{name:'Studio microphone',default:true},{name:'USB audio interface with a very long descriptive device name',default:false}]; }
const checks:DiagnosticChecks={credentials:{ok:true,ms:80},stt:{ok:true,ms:410},tts:{ok:true,ms:820}};
export async function runDiagnostics() { return clone(checks); }
export async function saveApiKey() { status.api_key_set=true;status.voice_ready=true;return {ok:true,checks:clone(checks)}; }
export async function getProviders():Promise<ProvidersInfo> { if(!providers) throw new Error('Simulated unavailable providers endpoint'); return clone(providers); }
export async function setProviders(patch:{tts?:string;stt?:string;prefetch?:boolean}) {
  if(!providers) throw new Error('Simulated unavailable providers endpoint');
  if ((patch.tts === 'local' || patch.stt === 'local') && providers.downloads?.some(d => d.state !== 'done')) throw new Error('{"error":"Preparing local models. Your current engines remain active; apply again after the download finishes."}');
  if(patch.tts) providers.active.tts=patch.tts;
  if(patch.stt) providers.active.stt=patch.stt;
  if(providers.active.tts==='local') status.voice_ready=true;
  return clone(providers.active);
}
resetScenario('conversation');

import type { SpeechSettingsInfo, SpeechSettingsPatch } from '../api/client';
import { speechFixture } from '../components/speechSettings.fixture';
let speechSettings = speechFixture();
let speechSettingsError: Error | undefined;
export function setSpeechSettingsFixture(value: SpeechSettingsInfo, error?: Error) { speechSettings = clone(value); speechSettingsError=error; }
export async function getSpeechSettings() { if(speechSettingsError) throw speechSettingsError; return clone(speechSettings); }
export async function updateSpeechSettings(patch: SpeechSettingsPatch) {
  const engine = speechSettings.engines.find(e => e.id === patch.choice)!;
  if (patch.operation === 'prepare') { engine.state = 'ready'; engine.detail = 'Model files are on this Mac.'; }
  else { speechSettings.active[engine.direction] = engine.id; engine.bindings = {...patch.bindings}; }
  return clone(speechSettings);
}
export async function previewSpeechVoice() { throw new Error('Storybook has no live provider account. Voice preview errors are shown inline.'); }
export async function previewRecognition() {return {text:'The search should ignore capital letters.',elapsed_ms:640};}

export async function restoreSpeechSettings(_revision:string) { speechSettingsError=undefined; status.voice_ready=true; return getSpeechSettings(); }
