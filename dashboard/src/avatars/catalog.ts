import portraitFrames from './portrait-frames.json';
import cropMetadata from './crop-metadata.json';
import voiceOrder from './voice-order.json';

export const AVATAR_COLUMNS = 6;
export const AVATAR_ROWS = 5;
export const AVATAR_VOICES: readonly string[] = voiceOrder;
export const AVATAR_SETS = [
  { id: 'editorial', name: 'Illustrated portraits', description: 'Clean illustrated portraits', image: new URL('../assets/voice-avatars/editorial.webp', import.meta.url).href },
  { id: 'matte', name: 'Matte portraits', description: 'Softly sculpted people', image: new URL('../assets/voice-avatars/matte.png', import.meta.url).href },
  { id: 'mineral', name: 'Minerals', description: 'Distinctive stone forms', image: new URL('../assets/voice-avatars/mineral.png', import.meta.url).href },
  { id: 'blobs', name: 'Blobs', description: 'Expressive little creatures', image: new URL('../assets/voice-avatars/blobs.png', import.meta.url).href },
  { id: 'animals', name: 'Animals', description: 'Distinctive animal portraits', image: new URL('../assets/voice-avatars/animals.png', import.meta.url).href },
  { id: 'robots', name: 'Robots', description: 'Original sci-fi robot personalities', image: new URL('../assets/voice-avatars/robots.png', import.meta.url).href },
  { id: 'agents', name: 'Agents', description: 'Black suits and dark sunglasses', image: new URL('../assets/voice-avatars/agents.png', import.meta.url).href },
] as const;
export type AvatarSetId = typeof AVATAR_SETS[number]['id'];
export const DEFAULT_AVATAR_SET: AvatarSetId = 'editorial';
export function isAvatarSet(value: unknown): value is AvatarSetId {
  return AVATAR_SETS.some(set => set.id === value);
}
export function avatarCell(voice: string): number | null {
  const index = AVATAR_VOICES.indexOf(voice.trim().toLowerCase());
  return index < 0 ? null : index;
}

export function avatarImageStyle(set: AvatarSetId, cell: number) {
  const crop = cropMetadata[set];
  const frame = avatarFrame(set, cell);
  if (frame) return {
    width: `${crop.width / frame.width * 100}%`, height: `${crop.height / frame.height * 100}%`,
    left: `${-frame.left / frame.width * 100}%`, top: `${-frame.top / frame.height * 100}%`,
  };
  const row = Math.floor(cell / AVATAR_COLUMNS);
  const top = crop.rows[row];
  const height = crop.rows[row + 1] - top;
  const column = cell % AVATAR_COLUMNS;
  const left = crop.columns[row][column];
  const width = crop.columns[row][column + 1] - left;
  return {
    width: `${crop.width / width * 100}%`, height: `${crop.height / height * 100}%`,
    left: `${-left / width * 100}%`, top: `${-top / height * 100}%`,
  };
}

/** Keep the source crop clipped while fitting it without stretching the face. */
export function avatarFrame(set: AvatarSetId, cell: number) {
  return set === 'editorial' || set === 'matte' ? portraitFrames[set][cell] : undefined;
}
export function avatarFrameStyle(set: AvatarSetId, cell: number) {
  const frame = avatarFrame(set, cell);
  if (!frame) return { width: '100%', height: '100%', left: '0%', bottom: '0%' };
  const side = Math.max(frame.width, frame.height);
  return {
    width: `${frame.width / side * 100}%`, height: `${frame.height / side * 100}%`,
    left: `${(side - frame.width) / side * 50}%`, bottom: '0%',
  };
}
