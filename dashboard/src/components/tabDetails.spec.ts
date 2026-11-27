import { describe, expect, it } from "vitest";
import { projectHue, waitLabel } from "./tabDetails";

describe("waitLabel", () => {
  it.each([
    [null, ""], [1000, "now"], [1000 - 59, "now"], [1000 - 60, "1m"], [1000 - 3599, "59m"],
    [1000 - 3600, "1h"], [1000 - 86400 * 3, "3d"], [2000, "now"],
  ])("since %s at 1000 reads %j", (since, expected) => {
    expect(waitLabel(since, 1000)).toBe(expected);
  });
});

describe("projectHue", () => {
  it("is stable per name and differs between names", () => {
    expect([projectHue("noisy-studio"), projectHue("noisy-studio") === projectHue("dataoffice")]).toEqual([projectHue("noisy-studio"), false]);
  });
});
