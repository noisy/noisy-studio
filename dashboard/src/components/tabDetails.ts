/** Small, pure rules behind a conversation row's extra lines. */

const MINUTE_S = 60;
const HOUR_S = 60 * MINUTE_S;
const DAY_S = 24 * HOUR_S;

/** How long a conversation has waited for you, compact like T3: "now",
 *  "4m", "2h", "3d". `since` and `now` are epoch seconds. */
export function waitLabel(since: number | null | undefined, now: number): string {
  if (since == null) return "";
  const waited = Math.max(0, now - since);
  if (waited < MINUTE_S) return "now";
  if (waited < HOUR_S) return `${Math.floor(waited / MINUTE_S)}m`;
  if (waited < DAY_S) return `${Math.floor(waited / HOUR_S)}h`;
  return `${Math.floor(waited / DAY_S)}d`;
}

/** A stable hue per project name, so a project keeps its badge colour
 *  across reloads and machines without any setup. */
export function projectHue(project: string): number {
  let hash = 0;
  for (const char of project) hash = (hash * 31 + char.codePointAt(0)!) >>> 0;
  return hash % 360;
}

const MODIFIER_GLYPHS: Record<string, string> = { ctrl: "⌃", control: "⌃", alt: "⌥", option: "⌥", cmd: "⌘", command: "⌘", shift: "⇧" };

/** A stored chord ("F16", "ctrl+alt+g") as a compact key-cap label
 *  ("F16", "⌃⌥G"). Empty for no chord. */
export function chordLabel(chord: string | null | undefined): string {
  if (!chord) return "";
  return chord.split("+").map((part) => MODIFIER_GLYPHS[part.toLowerCase()] ?? part.toUpperCase()).join("");
}
