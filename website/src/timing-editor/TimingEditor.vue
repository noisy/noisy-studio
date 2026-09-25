<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
import RecordedHeroScene from '@dashboard/components/marketing/RecordedHeroScene.vue';
import take from '../assets/todd/hero.json';
import recording from '../assets/todd/hero.mp4';
import poster from '../assets/todd/hero-poster.jpg';
import savedEdits from '../assets/todd/hero-presentation-edits.json';
import { toddCamera } from '../toddCamera';
import { CONSOLE_ACTIVITIES, activityWindows, idleWindows, type ActivityBlock, userTurns, validatePresentation, type ActivityKind, type PresentationEdits } from '@dashboard/components/marketing/presentationTiming';
const sourceSha256 = savedEdits.sourceSha256;
const cacheKey = `demo-presentation:${sourceSha256}`;
const edits = ref<PresentationEdits>(validatePresentation(structuredClone(savedEdits), take, sourceSha256));
const turns = userTurns(take);
const selected = ref('u1');
const current = computed(() => turns.find(turn => turn.utterance === selected.value)!);
const edit = computed(() => edits.value.turns.find(edit => edit.utterance === selected.value) ?? { utterance: selected.value, userEndMs: Math.floor(current.value.endMs), status: 'none' as ActivityKind });
const time = ref(0), playing = ref(false), dirty = ref(false), error = ref(''), notice = ref('Changes affect presentation only. Video and Lux keep their original timing.');
const scene = shallowRef<InstanceType<typeof RecordedHeroScene>>();
const frame = ref<HTMLElement>(); const scale = ref(.5); let observer: ResizeObserver;
let stopAt: number | null = null;
const duration = take.durationMs;
const replies = take.events.filter(event => event.type === 'agent-start').map(event => ({start: event.atMs, end: take.events.find(end => end.type === 'agent-end' && end.clip === event.clip && end.atMs > event.atMs)?.atMs ?? event.atMs, text: event.text}));
const position = (start: number, end: number) => ({left: `${start / duration * 100}%`, width: `${(end - start) / duration * 100}%`});
const turnStart = (id: string, fallback: number) => edits.value.turns.find(edit => edit.utterance === id)?.userStartMs ?? fallback;
const turnEnd = (id: string, fallback: number) => edits.value.turns.find(edit => edit.utterance === id)?.userEndMs ?? fallback;
const workWindows = computed(() => activityWindows(take, edits.value.turns, edits.value.activities ?? []));
const blockDraft = ref<ActivityBlock>({id: '', startMs: 0, endMs: 0, status: 'thinking', consoleTask: 'u1'});
function newBlock(at = time.value) {
  const gap = idleWindows(take, edits.value.turns).find(gap => gap.endMs > at && Math.floor(gap.endMs) > Math.ceil(Math.max(at, gap.startMs)));
  if (!gap) {error.value = 'No available pause here. Trim the beginning or end of a user turn first.'; return;}
  const next = turns.find(turn => turnStart(turn.utterance, turn.startMs) >= gap.endMs - 1);
  blockDraft.value = {id: '', startMs: Math.ceil(Math.max(at, gap.startMs)), endMs: Math.floor(gap.endMs), status: 'thinking', consoleTask: next && CONSOLE_ACTIVITIES[next.utterance] ? next.utterance : 'u4'};
  error.value = '';
}
function saveBlock() {
  try {
    const block = {...blockDraft.value, id: blockDraft.value.id || crypto.randomUUID()};
    edits.value = validatePresentation({...edits.value, activities: [...(edits.value.activities ?? []).filter(item => item.id !== block.id), block]}, take, sourceSha256);
    blockDraft.value = block; dirty.value = true; saveDraft(); error.value = ''; notice.value = 'Activity block saved in the preview. Export JSON when finished.';
  } catch (exception) {error.value = (exception as Error).message;}
}
function removeBlock(id: string) {edits.value = {...edits.value, activities: (edits.value.activities ?? []).filter(block => block.id !== id)}; dirty.value = true; saveDraft(); blockDraft.value.id = '';}
function editBlock(block: ActivityBlock) {blockDraft.value = {...block}; seek(block.startMs);}

