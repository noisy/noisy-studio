/** Angle → value mapping for the editable radial gauges (kept pure). */

// Trait gauges: 280° sweep starting at 130° (prototype geometry).
const TRAIT_START_DEG = 130;
const TRAIT_SWEEP_DEG = 280;

// Speed dial: 250° sweep starting at 145° (rotate(-215) in the prototype).
const SPEED_START_DEG = 145;
const SPEED_SWEEP_DEG = 250;
const SPEED_MIN = 0.7;
const SPEED_MAX = 1.5;

/** Screen angle (deg, 0 = right, clockwise) of a pointer relative to a box center. */
export function pointerAngleDeg(x: number, y: number): number {
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function sweepFraction(angleDeg: number, startDeg: number, sweepDeg: number): number {
  const along = (angleDeg - startDeg + 360) % 360;
  if (along <= sweepDeg) return along / sweepDeg;
  // In the dead zone below the arc: snap to the nearest end.
  return along - sweepDeg < (360 - sweepDeg) / 2 ? 1 : 0;
}

export function traitValueFromAngle(angleDeg: number): number {
  return Math.round(sweepFraction(angleDeg, TRAIT_START_DEG, TRAIT_SWEEP_DEG) * 100);
}

// Traits are set in coarse steps, not a continuous 0–100: fine granularity
// was never meaningful (the character-matrix semantics move in ~20-point
// bands) and snapping makes a value easy to hit by eye. Six stops.
export const TRAIT_STEP = 20;
export const TRAIT_STOPS = [0, 20, 40, 60, 80, 100] as const;

// ── Segmented dial geometry ─────────────────────────────────────────────
// The full circle is 6 equal 60° wedges. The BOTTOM wedge is a decorative
// gap (clicking it means 0); the other 5 wedges form a 300° arc whose 6
// boundaries are exactly the 6 trait stops. Value grows clockwise: 0 at the
// gap's leading edge, 100 at its trailing edge.
export const SEG_COUNT = 6; // wedges around the circle (1 decorative)
export const SEG_DEG = 360 / SEG_COUNT; // 60°
export const SEG_ARC_START_DEG = 120; // leading boundary (value 0), screen deg
export const SEG_ARC_SWEEP_DEG = SEG_DEG * (SEG_COUNT - 1); // 300° visible

/** The screen angle of trait stop `value` (0..100) on the segmented arc. */
export function segStopAngle(value: number): number {
  return (SEG_ARC_START_DEG + (value / 100) * SEG_ARC_SWEEP_DEG) % 360;
}

/** Which trait stop a click at `angleDeg` selects on the segmented dial.
 *
 * A click anywhere inside a wedge selects that wedge — i.e. its UPPER
 * boundary value (clicking between 40 and 60 gives 60). A click in the
 * decorative bottom wedge gives 0. No snapping subtlety, no tolerance —
 * just "which of the 6 wedges is this angle in". */
export function segTraitFromAngle(angleDeg: number): number {
  const along = (angleDeg - SEG_ARC_START_DEG + 360) % 360; // 0..360 from stop 0
  if (along >= SEG_ARC_SWEEP_DEG) return 0; // inside the decorative bottom gap
  const wedge = Math.floor(along / SEG_DEG); // 0..4
  return (wedge + 1) * TRAIT_STEP; // upper boundary: 20,40,60,80,100
}

// One word per stop, so the dial shows what the number MEANS (see the
// character-matrix skill). Index = value / 20 (0,20,…,100 → 0..5).
export const TRAIT_WORDS: Record<string, readonly [string, string, string, string, string, string]> = {
  humor: ["sterile", "dry", "warm", "playful", "witty", "absurd"],
  honesty: ["courtier", "soft", "diplomatic", "frank", "candid", "no filter"],
  verbosity: ["clicks", "terse", "tight", "balanced", "generous", "lecture"],
  talkative: ["silent", "milestones", "colleague", "aloud", "narrating", "commentary"],
};

/** The semantic word for a trait at a given (snapped) value. */
export function traitWord(trait: string, value: number): string {
  const words = TRAIT_WORDS[trait];
  if (!words) return String(value);
  return words[Math.round(value / TRAIT_STEP)] ?? String(value);
}

export function speedFromAngle(angleDeg: number): number {
  const raw = SPEED_MIN + sweepFraction(angleDeg, SPEED_START_DEG, SPEED_SWEEP_DEG) * (SPEED_MAX - SPEED_MIN);
  return Math.round(raw * 20) / 20; // 0.05 steps
}

/** All Grok voices, as on the legacy dashboard. */
export const VOICES: Record<string, string> = {
  altair: "male", ara: "female", atlas: "male", aurora: "female", carina: "female", castor: "male",
  celeste: "female", cosmo: "male", eve: "female", helios: "male", helix: "male",
  iris: "female", kepler: "male", leo: "male", liora: "female", lumen: "male", luna: "female",
  lux: "male", naksh: "male", orion: "male", perseus: "male", rex: "male",
  rigel: "male", sal: "male", sirius: "male", ursa: "female", zagan: "male",
  zenith: "male",
};
