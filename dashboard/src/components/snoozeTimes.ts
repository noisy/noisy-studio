/** When a snoozed conversation comes back: the menu's choices and how a
 *  wake time reads. Local time throughout - "tomorrow" is the user's
 *  tomorrow. Pure, so the calendar rules are tested without a clock. */

const HOUR_MS = 3_600_000;
const SNOOZE_HOURS = [1, 3, 6];
const MORNING_HOUR = 9; // "Tomorrow" and "Next week" wake at 09:00
const MONDAY = 1; // Date#getDay
const DAYS_IN_WEEK = 7;
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export interface SnoozeOption {
  label: string;
  until: number; // epoch s
}

/** 1 hour, 3 hours, 6 hours, Tomorrow (09:00 the next day) and Next week
 *  (the coming Monday, 09:00 - a week ahead when today is Monday). */
export function snoozeOptions(now: Date): SnoozeOption[] {
  const daysToMonday = (DAYS_IN_WEEK + MONDAY - now.getDay()) % DAYS_IN_WEEK || DAYS_IN_WEEK;
  return [
    ...SNOOZE_HOURS.map((hours) => ({
      label: hours === 1 ? "1 hour" : `${hours} hours`,
      until: toEpoch(new Date(now.getTime() + hours * HOUR_MS)),
    })),
    { label: "Tomorrow", until: toEpoch(morningIn(now, 1)) },
    { label: "Next week", until: toEpoch(morningIn(now, daysToMonday)) },
  ];
}

/** A wake time as the row and the menu show it: "15:30" today, else with
 *  its weekday, "Mon 09:00". */
export function wakeLabel(until: number, now: Date): string {
  const wake = new Date(until * 1000);
  const time = `${pad(wake.getHours())}:${pad(wake.getMinutes())}`;
  return wake.toDateString() === now.toDateString() ? time : `${WEEKDAYS[wake.getDay()]} ${time}`;
}

// The calendar day `days` after `now`, at 09:00 local (DST-safe: the Date
// constructor normalises the day overflow, not a fixed 24h step).
function morningIn(now: Date, days: number): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + days, MORNING_HOUR);
}

const toEpoch = (date: Date) => Math.floor(date.getTime() / 1000);
const pad = (value: number) => String(value).padStart(2, "0");
