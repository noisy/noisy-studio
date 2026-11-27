import { describe, expect, it } from "vitest";
import { groupAgents, moveProject, moveWithinProject, orderAgents, projectOrder, settledRows } from "./agentOrder";

// Two projects interleaved by arrival, one session without a project, one
// ended session of the first project.
const meta = {
  studio1: { online: true, activated_at: 1, project: "noisy-studio" },
  web1: { online: true, activated_at: 2, project: "website" },
  loose: { online: true, activated_at: 3, project: null },
  studio2: { online: true, activated_at: 4, project: "noisy-studio" },
  ended: { online: false, activated_at: 0, offline_since: 9, project: "noisy-studio" },
};
const names = Object.keys(meta);

describe("orderAgents", () => {
  it("groups online conversations by project, no-project last, then the ended ones", () => {
    expect(orderAgents(names, meta)).toEqual(["studio1", "studio2", "web1", "loose", "ended"]);
  });

  it("keeps the legacy flat arrival order for a daemon without projects", () => {
    expect(orderAgents(["b", "a"], { a: { activated_at: 1 }, b: { activated_at: 2 } })).toEqual(["a", "b"]);
  });
});

describe("projectOrder", () => {
  it("orders projects by their first conversation, ended ones included", () => {
    expect(projectOrder(names, meta)).toEqual(["noisy-studio", "website", null]);
  });

  it("does not move a project when its first session ends", () => {
    const studioEnded = { ...meta, studio1: { ...meta.studio1, online: false, offline_since: 10 } };
    expect(projectOrder(names, studioEnded)).toEqual(["noisy-studio", "website", null]);
  });
});

describe("groupAgents", () => {
  it("lists each project's live conversations and sends ended ones to Settled", () => {
    expect(groupAgents(names, meta)).toEqual({
      projects: [
        { project: "noisy-studio", names: ["studio1", "studio2"] },
        { project: "website", names: ["web1"] },
        { project: null, names: ["loose"] },
      ],
      settled: ["ended"],
    });
  });

  it("never re-sorts on speaking, queued messages or work", () => {
    const quiet = groupAgents(names, meta);
    const busy = groupAgents(names, meta, { speaking: ["web1"], queued: { loose: 3, studio2: 1 } });
    expect(busy).toEqual(quiet);
  });

  it("keeps an ended session in its project while it waits for you or is in sight", () => {
    const more = {
      ...meta,
      unheard: { online: false, offline_since: 8, project: "website" },
      viewed: { online: false, offline_since: 7, project: null },
    };
    const groups = groupAgents(Object.keys(more), more, { queued: { unheard: 1 }, keepInSight: ["viewed", null] });
    expect(groups).toEqual({
      projects: [
        { project: "noisy-studio", names: ["studio1", "studio2"] },
        { project: "website", names: ["web1", "unheard"] },
        { project: null, names: ["loose", "viewed"] },
      ],
      settled: ["ended"],
    });
  });

  it("keeps an ended session the user restored in its project", () => {
    const restored = { ...meta, ended: { ...meta.ended, kept: true } };
    const { projects, settled } = groupAgents(names, restored);
    expect([projects[0], settled]).toEqual([{ project: "noisy-studio", names: ["studio1", "studio2", "ended"] }, []]);
  });

  it("treats conversations without metadata as online, without a project (legacy daemon)", () => {
    expect(groupAgents(["a", "b"])).toEqual({ projects: [{ project: null, names: ["a", "b"] }], settled: [] });
  });
});

describe("moveWithinProject", () => {
  it("reshuffles only the project's own slots and keeps every other position", () => {
    expect(moveWithinProject(names, meta, "studio2", "studio1"))
      .toEqual(["ended", "studio2", "web1", "loose", "studio1"]);
  });

  it("refuses a drop onto another project", () => {
    expect(moveWithinProject(names, meta, "studio1", "web1")).toBeNull();
  });
});


describe("moveProject", () => {
  const order = { a1: { manual_pos: 0, project: "a" }, b1: { manual_pos: 1, project: "b" }, a2: { manual_pos: 2, project: "a" }, c1: { manual_pos: 3, project: "c" } };
  const keys = Object.keys(order);

  it("lays the projects out whole in the new sequence, each keeping its inner order", () => {
    expect([moveProject(keys, order, "c", "a"), moveProject(keys, order, "a", "c")]).toEqual([
      ["c1", "a1", "a2", "b1"],
      ["b1", "c1", "a1", "a2"],
    ]);
  });

  it("ignores a drop on itself or an unknown project", () => {
    expect([moveProject(keys, order, "a", "a"), moveProject(keys, order, "a", "zzz")]).toEqual([null, null]);
  });
});

describe("settledRows", () => {
  const hidden = (name: string, at: number) => ({
    name, label: name, project: null, branch: null, last_active_at: at, ended: true, talk_key: null,
  });
  const endedMeta = { gone1: { online: false, offline_since: 30 }, gone2: { online: false, offline_since: 10 } };

  it("merges ended sessions and settled conversations, newest first, counting the daemon's total", () => {
    const settled = { total: 7, items: [hidden("s1", 40), hidden("s2", 20)] };
    expect(settledRows(["gone2", "gone1"], endedMeta, settled)).toEqual({
      rows: [
        { name: "s1", hidden: settled.items[0] },
        { name: "gone1", hidden: null },
        { name: "s2", hidden: settled.items[1] },
        { name: "gone2", hidden: null },
      ],
      total: 9,
      older: 5,
    });
  });

  it("caps the rows and says how many older ones it left out", () => {
    const settled = { total: 2, items: [hidden("s1", 40), hidden("s2", 20)] };
    const { rows, older } = settledRows(["gone1"], endedMeta, settled, 2);
    expect([rows.map((row) => row.name), older]).toEqual([["s1", "gone1"], 1]);
  });

  it("lists a conversation the daemon sends twice only once", () => {
    const settled = { total: 1, items: [hidden("gone1", 50)] };
    expect(settledRows(["gone1"], endedMeta, settled)).toEqual({ rows: [{ name: "gone1", hidden: null }], total: 1, older: 0 });
  });

  it("works with a daemon that sends no settled conversations", () => {
    expect(settledRows(["gone1"], endedMeta, undefined)).toEqual({ rows: [{ name: "gone1", hidden: null }], total: 1, older: 0 });
  });
});
