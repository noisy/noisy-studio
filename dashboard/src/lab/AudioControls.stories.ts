import './audioControls.css';
import { computed, nextTick, ref } from 'vue';
import type { Meta, StoryObj } from '@storybook/vue3';

export default { title: 'Lab/AudioControls', parameters: { layout: 'fullscreen' } } satisfies Meta;

const DASHBOARD_PANEL_WIDTH = 320;
const END_SILENCE_SECONDS = [0, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const controls = [
  { id: 'microphone', label: 'Microphone', help: 'Choose the input device used to hear your voice.', choices: ['System default', 'USB headset', 'Built-in microphone'], initial: 'System default' },
  { id: 'language', label: 'Language', help: 'Language used for speech recognition and synthesis.', choices: ['Auto-detect', 'English', 'Polish'], initial: 'English' },
  { id: 'turn', label: 'Turn detection', help: 'Speak naturally, or hold a button while talking.', choices: ['Auto', 'Push to talk'], initial: 'Auto' },
  { id: 'agent', label: 'Agent speech', help: 'Stream replies as they are generated, or wait for the complete audio.', choices: ['Live', 'Batch'], initial: 'Live' },
  { id: 'recognition', label: 'Your speech', help: 'Transcribe while you speak, or after your turn ends.', choices: ['Live', 'Batch'], initial: 'Live' },
  { id: 'cues', label: 'Sound cues', help: 'Play short sounds for conversation events.', choices: ['On', 'Off'], initial: 'On' },
  { id: 'silence', label: 'End silence', help: 'In Auto mode, wait this long after speech before ending your turn.', choices: END_SILENCE_SECONDS.map(seconds => `${seconds}s`), initial: '2s' },
  { id: 'sensitivity', label: 'Sensitivity', help: 'Adjust how readily the microphone detects speech.', choices: ['Low', 'Medium', 'High'], initial: 'Medium' },
  { id: 'smart', label: 'Smart turn', help: 'In Auto mode, allow extra time when a sentence sounds unfinished.', choices: ['Off', '0.5', '1.0'], initial: 'Off' },
];

function render(variant: 'column' | 'inline', all = false) {
  return () => ({
    setup() {
      const shown = ref(all ? controls.map(c => c.id) : ['microphone', 'language', 'turn']);
      const values = ref(Object.fromEntries(controls.map(c => [c.id, c.initial])));
      const settingsOpen = ref(false);
      const settingsHeading = ref<HTMLElement | null>(null);
      const visible = computed(() => controls.filter(c => shown.value.includes(c.id)));
      const inactive = (id: string) => ['silence', 'smart'].includes(id) && values.value.turn === 'Push to talk';
      async function openSettings() {
        settingsOpen.value = true;
        await nextTick();
        settingsHeading.value?.focus();
      }
      return { panelWidth: DASHBOARD_PANEL_WIDTH, controls, shown, values, settingsOpen, settingsHeading, visible, inactive, openSettings, variant };
    },
    template: `
      <main class="audio-lab" :style="{ '--audio-panel-width': panelWidth + 'px' }">

        <h1>Audio controls · {{ variant === 'column' ? 'A — compact visibility column' : 'B — explicit row checkboxes' }}</h1>
        <p>Choose what stays within reach. Hiding a control never changes its value.</p>
        <div class="board">
          <div>
            <p class="note">DASHBOARD PREVIEW</p>
            <section class="quick-panel" aria-label="Dashboard audio controls">
              <header><h2>Audio controls</h2><button @click="openSettings" aria-label="Open Settings, Audio, Audio controls">Settings ↗</button></header>
              <div v-for="c in visible" :key="c.id" class="quick" :title="inactive(c.id) ? 'Used in Auto mode' : c.help">
                <label :id="'quick-label-'+c.id" :for="c.choices.length === 2 ? undefined : 'quick-'+c.id">{{ c.label }}</label>
                <div v-if="c.choices.length === 2" class="choice-buttons" role="group" :aria-labelledby="'quick-label-'+c.id"><button v-for="choice in c.choices" :key="choice" :aria-pressed="values[c.id] === choice" @click="values[c.id] = choice">{{choice}}</button></div>
                <select v-else :id="'quick-'+c.id" v-model="values[c.id]" :disabled="inactive(c.id)"><option v-for="choice in c.choices" :key="choice">{{choice}}</option></select>
              </div>
              <p v-if="!visible.length">No quick controls selected. Choose which to show in Settings.</p>
            </section>
            <p class="note">Interactive proposal only. Changes here do not affect your microphone or daemon.</p>
          </div>
          <section v-if="settingsOpen" :class="variant" aria-label="Audio settings">
            <header><span>Settings / Audio</span><button @click="settingsOpen = false">Close settings</button></header>
            <h2 ref="settingsHeading" tabindex="-1">Audio controls</h2>
            <p>All controls are available here. Choose which also appear on your dashboard.</p>
            <div v-if="variant === 'column'" class="column-label">Show on dashboard</div>
            <div v-for="c in controls" :key="c.id" class="setting">
              <div><label :id="'setting-label-'+c.id" :for="c.choices.length === 2 ? undefined : 'setting-'+c.id">{{c.label}}</label><p class="description">{{c.help}}</p></div>
              <div v-if="c.choices.length === 2" class="choice-buttons" role="group" :aria-labelledby="'setting-label-'+c.id"><button v-for="choice in c.choices" :key="choice" :aria-pressed="values[c.id] === choice" @click="values[c.id] = choice">{{choice}}</button></div>
              <select v-else :id="'setting-'+c.id" v-model="values[c.id]" :disabled="inactive(c.id)"><option v-for="choice in c.choices" :key="choice">{{choice}}</option></select>
              <label class="pin"><input type="checkbox" v-model="shown" :value="c.id" :aria-label="'Show '+c.label+' on dashboard'">{{variant === 'inline' ? 'Show on dashboard' : 'Show'}}</label>
            </div>
            <button @click="shown = ['microphone', 'language', 'turn']">Restore default visibility</button>
          </section>
          <section v-else class="placeholder"><h2>Settings shortcut</h2><p>Click Settings on the audio panel to open Audio → Audio controls and focus the section heading.</p><p>Try hiding every control, showing them all, or choosing Push to talk.</p></section>
        </div>
      </main>`,
  });
}

export const Compact: StoryObj = { render: render('column') };
export const Explicit: StoryObj = { render: render('inline') };
export const AllControls: StoryObj = { render: render('column', true) };
