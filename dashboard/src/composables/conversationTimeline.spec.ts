import { expect, it } from "vitest";
import type { Utterance } from "../types";
import { conversationTimeline } from "./conversationTimeline";

const rows = [
  { id: 1, role: "system", agent: "new", started_at: 10 },
  { id: 2, role: "system", agent: "old", started_at: 20 },
  { id: 3, role: "user", agent: "new", started_at: 30 },
  { id: 4, role: "system", agent: "old", started_at: 40 },
] as Utterance[];

it("shares microphone changes only with conversations that already existed", () => {
  expect(conversationTimeline(rows, "old", 5).map((u) => u.id)).toEqual([1, 2, 4]);
  expect(conversationTimeline(rows, "new", 25).map((u) => u.id)).toEqual([3, 4]);
});
it("uses the first own utterance on older daemons and hides system history for empty conversations", () => {
  expect(conversationTimeline(rows, "new").map((u) => u.id)).toEqual([3, 4]);
  expect(conversationTimeline(rows, "empty")).toEqual([]);
});
