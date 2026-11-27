import { describe, expect, it } from "vitest";
import type { DaemonStatus, Utterance } from "../types";
import {
  applyStatusOps, applyUtterancePatch, reconnectDelayMs, StateStreamDecoder, stateStreamUrl,
} from "./stateStream";

const utterance = (id: number, text = ""): Utterance => ({ id, text } as unknown as Utterance);

describe("applyStatusOps", () => {
  it("sets, adds and deletes at any depth without touching the input", () => {
    const before = { active_agent: "a", conversations: { a: { state: "live" }, b: { state: "idle" } }, gone: 1 };
    const frozen = JSON.parse(JSON.stringify(before));

    const after = applyStatusOps(before, [
      [["conversations", "a", "state"], "idle"],
      [["conversations", "c"], { state: "live" }],
      [["conversations", "b"]],
      [["active_agent"], null],
      [["gone"]],
    ]);

    expect({ after, before }).toEqual({
      after: { active_agent: null, conversations: { a: { state: "idle" }, c: { state: "live" } } },
      before: frozen,
    });
  });

  it("shares the branches a patch did not touch", () => {
    const before = { agents_meta: { a: { project: "x" } }, conversations: { a: {} } };
    const after = applyStatusOps(before, [[["conversations", "a", "state"], "live"]]);
    expect(after.agents_meta).toBe(before.agents_meta);
  });
});

describe("applyUtterancePatch", () => {
  it("drops removals, replaces edits in place and appends new ones in order", () => {
    const list = [utterance(1), utterance(2, "rec"), utterance(3)];
    const next = applyUtterancePatch(list, {
      remove: [1], upsert: [utterance(2, "done"), utterance(4), utterance(5)],
    });
    expect(next).toEqual([utterance(2, "done"), utterance(3), utterance(4), utterance(5)]);
  });

  it("takes a replacement as is", () => {
    expect(applyUtterancePatch([utterance(1)], { replace: [utterance(9)] })).toEqual([utterance(9)]);
  });
});

describe("StateStreamDecoder", () => {
  const status = { active_agent: "a" } as unknown as DaemonStatus;
  const snapshot = (extra: object = {}) =>
    JSON.stringify({ type: "snapshot", v: 2, seq: 7, status, utterances: [utterance(1)], events: [], ...extra });

  it("materializes a snapshot and then each patch in order", () => {
    const decoder = new StateStreamDecoder();
    decoder.decode(snapshot());
    const update = decoder.decode(JSON.stringify({
      type: "patch", v: 2, seq: 8,
      status: [[["active_agent"], "b"]],
      utterances: { remove: [], upsert: [utterance(2)] },
      events: [{ seq: 3, ts: 1, kind: "stt_error", detail: "x" }],
    }));
    expect(update).toEqual({
      status: { active_agent: "b" },
      utterances: [utterance(1), utterance(2)],
      events: [{ seq: 3, ts: 1, kind: "stt_error", detail: "x" }],
      fresh: false,
    });
  });

  it("asks for a resync on a gap or a patch without a snapshot", () => {
    const fresh = new StateStreamDecoder();
    const gapped = new StateStreamDecoder();
    gapped.decode(snapshot());
    expect([
      fresh.decode(JSON.stringify({ type: "patch", v: 2, seq: 1 })),
      gapped.decode(JSON.stringify({ type: "patch", v: 2, seq: 9 })),
    ]).toEqual(["resync", "resync"]);
  });

  it("reads a v1 full snapshot as a state without events", () => {
    const update = new StateStreamDecoder().decode(JSON.stringify({ type: "snapshot", status, utterances: [] }));
    expect(update).toEqual({ status, utterances: [], events: null, fresh: true });
  });

  it("refuses a newer protocol and ignores what it cannot read", () => {
    const decoder = new StateStreamDecoder();
    expect([
      decoder.decode(snapshot({ v: 3 })),
      decoder.decode("not json"),
      decoder.decode(JSON.stringify({ type: "error", reason: "boom" })),
    ]).toEqual(["unsupported", null, null]);
  });
});

describe("stateStreamUrl", () => {
  const at = (protocol: string, hostname: string, port: string) =>
    ({ protocol, hostname, port, host: port ? `${hostname}:${port}` : hostname });

  it("uses the bridge port beside the daemon and the page's origin behind vite", () => {
    expect([
      stateStreamUrl(at("http:", "127.0.0.1", "9765"), false),
      stateStreamUrl(at("http:", "127.0.0.1", "7765"), false),
      stateStreamUrl(at("http:", "localhost", "5173"), true),
    ]).toEqual([
      "ws://127.0.0.1:9766/state?v=2",
      "ws://127.0.0.1:7766/state?v=2",
      "ws://localhost:5173/state?v=2",
    ]);
  });
});

describe("reconnectDelayMs", () => {
  it("doubles from half a second up to five", () => {
    expect([0, 1, 2, 3, 4, 9].map(reconnectDelayMs)).toEqual([500, 1000, 2000, 4000, 5000, 5000]);
  });
});
