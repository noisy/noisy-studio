import { describe, expect, it } from "vitest";
import { snoozeOptions, wakeLabel } from "./snoozeTimes";

// Local-time dates, so the expectations hold in any time zone.
const at = (month: number, day: number, hour: number, minute = 0) => new Date(2026, month - 1, day, hour, minute);
const epoch = (date: Date) => Math.floor(date.getTime() / 1000);

describe("snoozeOptions", () => {
  it("offers 1, 3 and 6 hours, tomorrow 09:00 and next Monday 09:00", () => {
    const wednesday = at(11, 25, 14, 30);
    expect(snoozeOptions(wednesday)).toEqual([
      { label: "1 hour", until: epoch(at(11, 25, 15, 30)) },
      { label: "3 hours", until: epoch(at(11, 25, 17, 30)) },
      { label: "6 hours", until: epoch(at(11, 25, 20, 30)) },
      { label: "Tomorrow", until: epoch(at(11, 26, 9)) },
      { label: "Next week", until: epoch(at(11, 30, 9)) },
    ]);
  });

  it("crosses midnight and the month end", () => {
    const lateLastDay = at(11, 30, 23, 30); // a Monday
    const [hour, , six, tomorrow, nextWeek] = snoozeOptions(lateLastDay);
    expect([hour.until, six.until, tomorrow.until, nextWeek.until]).toEqual([
      epoch(at(12, 1, 0, 30)), epoch(at(12, 1, 5, 30)), epoch(at(12, 1, 9)), epoch(at(12, 7, 9)),
    ]);
  });

  it("takes Tomorrow to mean the next calendar day even just after midnight", () => {
    expect(snoozeOptions(at(11, 26, 0, 30))[3].until).toBe(epoch(at(11, 27, 9)));
  });

  it("goes to the coming Monday from a Sunday, and a week ahead from a Monday", () => {
    expect([snoozeOptions(at(11, 29, 20))[4].until, snoozeOptions(at(11, 23, 8))[4].until])
      .toEqual([epoch(at(11, 30, 9)), epoch(at(11, 30, 9))]);
  });
});

describe("wakeLabel", () => {
  it("shows the time alone today and the weekday on another day", () => {
    const now = at(11, 25, 23, 30);
    expect([wakeLabel(epoch(at(11, 25, 23, 45)), now), wakeLabel(epoch(at(11, 26, 0, 30)), now), wakeLabel(epoch(at(11, 30, 9)), now)])
      .toEqual(["23:45", "Thu 00:30", "Mon 09:00"]);
  });
});
