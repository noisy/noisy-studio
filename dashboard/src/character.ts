import type { Character } from "./types";

type CharacterInput = Omit<Character, "verbosity" | "talkative"> &
  Partial<Pick<Character, "verbosity" | "talkative">> &
  { brevity?: number; chatty?: number };

/** Upgrade old API responses and cached characters once, before rendering. */
export function canonicalCharacter(value: CharacterInput): Character {
  const { brevity, chatty, ...character } = value;
  return {
    ...character,
    verbosity: character.verbosity ?? (brevity === undefined ? 40 : 100 - brevity),
    talkative: character.talkative ?? chatty ?? 40,
  };
}
