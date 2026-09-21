import { readonly, ref } from 'vue';
import { DEFAULT_AVATAR_SET, isAvatarSet, type AvatarSetId } from '../avatars/catalog';

export const AVATAR_STORAGE_KEY = 'noisy-studio.avatar-set';
function readPreference(): AvatarSetId {
  try {
    const saved = localStorage.getItem(AVATAR_STORAGE_KEY);
    return isAvatarSet(saved) ? saved : DEFAULT_AVATAR_SET;
  } catch {
    return DEFAULT_AVATAR_SET;
  }
}
const selected = ref<AvatarSetId>(readPreference());
function receivePreference(event: StorageEvent) {
  if (event.key === AVATAR_STORAGE_KEY || event.key === null) {
    selected.value = isAvatarSet(event.newValue) ? event.newValue : DEFAULT_AVATAR_SET;
  }
}
// Same-origin dashboard and companion windows share this local preference.
if (typeof window !== 'undefined') window.addEventListener('storage', receivePreference);
if (import.meta.hot) import.meta.hot.dispose(() => window.removeEventListener('storage', receivePreference));

export function useAvatarSet() {
  function selectAvatarSet(value: AvatarSetId) {
    if (!isAvatarSet(value)) return;
    selected.value = value;
    try { localStorage.setItem(AVATAR_STORAGE_KEY, value); } catch { /* Still usable for this session. */ }
  }
  return { avatarSet: readonly(selected), selectAvatarSet };
}
