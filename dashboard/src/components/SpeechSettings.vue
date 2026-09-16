<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { getSpeechSettings, updateSpeechSettings, previewSpeechVoice, previewRecognition, getStatus, setMuted, type SpeechSettingsInfo, type SpeechEngine } from '../api/client';

import ModelDownloadProgress from './ModelDownloadProgress.vue';
import { useSpeechSample } from '../composables/useSpeechSample';

const emit = defineEmits<{configure: []}>();
const root = ref<HTMLElement>();
const info = ref<SpeechSettingsInfo>();
const editing = ref<'stt' | 'tts' | null>(null);
const selected = ref('');
const draftRevision = ref('');
const bindings = ref<Record<string, string>>({});
const busy = ref(false);
const error = ref('');
const notice = ref('');
const transcript = ref('');
const needsMicPause = ref(false);
async function pauseMainMic() { try { await setMuted(true); needsMicPause.value=false; notice.value='Main microphone paused. Resume it from the dashboard when you finish testing.'; } catch { error.value='Could not pause the main microphone. Check the connection.'; } }
async function sampleAllowed() { const status=await getStatus(); needsMicPause.value=!status.muted; return status.muted; }
const sample = useSpeechSample(async wav => {
  const choice = selected.value; busy.value = true;
  try { const result = await previewRecognition(choice, wav); if(selected.value===choice) transcript.value = result.text || 'No speech recognized. Try again.'; }
  catch { error.value = 'Recognition test failed. Check the microphone and provider connection.'; }
  finally { busy.value=false; }
});
async function recordSample() { stop(); transcript.value=''; try { if(await sampleAllowed()) await sample.start(); } catch { error.value='Microphone access is unavailable. Check browser permissions.'; } }
const playing = ref('');
const loadingSample = ref(false);
let audio: HTMLAudioElement | undefined;
let previewRequest = 0;
let poll: ReturnType<typeof setInterval>;
const sections = [{id: 'stt', title: 'Your speech', intro: 'How your words become text.'}, {id: 'tts', title: 'Agent voices', intro: 'How your agents sound.'}] as const;
const candidate = computed(() => info.value?.engines.find(e => e.id === selected.value));
const shared = computed(() => Object.values(bindings.value).length > new Set(Object.values(bindings.value)).size);
function active(direction: 'tts' | 'stt') { return info.value?.engines.find(e => e.id === info.value?.active[direction]); }
function stop() { previewRequest++; audio?.pause(); audio = undefined; playing.value = ''; loadingSample.value = false; }
function choose(engine: SpeechEngine) { sample.cancel(); transcript.value=''; stop(); selected.value = engine.id; bindings.value = {...engine.bindings}; error.value = ''; }
async function edit(direction: 'stt' | 'tts') {
  editing.value = direction; draftRevision.value=info.value?.revision ?? ''; notice.value = ''; error.value = '';
  const engine = active(direction) ?? info.value?.engines.find(e => e.direction === direction);
  if (engine) choose(engine);
  await nextTick(); root.value?.querySelector<HTMLElement>('.details h3')?.focus();
}
async function cancel() { const previous = editing.value; sample.cancel(); stop(); editing.value = null; error.value = ''; await nextTick(); root.value?.querySelector<HTMLButtonElement>(`[data-change="${previous}"]`)?.focus(); }
async function reload() {
  try { info.value = await getSpeechSettings(); }
  catch { error.value = 'Could not load speech settings. Check the connection and retry.'; }
}
async function save(operation: 'prepare' | 'apply') {
  if (!info.value || !candidate.value) return;
  busy.value = true; error.value = ''; stop();
  try {
    info.value = await updateSpeechSettings({operation, choice: selected.value, revision: draftRevision.value, bindings: bindings.value});
    if (operation === 'apply') { const direction = editing.value; cancel(); notice.value = direction === 'tts' ? 'Updated. New speech uses this choice; audio already prepared keeps its original voice.' : 'Updated. Your next recording uses this recognition engine.'; }
  } catch (e) { error.value = e instanceof Error ? e.message : 'Could not update speech settings.'; }
  finally { busy.value = false; }
}
async function preview(engine: SpeechEngine, voice: string, identity: string) {
  stop(); const request = previewRequest; playing.value = identity; loadingSample.value = true; error.value = '';
  try {
    if (!(await sampleAllowed())) { playing.value=''; loadingSample.value=false; return; }
    if (request !== previewRequest) return;
    const clip = await previewSpeechVoice(engine.id, voice);
    if (request !== previewRequest) return;
    audio = new Audio(`data:${clip.content_type};base64,${clip.audio}`);
    audio.onended = () => { playing.value = ''; };
    await audio.play(); loadingSample.value = false;
  } catch { if (request === previewRequest) { error.value = 'Could not play this voice. Check the provider connection and try again.'; playing.value = ''; } }
}
onMounted(() => { void reload(); poll = setInterval(() => { if (!busy.value) void reload(); }, 1500); });
onUnmounted(() => { clearInterval(poll); stop(); });
</script>

