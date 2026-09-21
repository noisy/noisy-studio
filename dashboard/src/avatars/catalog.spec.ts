import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { AVATAR_SETS, AVATAR_VOICES, avatarCell } from './catalog';
import { VOICES } from '../components/characterMath';
import cropMetadata from './crop-metadata.json';

describe('voice artwork coverage', () => {
  it('keeps every voice crop inside the shipped atlas', () => {
    for (const set of AVATAR_SETS) {
      const crop = cropMetadata[set.id];
      expect(crop.rows[0]).toBe(0);
      expect(crop.rows.at(-1)).toBe(crop.height);
      for (let row = 0; row < 5; row++) {
        expect(crop.rows[row + 1]).toBeGreaterThan(crop.rows[row]);
        expect(crop.columns[row][0]).toBe(0);
        expect(crop.columns[row].at(-1)).toBe(crop.width);
        for (let column = 0; column < 6; column++) {
          expect(crop.columns[row][column + 1]).toBeGreaterThan(crop.columns[row][column]);
        }
      }
    }
  });
  it('covers every voice assigned by the backend, including Aurora and Liora', () => {
    // The pool moved from http_api.py to state.py (VOICE_POOL) when agent
    // tabs started claiming exclusive voices (#54); read it where it lives.
    const backend = readFileSync(resolve('../src/noisy_studio/listener/state.py'), 'utf8');
    const pool = backend.match(/^VOICE_POOL = \(([\s\S]*?)\)/m)?.[1] ?? '';
    const voices = [...pool.matchAll(/"([^"]+)"/g)].map(match => match[1]);
    expect(voices.length).toBeGreaterThan(0);
    expect([...AVATAR_VOICES].sort()).toEqual(voices.sort());
    expect(Object.keys(VOICES).sort()).toEqual([...AVATAR_VOICES].sort());
    expect(new Set(AVATAR_VOICES).size).toBe(AVATAR_VOICES.length);
  });
  it('ships artwork and reusable prompts for every selectable set', () => {
    for (const set of AVATAR_SETS) {
      expect(existsSync(resolve(`src/assets/voice-avatars/${set.id}.png`)), set.id).toBe(true);
      expect(existsSync(resolve(`../docs/avatar-generation/prompts/${set.id}.txt`)), set.id).toBe(true);
    }
  });
  it('normalizes known identities and leaves future voices to the fallback', () => {
    expect(avatarCell(' AURORA ')).not.toBeNull();
    expect(avatarCell('liora')).not.toBeNull();
    expect(avatarCell('future-voice')).toBeNull();
  });
});