function saveDraft() { try { localStorage.setItem(cacheKey, JSON.stringify(edits.value)); } catch { /* JSON download remains available. */ } }
function update(end = edit.value.userEndMs, status = edit.value.status, start = edit.value.userStartMs) {
  try {
    const next = {...edits.value, turns: [...edits.value.turns.filter(edit => edit.utterance !== selected.value), {utterance: selected.value, userStartMs: start, userEndMs: end, status}]};
    edits.value = validatePresentation(next, take, sourceSha256); dirty.value = true; error.value = ''; saveDraft();
    notice.value = 'Preview updated. Save the timing JSON when you are happy with it.';
  } catch (exception) { error.value = (exception as Error).message; }
}
const startChanged = (event: Event) => update(edit.value.userEndMs, edit.value.status, Number((event.target as HTMLInputElement).value));
const endChanged = (event: Event) => update(Number((event.target as HTMLInputElement).value));
const statusChanged = (event: Event) => update(edit.value.userEndMs, (event.target as HTMLSelectElement).value as ActivityKind);
function seek(ms: number) { scene.value?.pause(); playing.value = false; stopAt = null; time.value = ms; scene.value?.seek(ms); }
function onTime(ms: number) {
  time.value = ms;
  if (playing.value && (ms >= (stopAt ?? duration) || ms >= duration)) { scene.value?.pause(); playing.value = false; stopAt = null; }
}
function togglePlay() {
  if (playing.value) { scene.value?.pause(); playing.value = false; stopAt = null; }
  else { if (time.value >= duration) scene.value?.seek(0); void scene.value?.play(); playing.value = true; }
}
function previewTurn() { seek(Math.max(0, current.value.startMs - 300)); stopAt = current.value.previewEndMs; void scene.value?.play(); playing.value = true; }
function resetTurn() { try { edits.value = validatePresentation({...edits.value, turns: edits.value.turns.filter(edit => edit.utterance !== selected.value)}, take, sourceSha256); dirty.value = true; saveDraft(); error.value = ''; } catch(exception) { error.value = (exception as Error).message; } }
function download() {
  const url = URL.createObjectURL(new Blob([JSON.stringify(edits.value, null, 2)], {type: 'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'todd-hero.presentation-edits.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);
  dirty.value = false; notice.value = 'Timing JSON saved. Keep it with the original hero recording.';
}
async function reopen(event: Event) {
  const input = event.target as HTMLInputElement; const file = input.files?.[0]; input.value = ''; if (!file) return;
  try { const next = validatePresentation(JSON.parse(await file.text()), take, sourceSha256);
    if (dirty.value && !confirm('Replace unsaved timing edits?')) return;
    edits.value = next; saveDraft(); dirty.value = false; error.value = ''; notice.value = 'Timing edits reopened.';
  } catch (exception) { error.value = (exception as Error).message; }
}
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value) {event.preventDefault(); event.returnValue = '';} }
onMounted(() => {
  try { const draft = localStorage.getItem(cacheKey); if (draft) {edits.value = validatePresentation(JSON.parse(draft), take, sourceSha256); dirty.value = true; notice.value = 'Restored your local timing draft.';} } catch { /* Ignore invalid drafts. */ }
  observer = new ResizeObserver(() => {scale.value = (frame.value?.clientWidth ?? 600) / 1200;});
  if (frame.value) observer.observe(frame.value);
  window.addEventListener('beforeunload', beforeUnload);
});
onBeforeUnmount(() => {observer?.disconnect(); window.removeEventListener('beforeunload', beforeUnload);});
</script>
<template>
  <main>
    <header><div><small>DEMO STUDIO / TODD HERO TIMING</small><h1>Give the agent time to think.</h1></div><a href="/demo-studio/">← Demo Studio</a></header>
    <div class="toolbar"><button @click="togglePlay">{{ playing ? 'Pause' : 'Play with sound' }}</button><button @click="previewTurn">Play selected turn</button><button @click="download">Save timing JSON</button><label class="file-button">Reopen timing JSON<input type="file" accept=".json" @change="reopen"></label><span>{{ Math.round(time) }} / {{ Math.round(duration) }} ms</span></div>
    <p role="status">{{ notice }}</p><p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="workspace">
      <div ref="frame" class="preview" :style="{height: `${760 * scale}px`}"><RecordedHeroScene ref="scene" :recording-src="recording" :recording-poster="poster" :recording-take="take" v-bind="toddCamera" manual-playback :presentation-edits="edits.turns" :activity-blocks="edits.activities ?? []" :style="{transform: `scale(${scale})`, transformOrigin: 'top left'}" @time="onTime" /></div>
      <section class="controls"><nav aria-label="Choose user turn"><button v-for="(turn, i) in turns" :key="turn.utterance" :aria-pressed="selected === turn.utterance" @click="selected = turn.utterance">{{ i + 1 }}</button></nav>
        <p class="quote">“{{ current.text }}”</p>
        <label>Start of “you are speaking”<input type="range" :min="Math.ceil(current.startMs)" :max="edit.userEndMs - 1" step="1" :value="edit.userStartMs ?? Math.ceil(current.startMs)" @input="startChanged"></label>
        <div class="end-time"><input aria-label="User speaking start in milliseconds" type="number" :min="Math.ceil(current.startMs)" :max="edit.userEndMs - 1" step="1" :value="edit.userStartMs ?? Math.ceil(current.startMs)" @input="startChanged"><span>ms</span><button @click="update(edit.userEndMs, edit.status, Math.round(time))">Start at playhead</button></div>
        <label>End of “you are speaking”<input type="range" :min="Math.ceil(current.startMs)" :max="Math.floor(current.endMs)" step="1" :value="edit.userEndMs" @input="endChanged"></label>
        <div class="end-time"><input aria-label="User speaking end in milliseconds" type="number" :min="Math.ceil(current.startMs)" :max="Math.floor(current.endMs)" step="1" :value="edit.userEndMs" @input="endChanged"><span>ms</span><button @click="update(Math.round(time))">Use playhead</button></div>
        <p class="hint">Original end: {{ Math.round(current.endMs) }} ms · {{ Math.max(0, Math.round((current.replyMs ?? current.endMs) - edit.userEndMs)) }} ms before Lux replies</p>
        <label>In the remaining pause<select :value="edit.status" aria-label="Agent activity" @change="statusChanged"><option value="none">No status</option><option value="thinking" :disabled="current.replyMs === undefined">Thinking</option><option value="console" :disabled="current.replyMs === undefined">Console activity</option></select></label>
        <p class="hint">{{ edit.status === 'console' ? CONSOLE_ACTIVITIES[selected] : edit.status === 'thinking' ? 'The widget shows Thinking until Lux starts speaking.' : 'Your bubble stays in the conversation history.' }}</p>
        <button @click="resetTurn">Reset this turn</button>
      </section>
    </div>
    <section class="timeline" aria-label="Presentation timeline">
      <div class="track"><span class="track-label">You</span><button v-for="(turn, i) in turns" :key="turn.utterance" class="user segment" :class="{selected: selected === turn.utterance}" :style="position(turn.startMs, turn.endMs)" :aria-label="`Select user turn ${i+1}`" @click="selected = turn.utterance"><i :style="{left: `${(turnStart(turn.utterance, turn.startMs) - turn.startMs) / (turn.endMs - turn.startMs) * 100}%`, width: `${(turnEnd(turn.utterance, turn.endMs) - turnStart(turn.utterance, turn.startMs)) / (turn.endMs - turn.startMs) * 100}%`}" /><b>{{ i + 1 }}</b></button></div>
      <div class="track"><span class="track-label">Work</span><button v-for="work in workWindows" :key="work.id" class="work segment" :style="position(work.startMs, work.endMs)" :title="work.status" @click="seek(work.startMs)">{{ work.status }}</button></div>
      <div class="track"><span class="track-label">Lux</span><button v-for="reply in replies" :key="reply.start" class="agent segment" :style="position(reply.start, reply.end)" :title="reply.text" @click="seek(reply.end); newBlock(reply.end)">Lux</button></div>
      <div class="cursor" :style="{left: `${time / duration * 100}%`}" />
    </section>
    <input class="scrub" aria-label="Playback position in milliseconds" type="range" min="0" :max="Math.ceil(duration)" step="1" :value="time" @input="seek(Number(($event.target as HTMLInputElement).value))">
    <section class="activity-editor">
      <h2>Activity blocks — before you speak or after Lux</h2>
      <p class="hint">Trim the user window to make room. Click a Lux segment to prepare an activity after that reply, or use the playhead.</p>
      <button @click="newBlock()">New activity at playhead</button>
      <div class="block-fields">
        <label>Activity start (ms)<input v-model.number="blockDraft.startMs" type="number" min="0" :max="duration" step="1"></label>
        <button @click="blockDraft.startMs = Math.round(time)">Mark activity start</button>
        <label>Activity end (ms)<input v-model.number="blockDraft.endMs" type="number" min="0" :max="duration" step="1"></label>
        <button @click="blockDraft.endMs = Math.round(time)">Mark activity end</button>
        <label>Activity type<select v-model="blockDraft.status"><option value="thinking">Thinking</option><option value="console">Console activity</option></select></label>
        <label v-if="blockDraft.status === 'console'">Console action<select v-model="blockDraft.consoleTask"><option v-for="(label, key) in CONSOLE_ACTIVITIES" :key="key" :value="key">{{ label }}</option></select></label>
        <button @click="saveBlock">{{ blockDraft.id ? 'Update activity block' : 'Add activity block' }}</button>
      </div>
      <div v-for="block in edits.activities ?? []" :key="block.id" class="block-row"><span>{{ block.startMs }}–{{ block.endMs }} ms · {{ block.status === 'thinking' ? 'Thinking' : CONSOLE_ACTIVITIES[block.consoleTask ?? ''] }}</span><button @click="editBlock(block)">Edit / preview</button><button @click="removeBlock(block.id)">Remove</button></div>
    </section>
    <p class="hint">Faded user bars show the original speaking windows. Solid bars show your changes. Only presentation changes — no audio is cut and no reply moves.</p>
  </main>
