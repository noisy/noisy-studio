import { ref } from "vue";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { conversationCharacter } from "./conversationCharacter";
import { canonicalCharacter } from "../character";
import { getCharacter, setCharacter } from "../api/client";
import type { Character, DaemonStatus } from "../types";

vi.mock("../api/client", () => ({ getCharacter: vi.fn(), setCharacter: vi.fn() }));
const voice = (value: string) => canonicalCharacter({ voice: value, humor: 50, honesty: 100, speed: 1 });
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function flush() { for (let i = 0; i < 8; i++) await Promise.resolve(); }
function setup() {
  const selected = ref<string | null>("a1");
  const report = vi.fn();
  const state = conversationCharacter(selected, null, vi.fn(), report);
  const snapshot = { agent_characters: { a1: voice("leo"), a2: voice("eve") } } as unknown as DaemonStatus;
  state.apply(snapshot, Date.now());
  return { state, selected, snapshot, report };
}
beforeEach(() => vi.resetAllMocks());

describe("conversation character changes", () => {
  it("previews a choice, ignores old snapshots, and confirms the saved response", async () => {
    const { state, snapshot } = setup();
    const save = deferred<Character>();
    vi.mocked(setCharacter).mockReturnValue(save.promise);
    state.change({ voice: "iris" });
    state.apply(snapshot, 0);
    expect([state.character.value?.voice, state.pending.value]).toEqual(["iris", true]);
    save.resolve(voice("rex"));
    await flush();
    state.apply(snapshot, 0);
    expect([state.character.value?.voice, state.pending.value]).toEqual(["rex", false]);
  });

  it("rolls back failed changes and reports the error", async () => {
    const { state, report } = setup();
    vi.mocked(setCharacter).mockRejectedValue(new Error("offline"));
    state.change({ voice: "iris" });
    await flush();
    expect([state.character.value?.voice, state.pending.value, state.error.value]).toEqual([
      "leo", false, "Could not save character settings: offline",
    ]);
    expect(report).toHaveBeenCalledWith(state.error.value);
  });

  it("serializes rapid edits and preserves the latest preview across earlier responses", async () => {
    const { state } = setup();
    const first = deferred<Character>();
    const second = deferred<Character>();
    vi.mocked(setCharacter).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    state.change({ voice: "iris" });
    state.change({ humor: 80 });
    expect(setCharacter).toHaveBeenCalledTimes(1);
    first.resolve(voice("iris"));
    await flush();
    expect([state.character.value?.voice, state.character.value?.humor, state.pending.value]).toEqual(["iris", 80, true]);
    second.reject(new Error("offline"));
    await flush();
    expect(state.character.value).toEqual(voice("iris"));
  });

  it("does not repaint another tab when a save settles", async () => {
    const { state, selected } = setup();
    const save = deferred<Character>();
    vi.mocked(setCharacter).mockReturnValue(save.promise);
    state.change({ voice: "iris" });
    selected.value = "a2";
    save.resolve(voice("iris"));
    await flush();
    expect(state.character.value?.voice).toBe("eve");
    selected.value = "a1";
    expect(state.character.value?.voice).toBe("iris");
  });

  it("receives external character changes on the same tab", () => {
    const { state, snapshot } = setup();
    state.apply({ ...snapshot, agent_characters: { a1: voice("iris") } }, Date.now());
    expect(state.character.value?.voice).toBe("iris");
    expect(getCharacter).not.toHaveBeenCalled();
  });

  it("ignores a stale fallback read after a newer snapshot", async () => {
    const { state, selected, snapshot } = setup();
    const read = deferred<Character>();
    vi.mocked(getCharacter).mockReturnValue(read.promise);
    state.apply({ agent_voices: { a1: "iris" } } as unknown as DaemonStatus, Date.now());
    selected.value = "a2";
    state.apply({ ...snapshot, agent_characters: { a1: voice("rex"), a2: voice("eve") } }, Date.now());
    read.resolve(voice("iris"));
    await flush();
    expect(state.character.value?.voice).toBe("eve");
    selected.value = "a1";
    expect(state.character.value?.voice).toBe("rex");
  });
});
