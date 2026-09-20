import { describe, expect, it } from "vitest";
import {
  SEG_ARC_START_DEG,
  SEG_DEG,
  segStopAngle,
  segTraitFromAngle,
  traitWord,
  TRAIT_STOPS,
} from "./characterMath";

describe("segTraitFromAngle", () => {
  it("selects a wedge's upper boundary — a click anywhere in a wedge", () => {
    // First visible wedge spans [start, start+60); a click just inside it
    // selects its upper boundary, value 20.
    expect(segTraitFromAngle(SEG_ARC_START_DEG + 1)).toBe(20);
    expect(segTraitFromAngle(SEG_ARC_START_DEG + SEG_DEG + 1)).toBe(40);
    expect(segTraitFromAngle(SEG_ARC_START_DEG + 4 * SEG_DEG + 1)).toBe(100);
  });

  it("returns 0 for a click in the decorative bottom wedge", () => {
    // Just past the 5th wedge's end (i.e. into the 300°→360° gap) → 0.
    expect(segTraitFromAngle(SEG_ARC_START_DEG + 5 * SEG_DEG + 1)).toBe(0);
    // Bottom-centre (90° screen) sits in the gap.
    expect(segTraitFromAngle(90)).toBe(0);
  });

  it("only ever returns a declared stop", () => {
    for (let a = 0; a < 360; a += 3) {
      expect(TRAIT_STOPS).toContain(segTraitFromAngle(a) as (typeof TRAIT_STOPS)[number]);
    }
  });
});

describe("segStopAngle", () => {
  it("places stop 0 at the arc start and stops 60° apart", () => {
    expect(segStopAngle(0)).toBeCloseTo(SEG_ARC_START_DEG % 360, 5);
    expect(segStopAngle(20)).toBeCloseTo((SEG_ARC_START_DEG + SEG_DEG) % 360, 5);
    expect(segStopAngle(100)).toBeCloseTo((SEG_ARC_START_DEG + 5 * SEG_DEG) % 360, 5);
  });
});

describe("traitWord", () => {
  it("names each stop for a known trait", () => {
    expect(traitWord("humor", 0)).toBe("sterile");
    expect(traitWord("humor", 60)).toBe("playful");
    expect(traitWord("humor", 100)).toBe("absurd");
    expect(traitWord("talkative", 100)).toBe("commentary");
    expect(traitWord("verbosity", 0)).toBe("clicks");
    expect(traitWord("verbosity", 100)).toBe("lecture");
  });

  it("indexes by value/20 across all four traits at their extremes", () => {
    for (const trait of ["humor", "honesty", "verbosity", "talkative"]) {
      expect(typeof traitWord(trait, 0)).toBe("string");
      expect(typeof traitWord(trait, 100)).toBe("string");
      expect(traitWord(trait, 0)).not.toBe(traitWord(trait, 100));
    }
  });

  it("falls back to the number for an unknown trait", () => {
    expect(traitWord("nope", 40)).toBe("40");
  });
});
