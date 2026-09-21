import { afterEach, expect, it, vi } from 'vitest';
import { ACCENT_STORAGE_KEY, initializeAccentPalette, useAccentPalette } from './useAccentPalette';
const { accent, selectAccent } = useAccentPalette();
afterEach(() => { vi.restoreAllMocks(); localStorage.removeItem(ACCENT_STORAGE_KEY); initializeAccentPalette(); });
it('persists a selected palette and restores it at startup', () => {
  selectAccent('rose');
  document.documentElement.dataset.accent = 'amber';
  initializeAccentPalette();
  expect([accent.value, document.documentElement.dataset.accent, localStorage.getItem(ACCENT_STORAGE_KEY)]).toEqual(['rose', 'rose', 'rose']);
});
it('receives changes from another window and resets deleted preferences', () => {
  localStorage.setItem(ACCENT_STORAGE_KEY, 'teal');
  window.dispatchEvent(new StorageEvent('storage', { key: ACCENT_STORAGE_KEY }));
  expect(document.documentElement.dataset.accent).toBe('teal');
  localStorage.removeItem(ACCENT_STORAGE_KEY);
  window.dispatchEvent(new StorageEvent('storage', { key: ACCENT_STORAGE_KEY }));
  expect(document.documentElement.dataset.accent).toBe('teal');
});
it('keeps selection usable if saving fails', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage unavailable'); });
  selectAccent('blue');
  expect([accent.value, document.documentElement.dataset.accent]).toEqual(['blue', 'blue']);
});

it('saves and restores independent user and agent palettes', () => {
  const { selectAgentAccent, agentAccent } = useAccentPalette();
  selectAccent('teal');
  selectAgentAccent('rose');
  initializeAccentPalette();
  expect([accent.value, agentAccent.value, document.documentElement.dataset.accent, document.documentElement.dataset.agentAccent]).toEqual(['teal', 'rose', 'teal', 'rose']);
  localStorage.removeItem('noisy-studio.agent-accent');
});

it('uses teal and periwinkle when neither preference is saved', () => {
  localStorage.removeItem(ACCENT_STORAGE_KEY);
  localStorage.removeItem('noisy-studio.agent-accent');
  initializeAccentPalette();
  expect([document.documentElement.dataset.accent, document.documentElement.dataset.agentAccent]).toEqual(['teal', 'periwinkle']);
});
