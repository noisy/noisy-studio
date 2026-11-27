import { describe, expect, it } from "vitest";
import { BENCH, DESK, LEGACY, LONG, NOW, STUDIO, WEBSITE } from "./fixtures";
import { arrange, clockLabel, demandsOf, runningOf } from "./orgModel";
import { parseSnooze, snoozePresets } from "./snooze";

const local = (day: number, hour: number, minute = 0) => Math.floor(new Date(2026, 10, day, hour, minute).getTime() / 1000);

describe("demandsOf", () => {
  it("counts blocked and to-review agents, not a manager that merely waits for its next order", () => {
    expect(demandsOf(STUDIO, NOW).map((demand) => demand.kind)).toEqual(["blocked", "review"]);
  });

  it("adds unheard messages and a broken cap", () => {
    expect(demandsOf(BENCH, NOW).map((demand) => demand.kind)).toEqual(["listen", "overCap"]);
  });

  it("holds back a snoozed manager's messages until it wakes", () => {
    expect([demandsOf(LONG, NOW).length, demandsOf(LONG, local(27, 18, 1)).length]).toEqual([0, 1]);
  });

  it("finds nothing on an idle project", () => {
    expect(demandsOf(WEBSITE, NOW)).toEqual([]);
  });
});

describe("runningOf", () => {
  it("counts working and paused agents and working managers", () => {
    expect(runningOf(BENCH)).toEqual({ agents: 3, paused: 0, managers: 1 });
  });
});

describe("arrange", () => {
  it("keeps the given order, gathers legacy conversations under No project and settles the rest", () => {
    const arranged = arrange(DESK);
    expect({
      projects: arranged.projects.map((project) => project.name),
      unassigned: arranged.unassigned?.managers.map((manager) => manager.id),
      settled: arranged.settled.map(({ manager }) => manager.id),
    }).toEqual({
      projects: ["noisy-studio", "bucky", "stt-bench", "website", "noisy-studio-website-assets"],
      unassigned: ["fitatu"],
      settled: ["deck", "i172"],
    });
  });

  it("moves a focused project to the top without reordering the others", () => {
    const focused = DESK.map((project) => (project.id === WEBSITE.id ? { ...project, focused: true } : project));
    expect(arrange(focused).projects.map((project) => project.name)).toEqual(
      ["website", "noisy-studio", "bucky", "stt-bench", "noisy-studio-website-assets"],
    );
  });

  it("has no No project group when every conversation has a folder", () => {
    expect(arrange(DESK.filter((project) => project !== LEGACY)).unassigned).toBeNull();
  });
});

describe("snooze", () => {
  const friday = local(27, 11, 42);

  it("offers presets with their wake times, this evening only while it is ahead", () => {
    const label = (now: number) => snoozePresets(now).map((preset) => `${preset.label} ${clockLabel(preset.at, now)}`);
    expect([label(friday), label(local(27, 17, 30))]).toEqual([
      ["1 hour 12:42", "3 hours 14:42", "This evening 18:00", "Tomorrow morning Sat 09:00"],
      ["1 hour 18:30", "3 hours 20:30", "Tomorrow morning Sat 09:00"],
    ]);
  });

  it.each([
    ["45m", local(27, 12, 27)],
    ["2h", local(27, 13, 42)],
    ["1.5h", local(27, 13, 12)],
    ["14:30", local(27, 14, 30)],
    ["9:00", local(28, 9, 0)],
    ["tomorrow", local(28, 9, 0)],
    ["tomorrow 14:00", local(28, 14, 0)],
    ["mon 8:30", local(30, 8, 30)],
    ["fri 9:00", local(34, 9, 0)],
    ["Friday 15", local(27, 15, 0)],
  ])("reads %s", (input, expected) => {
    expect(parseSnooze(input, friday)).toBe(expected);
  });

  it.each(["", "soon", "25:00", "0m", "fri 9:75"])("refuses %j", (input) => {
    expect(parseSnooze(input, friday)).toBeNull();
  });
});
