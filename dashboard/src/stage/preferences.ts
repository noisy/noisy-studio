import { ref, watch } from 'vue';
export interface StagePreferences { display: 'heads' | 'caption' | 'thread'; labels: 'persona' | 'conversation'; hidden: string[] }
export const STAGE_PREFERENCES_KEY = 'noisy-studio.stage';
export function useStagePreferences() {
  const initial: StagePreferences = { display: 'heads', labels: 'persona', hidden: [] };
  try {
    const saved = JSON.parse(localStorage.getItem(STAGE_PREFERENCES_KEY) ?? 'null');
    if (saved && typeof saved === 'object') {
      if (['heads','caption','thread'].includes(saved.display)) initial.display = saved.display;
      if (['persona','conversation'].includes(saved.labels)) initial.labels = saved.labels;
      if (Array.isArray(saved.hidden)) initial.hidden = saved.hidden.filter((id: unknown) => typeof id === 'string');
    }
  } catch { /* Damaged or unavailable storage uses session defaults. */ }
  const preferences = ref(initial);
  watch(preferences, value => { try { localStorage.setItem(STAGE_PREFERENCES_KEY, JSON.stringify(value)); } catch { /* Session-only preferences. */ } }, { deep: true });
  return preferences;
}
