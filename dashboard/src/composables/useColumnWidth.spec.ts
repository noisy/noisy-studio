import { beforeEach, describe, expect, it } from "vitest";
import { clampColumnWidth, COLUMN_WIDTH_LIMITS, useColumnWidth } from "./useColumnWidth";

describe("useColumnWidth", () => {
  beforeEach(() => localStorage.clear());

  it("clamps to the limits", () => {
    expect([clampColumnWidth(10), clampColumnWidth(300.4), clampColumnWidth(5000)]).toEqual([COLUMN_WIDTH_LIMITS.min, 300, COLUMN_WIDTH_LIMITS.max]);
  });

  it("remembers the width per browser and resets to the default", () => {
    useColumnWidth().set(400);
    const reopened = useColumnWidth();
    const remembered = reopened.width.value;
    reopened.reset();

    expect([remembered, useColumnWidth().width.value]).toEqual([400, COLUMN_WIDTH_LIMITS.default]);
  });
});
