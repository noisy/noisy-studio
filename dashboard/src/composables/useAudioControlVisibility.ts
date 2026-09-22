import { ref, watch } from 'vue';
import { AUDIO_CONTROL_IDS, DEFAULT_AUDIO_CONTROLS, type AudioControlId } from '../components/audioControls';
const KEY = 'noisy.audioControls.visible';
export function useAudioControlVisibility() {
  let initial = [...DEFAULT_AUDIO_CONTROLS];
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    if (Array.isArray(saved)) initial = AUDIO_CONTROL_IDS.filter(id => saved.includes(id));
  } catch { /* Use defaults when storage is unavailable or damaged. */ }
  const visible = ref<AudioControlId[]>(initial);
  watch(visible, value => { try { localStorage.setItem(KEY, JSON.stringify(value)); } catch { /* Session-only preferences. */ } }, {deep:true});
  return visible;
}
