<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import VoiceAvatar from './VoiceAvatar.vue';

export interface StagePerson { id: string; name: string; voice: string; offline?: boolean; muted?: boolean }
export interface StageLine { id: number; person: string; text: string; label?: string }
const props = withDefaults(defineProps<{
  people: StagePerson[]; speaking?: string; lines?: StageLine[];
  initialDisplay?: 'heads' | 'caption' | 'thread'; reducedMotion?: boolean;
  initialHidden?: string[]; labelMode?: 'persona' | 'conversation'; caption?: StageLine | null;
}>(), { speaking: '', lines: () => [], initialDisplay: 'heads', reducedMotion: false, initialHidden: () => [], labelMode: 'persona' });
const emit = defineEmits<{ exit: []; preferences: [value: { hidden: string[]; display: 'heads' | 'caption' | 'thread' }]; labelMode: [value: 'persona' | 'conversation'] }>();
const hidden = ref([...props.initialHidden]);
const focus = ref('');
const peopleOpen = ref(false);
const exitButton = ref<HTMLButtonElement | null>(null);
const display = ref(props.initialDisplay);
watch([hidden, display], () => emit('preferences', { hidden: [...hidden.value], display: display.value }), { deep: true });
// Slots survive hiding, speaking, and incoming participant reordering.
const slots = reactive(new Map<string, number>());
watch(() => props.people, people => {
  for (const person of people) if (!slots.has(person.id)) slots.set(person.id, slots.size);
}, { immediate: true });
const visible = computed(() => props.people.filter(p => !hidden.value.includes(p.id)));
const focused = computed(() => props.people.find(p => p.id === focus.value && !hidden.value.includes(p.id)));
const speaker = computed(() => props.people.find(p => p.id === props.speaking));
const currentLine = computed(() => props.caption !== undefined ? props.caption : [...props.lines].reverse().find(line => line.person === props.speaking));
const thread = computed(() => props.lines.filter(line => !hidden.value.includes(line.person)).slice(-5));
const positions = [ [25, 28], [72, 22], [48, 54], [17, 63], [80, 62], [49, 12] ];
const dense = computed(() => slots.size > 6);
function position(id: string) {
  const slot = slots.get(id) ?? 0;
  const [x, y] = positions[slot] ?? [50, 50];
  return { '--x': `${x}%`, '--y': `${y}%`, '--slot': slot, '--column': slot % 4 + 1, '--row': Math.floor(slot / 4) + 1, '--mobile-column': slot % 2 + 1, '--mobile-row': Math.floor(slot / 2) + 1, order: slot };
}
function togglePerson(id: string) {
  hidden.value = hidden.value.includes(id) ? hidden.value.filter(key => key !== id) : [...hidden.value, id];
  if (hidden.value.includes(focus.value)) focus.value = '';
}
function onKey(event: KeyboardEvent) {
  if (event.key !== 'Escape') return;
  if (peopleOpen.value) peopleOpen.value = false;
  else emit('exit');
}
onMounted(() => { window.addEventListener('keydown', onKey); exitButton.value?.focus(); });
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
  <section class="stage" :class="{ 'reduce-motion': reducedMotion, 'has-thread': display === 'thread' }" aria-label="Stage">
    <header class="stage-header">
      <div class="stage-title"><span class="stage-mark">n<span>·</span></span><div><strong>Stage</strong><span class="stage-subtitle">A little room for a bigger conversation</span></div></div>
      <button ref="exitButton" class="stage-exit" @click="emit('exit')">↙ Back to dashboard <kbd>Esc</kbd></button>
    </header>
    <div class="stage-body">
      <div class="constellation" :class="{ dense, solo: people.length === 1 }" aria-label="Conversation portraits">
        <div class="room-caption"><span class="room-dot" /> {{ speaker ? `${speaker.name} is speaking` : 'Room to think out loud' }}</div>
        <article v-for="person in visible" :key="person.id" class="person" :class="{ speaking: speaking === person.id, focused: focus === person.id, offline: person.offline, muted: person.muted }" :style="position(person.id)" :data-person="person.id">
          <button class="person-focus" :aria-label="`Focus on ${person.name}`" :aria-pressed="focus === person.id" @click="focus = focus === person.id ? '' : person.id">
            <span class="portrait-shell"><VoiceAvatar :voice="person.voice" :size="126" /><span v-if="speaking === person.id" class="speaking-bars" aria-hidden="true"><i/><i/><i/><i/></span></span>
            <span class="person-name">{{ person.name }}</span>
            <span class="person-state">{{ person.offline ? 'Offline' : person.muted ? 'Muted' : speaking === person.id ? 'Speaking' : focus === person.id ? 'In focus' : 'Ready' }}</span>
          </button>
        </article>
        <div v-if="!visible.length" class="stage-empty"><span>✧</span><h2>{{ people.length ? 'Make room for someone' : 'The room is quiet' }}</h2><p>{{ people.length ? 'Choose a conversation in People to bring it back on stage.' : 'Open a conversation to bring its portrait here.' }}</p><button v-if="people.length" class="stage-control" @click="hidden = []">Show everyone</button></div>
      </div>
      <aside v-if="display === 'thread'" class="stage-thread" aria-label="Shared transcript"><div class="thread-heading"><span>THE CONVERSATION</span></div><p class="thread-note">A shared view. Each agent keeps its own conversation.</p><div v-for="line in thread" :key="line.id" class="thread-line"><strong>{{ line.label ?? people.find(p => p.id === line.person)?.name ?? 'You' }}</strong><p>{{ line.text }}</p></div><p v-if="!thread.length" class="thread-note">Words will appear here.</p></aside>
    </div>
    <div v-if="display === 'caption'" class="stage-caption" aria-live="polite"><span>{{ currentLine?.label ?? speaker?.name ?? 'CURRENT CAPTION' }}</span><p>{{ currentLine?.text ?? 'When someone speaks, their words appear here.' }}</p></div>
    <footer class="stage-footer">
      <div class="people-picker"><button class="stage-control" :aria-expanded="peopleOpen" aria-controls="stage-people" @click="peopleOpen = !peopleOpen">People <span>{{ visible.length }}/{{ people.length }}</span> <span aria-hidden="true">⌃</span></button>
        <div v-if="peopleOpen" id="stage-people" class="people-menu"><strong>On your stage</strong><label class="label-choice">Names<select aria-label="Stage names" :value="labelMode" @change="emit('labelMode', ($event.target as HTMLSelectElement).value as 'persona' | 'conversation')"><option value="persona">Agent names</option><option value="conversation">Conversation titles</option></select></label><p>Hide a portrait without closing its conversation.</p><label v-for="person in people" :key="person.id"><input type="checkbox" :checked="!hidden.includes(person.id)" @change="togglePerson(person.id)"><span>{{ person.name }}</span></label><p v-if="!people.length">No open conversations yet.</p></div>
      </div>
      <div class="stage-display" aria-label="Stage display"><button v-for="option in (['heads','caption','thread'] as const)" :key="option" :aria-pressed="display === option" @click="display = option">{{ { heads: 'Just faces', caption: 'Caption', thread: 'Transcript' }[option] }}</button></div>
      <p class="stage-focus-note">{{ focused ? `${focused.name} in focus` : 'Choose a face to focus' }}<span>Microphone recipient stays unchanged</span></p>
    </footer>
  </section>
