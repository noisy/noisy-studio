/** Snooze choices: presets that resolve to a visible wake time, and the
 *  custom field's small grammar ("45m", "2h", "14:30", "fri 9:00",
 *  "tomorrow"). All times are local; `now` and results are epoch seconds. */

const HOUR_S = 3600;
const EVENING_HOUR = 18;
const MORNING_HOUR = 9;
const WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

export interface SnoozePreset { label: string; at: number }

const atLocal = (now: number, dayOffset: number, hour: number, minute = 0) => {
  const date = new Date(now * 1000);
  date.setDate(date.getDate() + dayOffset);
  date.setHours(hour, minute, 0, 0);
  return Math.floor(date.getTime() / 1000);
};

/** 1 hour, 3 hours, this evening (only while it is still ahead) and
 *  tomorrow morning. */
export function snoozePresets(now: number): SnoozePreset[] {
  const evening = atLocal(now, 0, EVENING_HOUR);
  return [
    { label: "1 hour", at: now + HOUR_S },
    { label: "3 hours", at: now + 3 * HOUR_S },
    ...(evening > now + HOUR_S ? [{ label: "This evening", at: evening }] : []),
    { label: "Tomorrow morning", at: atLocal(now, 1, MORNING_HOUR) },
  ];
}

/** The custom field. Returns null for anything it does not understand, so
 *  the menu can say so instead of guessing. */
export function parseSnooze(input: string, now: number): number | null {
  const text = input.trim().toLowerCase();
  const duration = text.match(/^(\d+(?:\.\d+)?)\s*(m|min|h|hr|d)$/);
  if (duration) {
    const unit = { m: 60, min: 60, h: HOUR_S, hr: HOUR_S, d: 24 * HOUR_S }[duration[2]]!;
    const seconds = Math.round(Number(duration[1]) * unit);
    return seconds > 0 ? now + seconds : null;
  }
  const day = text.match(/^(tomorrow|mon|tue|wed|thu|fri|sat|sun)[a-z]*(?:\s+(\d{1,2})(?::(\d{2}))?)?$/);
  if (day) {
    const [hour, minute] = [Number(day[2] ?? MORNING_HOUR), Number(day[3] ?? 0)];
    if (hour > 23 || minute > 59) return null;
    if (day[1] === "tomorrow") return atLocal(now, 1, hour, minute);
    const today = new Date(now * 1000).getDay();
    let offset = (WEEKDAYS.indexOf(day[1]) - today + 7) % 7;
    if (offset === 0 && atLocal(now, 0, hour, minute) <= now) offset = 7;
    return atLocal(now, offset, hour, minute);
  }
  const time = text.match(/^(\d{1,2}):(\d{2})$/);
  if (time) {
    const [hour, minute] = [Number(time[1]), Number(time[2])];
    if (hour > 23 || minute > 59) return null;
    const today = atLocal(now, 0, hour, minute);
    return today > now ? today : atLocal(now, 1, hour, minute);
  }
  return null;
}
