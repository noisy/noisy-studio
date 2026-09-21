import type { Utterance } from "../types";

/** System events are shared, but cannot predate the conversation they explain. */
export function conversationTimeline(all: Utterance[], agent?: string, createdAt?: number): Utterance[] {
  if (!agent) return all;
  const own = all.filter((u) => u.agent === agent && u.role !== "system");
  const start = createdAt ?? (own.length ? Math.min(...own.map((u) => u.started_at)) : Infinity);
  return all.filter((u) => u.role === "system" ? u.started_at >= start : u.agent === agent);
}