</template>

<style scoped>
.stage{--stage-ink:#eae6dc;--stage-muted:#9caaa5;box-sizing:border-box;min-height:100dvh;background:radial-gradient(ellipse at 49% 44%,#1c3533 0%,#132624 38%,#0b1719 76%);color:var(--stage-ink);font-family:var(--sans,system-ui,sans-serif);padding:28px 38px 24px;display:flex;flex-direction:column;overflow:hidden;position:relative}
.stage::before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.16;background-image:radial-gradient(#89afa0 .6px,transparent .6px);background-size:24px 24px;mask-image:radial-gradient(ellipse,#000,transparent 75%)}
.stage-header,.stage-footer{position:relative;z-index:3;display:flex;align-items:center;justify-content:space-between;gap:20px}.stage-title{display:flex;gap:17px;align-items:center}.stage-title strong{display:block;font-size:22px;font-weight:550;letter-spacing:-.7px}.stage-mark{font-size:38px;line-height:1;font-weight:700}.stage-mark span{color:#b6e3af}.stage-subtitle{display:block;margin-top:4px;font-size:12px;color:var(--stage-muted)}
.stage button{font:inherit;cursor:pointer}.stage button:focus-visible,.stage input:focus-visible{outline:2px solid #d5f4b2;outline-offset:5px}.stage-exit{border:0;background:transparent;color:#b9c4bd;font-size:12px!important;padding:12px 0}.stage-exit kbd{font-family:inherit;font-size:10px;border:1px solid #53625b;border-radius:4px;padding:3px 5px;margin-left:8px}
.stage-body{position:relative;display:flex;flex:1;min-height:550px;gap:34px}.constellation{position:relative;flex:1;min-width:0;margin:48px 0 20px}.room-caption{position:absolute;top:-23px;left:0;right:0;text-align:center;color:#b0c0b5;font-size:11px;letter-spacing:.8px}.room-dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:#b2caa9;margin:0 7px 2px 0}
.solo .person{left:50%;top:33%}
.person{position:absolute;left:var(--x);top:var(--y);transform:translate(-50%,-12%);width:190px;text-align:center}.person-focus{border:0;color:inherit;background:none;width:100%;padding:0;display:flex;flex-direction:column;align-items:center;gap:0}.portrait-shell{position:relative;display:inline-flex;padding:9px;border:1px solid #66827555;border-radius:42%;background:#b5c8b708;box-shadow:0 16px 40px #0004;transition:border-color .25s,box-shadow .25s}.portrait-shell :deep(.voice-avatar){border-radius:37%;filter:saturate(.75)}
.person-name{margin-top:14px;font-size:15px;font-weight:550;letter-spacing:-.15px;line-height:1.35;max-width:190px;overflow-wrap:anywhere}.person-state{height:14px;font-size:10px;margin-top:5px;color:#83968a;letter-spacing:.8px}.person.speaking .portrait-shell{border-color:#d4edb3;box-shadow:0 0 0 5px #c6e7a40b,0 0 70px #a6d89c22}.person.speaking .person-state{color:#d4edb3}.person.focused .portrait-shell{outline:1px solid #bccddd;outline-offset:5px}.person.offline .portrait-shell{opacity:.45;filter:grayscale(.8)}.person.muted .person-state{color:#cead8e}
.speaking-bars{display:flex;align-items:center;justify-content:center;gap:3px;position:absolute;bottom:-8px;left:calc(50% - 19px);width:38px;height:22px;background:#cce9ad;color:#263b2c;border:3px solid #19302b;border-radius:20px}.speaking-bars i{width:2px;height:9px;background:currentColor;animation:stage-speak 1s ease-in-out infinite}.speaking-bars i:nth-child(2){height:13px;animation-delay:.2s}.speaking-bars i:nth-child(3){height:6px;animation-delay:.4s}@keyframes stage-speak{50%{transform:scaleY(.4)}}
.stage-footer{margin-top:12px;padding-top:18px;border-top:1px solid #acc5b41a}.stage-control{background:#e7f7e80a;border:1px solid #b7cbbc33;border-radius:9px;padding:10px 15px;color:#dde6d9;font-size:12px!important}.stage-control span{color:#a6bca9;margin-left:9px}.people-picker{position:relative}.people-menu{position:absolute;bottom:calc(100% + 16px);left:0;width:260px;max-height:360px;overflow:auto;background:#20322f;border:1px solid #77958766;border-radius:14px;padding:20px;box-shadow:0 14px 55px #0008}.label-choice{justify-content:space-between}.label-choice select{max-width:150px;background:#10211f;color:#dce8d7;border:1px solid #77958766;padding:6px;border-radius:6px;font:inherit}.people-menu strong{font-size:14px}.people-menu p{font-size:11px;line-height:1.6;color:#b1c1b6;margin:7px 0 14px}.people-menu label{display:flex;align-items:center;gap:11px;font-size:12px;padding:9px 0;cursor:pointer}.people-menu input{accent-color:#c2dfa5}.people-menu label span{overflow-wrap:anywhere;min-width:0}
.stage-display{display:flex;gap:3px;background:#05121055;padding:4px;border:1px solid #748d7b33;border-radius:10px}.stage-display button{font-size:11px;border:0;background:none;color:#a9b7aa;border-radius:7px;padding:9px 15px;white-space:nowrap}.stage-display button[aria-pressed=true]{background:#d7e3be;color:#22342b;box-shadow:0 2px 8px #0002}.stage-focus-note{font-size:11px;color:#d0d8c8;text-align:right;min-width:205px;margin:0;max-width:280px;overflow-wrap:anywhere}.stage-focus-note span{display:block;font-size:10px;margin-top:5px;color:#859b8c}
.stage-caption{position:relative;max-width:780px;margin:0 auto 14px;text-align:center;background:#07151399;border:1px solid #a1baa333;border-radius:16px;padding:16px 26px}.stage-caption span{font-size:10px;letter-spacing:1px;color:#bdda9b}.stage-caption p{font-size:18px;line-height:1.6;margin:5px 0 0}.stage-thread{width:260px;align-self:stretch;margin:40px 0 16px;border-left:1px solid #a4b8a62a;padding-left:25px;flex-shrink:0}.thread-heading{display:flex;justify-content:space-between;gap:10px;font-size:10px;letter-spacing:1px;color:#c6d8b4}.thread-heading span:last-child{color:#94a796;letter-spacing:0}.thread-note{font-size:11px;color:#9ead9e;line-height:1.7}.thread-line{margin-top:28px}.thread-line strong{font-size:11px;color:#c2d2ad}.thread-line p{font-size:13px;line-height:1.75;color:#c6cfc3;margin:7px 0}.stage-empty{position:absolute;inset:18% 0 auto;text-align:center}.stage-empty>span{font-size:64px;color:#9dbea4}.stage-empty h2{font-size:24px;font-weight:400;letter-spacing:-.7px}.stage-empty p{font-size:13px;color:#9eb2a4;line-height:1.7}
.constellation.dense{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:35px 8px;padding:35px 0}.dense .person{grid-column:var(--column);grid-row:var(--row);position:relative;left:auto;top:auto;transform:none;width:auto}.dense .person:nth-of-type(2n){padding-top:25px}.dense .portrait-shell :deep(.voice-avatar){width:94px!important;height:94px!important}.dense .person-name{font-size:13px}.reduce-motion *, .reduce-motion *::before{animation:none!important;transition:none!important}
@media(prefers-reduced-motion:reduce){.stage *{animation:none!important;transition:none!important}}
@media(max-width:1050px){.stage{padding:22px}.stage-body{min-height:580px}.stage-focus-note{display:none}.person{width:150px}.portrait-shell :deep(.voice-avatar){width:102px!important;height:102px!important}.person-name{font-size:13px;max-width:150px}.stage-thread{width:210px}.has-thread .constellation{display:grid;grid-template-columns:repeat(2,1fr);gap:25px;padding-top:20px}.has-thread .person{grid-column:var(--mobile-column);grid-row:var(--mobile-row);position:relative;left:auto;top:auto;transform:none;width:auto}}
@media(max-width:650px){.stage{padding:20px 16px;overflow:visible}.stage-subtitle{display:none}.stage-exit kbd{display:none}.stage-exit{font-size:11px!important}.stage-title strong{font-size:20px}.stage-body{min-height:430px;display:block}.constellation,.constellation.dense,.has-thread .constellation{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:30px 12px;margin-top:60px;padding:16px 0 28px}.person,.dense .person,.has-thread .person{grid-column:var(--mobile-column);grid-row:var(--mobile-row);position:relative;left:auto;top:auto;transform:none;width:auto;padding:0}.person:nth-of-type(2n){padding-top:25px}.room-caption{font-size:10px;top:-24px}.person-name{max-width:150px}.stage-footer{flex-wrap:wrap;gap:15px;justify-content:center}.stage-display button{padding:9px 12px}.people-menu{left:50%;transform:translateX(-50%);width:min(260px,76vw)}.stage-thread{width:auto;margin:12px 0;border-left:0;border-top:1px solid #a4b8a62a;padding:24px 0}.stage-caption{padding:13px 16px}.stage-caption p{font-size:15px}.stage-empty{position:relative;grid-column:1/-1;padding:45px 12px}.stage-empty h2{font-size:21px}}
</style>
