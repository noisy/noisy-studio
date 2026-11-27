import { describe, expect, it } from "vitest";
import { sectionAgents } from "./agentOrder";

const meta = {
  idle: { online: true, activated_at: 1 },
  busy: { online: true, activated_at: 2 },
  talking: { online: true, activated_at: 3 },
  backlog: { online: true, activated_at: 4 },
  ended: { online: false, activated_at: 0, offline_since: 9 },
};
const names = Object.keys(meta);

describe("sectionAgents", () => {
  it("keeps your turn on top, sends sustained work and ended sessions down", () => {
    expect(sectionAgents(names, meta, { working: ["busy"] })).toEqual({
      yourTurn: ["idle", "talking", "backlog"],
      working: ["busy"],
      settled: ["ended"],
    });
  });

  it("pulls a working conversation back up the moment it speaks or queues a message", () => {
    const sections = sectionAgents(names, meta, {
      working: ["busy", "talking", "backlog"],
      speaking: ["talking"],
      queued: { backlog: 2 },
    });
    expect(sections.working).toEqual(["busy"]);
    expect(sections.yourTurn).toEqual(["idle", "talking", "backlog"]);
  });

  it("treats conversations without metadata as online (legacy daemon)", () => {
    expect(sectionAgents(["a", "b"])).toEqual({ yourTurn: ["a", "b"], working: [], settled: [] });
  });
});