<template>
  <div ref="root" class="speech-settings">
    <header><h2>Speech</h2><p>Choose how you speak to your agents and how they reply.</p></header>
    <p v-if="error && !editing" class="feedback error" role="alert">{{ error }} <button v-if="!info" @click="reload">Retry</button></p>
    <p v-if="notice" class="feedback" role="status">{{ notice }}</p>
    <p v-if="!info && !error">Loading speech engines…</p>
    <ModelDownloadProgress :downloads="info?.downloads.filter(d => d.state !== 'missing') ?? []" />
    <section v-for="section in sections" v-show="info" :key="section.id" class="speech-card" :class="{editing: editing === section.id}">
      <div class="summary">
        <div><span class="eyebrow">{{ section.title }}</span><p>{{ section.intro }}</p>
          <h3>{{ active(section.id)?.label ?? 'Current engine' }} <span class="location">{{ active(section.id)?.location }}</span></h3>
          <p>{{ active(section.id)?.live ? (section.id === 'stt' ? 'Text appears while you speak.' : 'Replies begin playing as audio arrives.') : (section.id === 'stt' ? 'Text appears after you finish speaking.' : 'The full reply is generated before playback.') }}</p>
        </div>
        <button v-if="editing !== section.id" :data-change="section.id" class="change" :disabled="busy" @click="edit(section.id)">Change</button>
      </div>
      <div v-if="editing === section.id" class="editor">
        <div class="choices" role="group" :aria-label="section.title + ' engine'">
          <button v-for="engine in info?.engines.filter(e => e.direction === section.id)" :key="engine.id" class="choice" :aria-pressed="selected === engine.id" :class="{selected: selected === engine.id}" :disabled="busy" @click="choose(engine)">
            <span class="choice-heading">{{ engine.label }} <span>{{ engine.location }}</span></span>
            <small>{{ engine.description }}</small><span class="choice-status">{{ engine.state === 'ready' ? 'Available' : engine.state === 'setup' ? 'Setup needed' : engine.state === 'downloading' ? 'Preparing…' : engine.state === 'error' ? 'Retry download' : 'Download needed' }}</span>
          </button>
        </div>
        <div v-if="candidate" class="details">
          <span class="eyebrow">{{ candidate.label }}</span>
          <h3 tabindex="-1">{{ candidate.live ? (section.id === 'stt' ? 'Follow your words live' : 'Hear replies sooner') : (section.id === 'stt' ? 'Speak, then see your text' : 'Generate, then play') }}</h3>
          <p>{{ candidate.languages }}</p>
          <p>{{ candidate.detail }}</p>
          <p v-if="candidate.state === 'downloading'" role="status">Downloading model files… Your current engine stays active.</p>
          <template v-if="section.id === 'tts'">
            <h4>Review your voices</h4><p>Review current → new voices. Switching back restores your saved voices.</p>
            <div class="voice-rows">
              <div v-for="(_voice, identity) in bindings" :key="identity" class="voice-row"><label :for="`speech-voice-${identity}`">{{ identity }}<small>{{ active('tts')?.voices.find(v => v.id === active('tts')?.bindings[identity])?.label ?? identity }} →</small></label>
                <select :id="`speech-voice-${identity}`" v-model="bindings[identity]" @change="stop" :aria-label="'Voice for ' + identity" :disabled="busy"><option v-for="voice in candidate.voices" :key="voice.id" :value="voice.id">{{ voice.label }}</option></select>
                <button :disabled="candidate.state !== 'ready' || busy" :aria-label="'Listen to voice for ' + identity" @click.prevent="playing === identity ? stop() : preview(candidate, bindings[identity]!, identity)">{{ playing === identity ? (loadingSample ? 'Loading…' : 'Stop') : 'Listen' }}</button>
              </div>
            </div>
            <p v-if="shared" class="warning">Some speakers share a voice. Choose different voices where available.</p>
            <small>Samples use this engine, in English, at normal speed. Online samples use your provider account.</small>
          </template>
          <p v-else class="behavior-note">{{ candidate.live ? 'You can watch the transcript develop while speaking.' : 'Live transcription is unavailable with this engine. Your words are processed when you finish.' }} Changing recognition does not change agent voices.</p>
          <div v-if="section.id === 'stt'" class="sample-test">
            <button :disabled="busy || candidate.state !== 'ready'" @click="sample.recording.value ? sample.finish() : recordSample()">{{ sample.recording.value ? 'Stop and transcribe' : busy ? 'Transcribing…' : 'Try my microphone' }}</button>
            <p>Up to 15 seconds. This comparison test returns text after recording; it does not send a message to your agent.</p>
            <p v-if="candidate.location === 'Online'">This sample is sent to {{ candidate.label }} using your account.</p>
            <p v-if="sample.error.value" class="error" role="alert">{{ sample.error.value }}</p>
            <p v-if="transcript" role="status">{{ transcript }}</p>
          </div>
          <div v-if="needsMicPause" class="feedback"><p>Pause the main microphone so samples cannot become messages in your conversation.</p><button @click="pauseMainMic">Pause main microphone</button></div>
          <p v-if="error" class="error" role="alert">{{ error }} <button @click="cancel(); reload()">Refresh settings</button></p>
          <p class="apply-note">{{ section.id === 'tts' ? 'Applies to new speech. Already prepared replies keep their original voice.' : 'Applies to your next recording. Your current conversation is unchanged.' }}</p>
          <button v-if="candidate.state === 'setup'" @click="emit('configure')">Open System settings</button>
          <footer>
            <button :disabled="busy" @click="cancel">Cancel</button>
            <button v-if="candidate.state === 'download' || candidate.state === 'error'" class="primary" :disabled="busy" @click="save('prepare')">{{ busy ? 'Preparing…' : candidate.state === 'error' ? 'Retry download' : 'Download model' }}</button>
            <button v-else class="primary" :disabled="busy || candidate.state !== 'ready'" @click="save('apply')">{{ busy ? 'Applying…' : section.id === 'stt' ? 'Use for my speech' : 'Use for agent voices' }}</button>
          </footer>
        </div>
      </div>
    </section>
    <p class="footnote">Online engines send audio or text to their provider. Local engines process it on your Mac after the initial download.</p>
  </div>
