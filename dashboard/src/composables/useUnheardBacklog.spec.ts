import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import type { DaemonStatus, Utterance } from "../types";

const calls: string[] = [];
vi.mock("../api/client", () => ({
  setVoiceMuted: vi.fn(async (muted: boolean) => { calls.push(`voice-muted ${muted}`); }),
  setAgentMuted: vi.fn(async (agent: string, muted: boolean) => { calls.push(`agent-muted ${agent} ${muted}`); }),
  skipUnheard: vi.fn(async (agent?: string) => { calls.push(`skip ${agent}`); return { skipped: 2 }; }),
  speakText: vi.fn(async (_text: string, id: number) => { calls.push(`replay #${id}`); }),
}));

import { useUnheardBacklog } from "./useUnheardBacklog";

function card(id: number, status: string, committedAt: number): Utterance {
  return {
    id, role: "claude", status, text: `message ${id}`, detail: "", cost_usd: 0,
    agent: "alpha", started_at: committedAt, updated_at: committedAt, committed_at: committedAt,
  };
}

function backlog(mutedAgents: string[]) {
  const status = ref({ muted_agents: mutedAgents } as DaemonStatus);
  const utterances = ref([
    card(2, "unheard — conversation muted", 20),
    card(1, "unheard — conversation muted", 10),
    card(3, "played", 30),
  ]);
  return useUnheardBacklog(status, utterances, ref("alpha"));
}

beforeEach(() => {
  calls.length = 0;
});

describe("useUnheardBacklog", () => {
  it("catches up after unmuting, replaying only parked cards oldest first", async () => {
    await backlog(["alpha"]).catchUp();

    expect(calls).toEqual(["voice-muted false", "agent-muted alpha false", "replay #1", "replay #2"]);
  });

  it("skips the backlog first, then unmutes so the next message plays live", async () => {
    await backlog(["alpha"]).skipAll();

    expect(calls).toEqual(["skip alpha", "voice-muted false", "agent-muted alpha false"]);
  });
});