</template>
<style>
:root{color-scheme:dark;font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#eee;background:#151619}*{box-sizing:border-box}body{margin:0}main{max-width:1450px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between}small{color:#cdb8ee;letter-spacing:1.4px;font-size:10px}h1{font-size:26px;margin:7px 0 16px}a{color:#cdb8ee;text-decoration:none}button,.file-button{font:inherit;padding:9px 12px;border:1px solid #484952;border-radius:7px;background:#292b33;color:#eee;cursor:pointer}button:hover{background:#3b3d48}button[aria-pressed=true]{background:#cab5ec;color:#19141f}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.toolbar span{margin-left:auto;font:12px monospace}.file-button input{position:absolute;width:1px;height:1px;opacity:0}.workspace{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(300px,1fr);gap:20px;align-items:start}.preview{overflow:hidden;border-radius:12px}.controls{background:#202228;border:1px solid #393c46;padding:18px;border-radius:12px}.controls nav{display:flex;gap:6px}.quote{line-height:1.5;color:#eee;min-height:58px}.controls label{display:grid;gap:8px;margin:12px 0;color:#d1d2dc}.controls input[type=range]{width:100%}.end-time{display:flex;align-items:center;gap:8px}input[type=number],select{background:#13151a;color:#eee;border:1px solid #4a4d58;border-radius:6px;padding:8px;font:inherit}input[type=number]{width:110px}.hint,[role=status]{color:#a7abb7;font-size:12px;line-height:1.5}.error{color:#ffb2a5}.timeline{position:relative;margin:28px 0 8px 44px}.track{height:34px;position:relative;background:#101217;margin:5px 0;border-radius:5px}.track-label{position:absolute;left:-44px;top:10px;color:#aaa;font-size:11px}.segment{position:absolute;height:100%;padding:0;font-size:10px;white-space:nowrap;overflow:hidden;border:1px solid transparent;border-radius:4px}.user{background:#cab5ec33}.user i{position:absolute;inset:0 auto 0 0;background:#b49bd6}.user b{position:relative;color:#15141a}.user.selected{border-color:#eee}.agent{background:#829dc1;color:#10141c}.work{background:#d3b477;color:#191610}.cursor{position:absolute;width:2px;top:0;bottom:0;background:white;pointer-events:none}.scrub{width:calc(100% - 44px);margin-left:44px}@media(max-width:850px){.workspace{grid-template-columns:1fr}main{padding:16px}}
.activity-editor{margin:24px 0;padding:18px;border:1px solid #393c46;border-radius:12px;background:#202228}.activity-editor h2{font-size:18px;margin:0}.block-fields{display:flex;align-items:end;gap:10px;flex-wrap:wrap;margin:14px 0}.block-fields label{display:grid;gap:6px;font-size:12px}.block-row{display:flex;align-items:center;gap:10px;margin-top:10px}.block-row span{margin-right:auto;font:12px monospace}
/* Match the approved website hero framing. */
.preview .hero .recorded-camera { left:24px; bottom:24px; width:336px; height:199.5px; aspect-ratio:auto; }
.preview .recorded-camera video { object-fit:cover; }
.preview .hero-terminal { top:49px; bottom:113px; }
.preview .hero .recorded-widget.aloft { transform:translate(-316px,-280px) scale(1.2); }
</style>