</template>

<style scoped>
.speech-settings{container-type:inline-size;display:grid;gap:16px;max-width:1000px;color:var(--ink);font-family:var(--sans)}
h2,h3,h4,p{margin:0}h2{font-size:24px}h3{font-size:19px;line-height:1.5}h4{font-size:14px}p{font-size:13px;line-height:1.55;color:var(--muted)}header p{margin-top:6px}
.speech-card{background:var(--bg1);border:1px solid var(--line-strong);border-radius:14px;padding:18px}.summary{display:flex;align-items:center;justify-content:space-between;gap:20px}.summary p{margin:5px 0}.eyebrow{font-size:12px;font-weight:650;color:var(--brand-accent)}.location{font-size:11px;color:var(--muted);font-weight:400;margin-left:8px}
button,select{font:inherit;color:var(--ink);background:var(--bg0);border:1px solid var(--line-strong);border-radius:7px;padding:8px 12px;font-size:12px}button{cursor:pointer}button:hover:not(:disabled){border-color:var(--brand-accent)}button:focus-visible,select:focus-visible{outline:2px solid var(--brand-accent);outline-offset:3px}button:disabled{opacity:.5;cursor:default}.change{flex:none}.editor{display:grid;grid-template-columns:minmax(220px, .85fr) minmax(0,1.15fr);gap:24px;margin-top:20px;padding-top:20px;border-top:1px solid var(--line-strong)}.choices{display:flex;flex-direction:column;gap:8px;max-height:320px;overflow:auto;padding:3px}.choice{text-align:left;padding:10px;display:grid;gap:4px}.choice.selected{border-color:var(--brand-accent);background:color-mix(in srgb,var(--brand-accent) 8%,var(--bg1))}.choice-heading{display:flex;justify-content:space-between;gap:10px;font-weight:600}.choice-heading span{font-size:10px;font-weight:400;color:var(--muted)}small{font-size:11px;line-height:1.5;color:var(--muted)}.choice-status{font-size:10px;color:var(--brand-accent)}.details{display:flex;flex-direction:column;gap:10px;min-width:0}.voice-rows{display:grid;gap:8px;padding:3px}.voice-row{display:grid;grid-template-columns:70px minmax(0,1fr) 62px;gap:7px;align-items:center;font-size:12px}.voice-row>label{text-transform:capitalize}.voice-row label small{display:block;text-transform:none;font-size:10px}.apply-note{font-size:11px}.voice-row select{min-width:0;width:100%}.voice-row button{padding:8px 4px}footer{display:flex;justify-content:flex-end;gap:8px;margin-top:auto;padding-top:14px}.primary{background:var(--brand-accent);color:var(--bg0);font-weight:650}.feedback{padding:12px;border-radius:8px;background:var(--bg1)}.error,.warning{color:var(--amber)}.behavior-note{border-left:2px solid var(--brand-accent);padding-left:12px;margin:8px 0}.footnote{font-size:11px}
@container(max-width:650px){.editor{grid-template-columns:1fr}.speech-card{padding:16px}.choices{max-height:230px}.summary{gap:8px}.voice-row{grid-template-columns:60px minmax(0,1fr) 55px}}
</style>
