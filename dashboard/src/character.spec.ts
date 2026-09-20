import { expect, it } from "vitest";
import { canonicalCharacter } from "./character";

it("migrates an old cached character without changing it or inverting it twice", () => {
  const legacy = { humor: 20, honesty: 60, brevity: 30, chatty: 80, voice: "lux", speed: 1.2 };

  const character = canonicalCharacter(legacy);

  expect(character).toEqual({ humor: 20, honesty: 60, verbosity: 70, talkative: 80, voice: "lux", speed: 1.2 });
  expect(canonicalCharacter(character)).toEqual(character);
  expect(legacy.brevity).toBe(30);
});

it("prefers canonical zeroes when both generations of keys are present", () => {
  const character = canonicalCharacter({ humor: 20, honesty: 60, verbosity: 0, talkative: 0,
    brevity: 30, chatty: 80, voice: "lux", speed: 1.2 });

  expect(character).toEqual({ humor: 20, honesty: 60, verbosity: 0, talkative: 0, voice: "lux", speed: 1.2 });
});
