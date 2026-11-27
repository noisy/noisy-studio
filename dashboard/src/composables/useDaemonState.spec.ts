import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import type { DaemonState } from "./useDaemonState";
import { resetDaemonState, useDaemonState } from "./useDaemonState";

const STATUS = {
  active_agent: "agent-a",
  agents: { "agent-a": 1, "agent-b": 1 },
  queued: 0,
};

function jsonResponse(body: unknown) {
  return { ok: true, json: () => Promise.resolve(body) };
}

function mountComposable(pollMs = 400): { state: DaemonState; unmount: () => void } {
  let state!: DaemonState;
  const Host = defineComponent({
    setup() {
      state = useDaemonState(pollMs);
      return () => h("div");
    },
  });
  const wrapper = mount(Host);
  return { state, unmount: () => wrapper.unmount() };
}

async function flush() {
  // Let the chained awaits inside tick() settle (fetch → json → assignment,
  // three sequential requests deep).
  for (let i = 0; i < 24; i++) await Promise.resolve();
}

/** Stands in for the browser WebSocket: records what was opened and lets a
 * test deliver messages or drop the connection. Never opens on its own, so a
 * test that ignores it exercises the polling fallback. */
class FakeSocket {
  static opened: FakeSocket[] = [];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) {
    FakeSocket.opened.push(this);
  }
  deliver(message: object) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
  close() {
    if (this.closed) return;
    this.closed = true;
    this.onclose?.();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeSocket.opened = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(() => {
  resetDaemonState(); // the state is now app-wide; each case starts clean
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useDaemonState", () => {
  it("polls status, utterances and character for the viewed agent", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.startsWith("/status")) return jsonResponse(STATUS);
      if (url.startsWith("/utterances"))
        return jsonResponse({ utterances: [{ id: 1, agent: "agent-a" }, { id: 2, agent: "agent-b" }] });
      if (url.startsWith("/events")) return jsonResponse({ events: [] });
      return jsonResponse({ character: { voice: "altair" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { state, unmount } = mountComposable();
    await flush();

    expect(state.status.value?.active_agent).toBe("agent-a");
    expect(state.viewedAgent.value).toBe("agent-a"); // follows active until pinned
    expect(state.utterances.value).toEqual([{ id: 1, agent: "agent-a" }]); // viewed slice
    expect(state.allUtterances.value).toHaveLength(2); // full list for badges
    expect(state.character.value?.voice).toBe("altair");
    expect(state.offline.value).toBe(false);
    unmount();
  });

  it("collects only error events from the daemon's event stream", async () => {
    let served = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.startsWith("/status")) return jsonResponse(STATUS);
        if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
        if (url.startsWith("/events")) {
          if (served) return jsonResponse({ events: [] });
          served = true;
          return jsonResponse({
            events: [
              { seq: 1, ts: 1, kind: "transcript", detail: "hello" },
              { seq: 2, ts: 2, kind: "stt_error", detail: "HTTP 500" },
            ],
          });
        }
        return jsonResponse({ character: {} });
      }),
    );

    const { state, unmount } = mountComposable();
    await flush();

    expect(state.errors.value).toEqual([
      { seq: 2, ts: 2, kind: "stt_error", detail: "HTTP 500" },
    ]);
    unmount();
  });

  it("clears displayed warnings without replaying them and displays new failures", async () => {
    const first = { seq: 1, ts: 1, kind: "voice_identity_error", detail: "Missing session" };
    const second = { seq: 2, ts: 2, kind: "voice_identity_error", detail: "Missing session again" };
    const events = [first];
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.startsWith("/status")) return jsonResponse(STATUS);
      if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
      if (url.startsWith("/events")) {
        const since = Number(new URL(url, "http://localhost").searchParams.get("since"));
        return jsonResponse({ events: events.filter(event => event.seq > since) });
      }
      return jsonResponse({ character: {} });
    }));
    const { state, unmount } = mountComposable();
    await flush();
    expect(state.errors.value).toEqual([first]);
    state.clearErrors();
    await vi.advanceTimersByTimeAsync(400);
    await flush();
    expect(state.errors.value).toEqual([]);
    events.push(second);
    await vi.advanceTimersByTimeAsync(400);
    await flush();
    expect(state.errors.value).toEqual([second]);
    unmount();
  });

  it("flags a status change the chat machine cannot explain", async () => {
    const card = { id: 7, role: "user", agent: "agent-a", started_at: 100 };
    let poll = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.startsWith("/status")) return jsonResponse(STATUS);
        if (url.startsWith("/utterances")) {
          poll += 1;
          // Legal hop first, then a resurrection no event chain explains.
          const status = poll === 1 ? "recording…" : poll === 2 ? "delivered to Claude" : "recording…";
          return jsonResponse({ utterances: [{ ...card, status }] });
        }
        if (url.startsWith("/events")) return jsonResponse({ events: [] });
        return jsonResponse({ character: {} });
      }),
    );
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const { state, unmount } = mountComposable();
    await flush();
    await vi.advanceTimersByTimeAsync(400); // recording → delivered: legal path
    await flush();
    expect(state.errors.value).toEqual([]);

    await vi.advanceTimersByTimeAsync(400); // delivered → recording: resurrection
    await flush();
    expect(state.errors.value).toHaveLength(1);
    expect(state.errors.value[0].kind).toBe("machine_violation");
    expect(state.errors.value[0].detail).toContain('"delivered to Claude" → "recording…"');
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
    unmount();
  });

  it("flips offline when the daemon is unreachable and back when it answers", async () => {
    let failing = true;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (failing) throw new TypeError("fetch failed");
        if (url.startsWith("/status")) return jsonResponse(STATUS);
        if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
        if (url.startsWith("/events")) return jsonResponse({ events: [] });
        return jsonResponse({ character: {} });
      }),
    );

    const { state, unmount } = mountComposable();
    await flush();
    expect(state.offline.value).toBe(true);

    failing = false;
    await vi.advanceTimersByTimeAsync(400);
    await flush();
    expect(state.offline.value).toBe(false);
    unmount();
  });

  it("selectAgent posts the switch and then follows the daemon's answer", async () => {
    let active = "agent-a";
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.startsWith("/status")) return jsonResponse({ ...STATUS, active_agent: active });
      if (url.startsWith("/active-agent")) {
        active = JSON.parse(String(init?.body)).name;
        return jsonResponse({ active_agent: active });
      }
      if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
      if (url.startsWith("/events")) return jsonResponse({ events: [] });
      return jsonResponse({ character: {} });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { state, unmount } = mountComposable();
    await flush();
    state.selectAgent("agent-b");

    expect(state.viewedAgent.value).toBe("agent-b"); // optimistic preview
    expect(fetchMock).toHaveBeenCalledWith("/active-agent", {
      method: "POST",
      body: JSON.stringify({ name: "agent-b" }),
    });
    await flush();
    await vi.advanceTimersByTimeAsync(400);
    await flush();
    expect(state.viewedAgent.value).toBe("agent-b"); // the daemon agreed
    unmount();
  });

  /* #65: the dashboard and the desktop companion are separate Electron
   * windows, so separate copies of this module. The only state they share is
   * the daemon's active_agent - a selection made in the OTHER window arrives
   * here as a status change and must win over anything chosen locally. */
  it("follows a switch made elsewhere, even after a local selection", async () => {
    let active = "agent-a";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.startsWith("/status")) return jsonResponse({ ...STATUS, active_agent: active });
        if (url.startsWith("/active-agent")) {
          active = JSON.parse(String(init?.body)).name;
          return jsonResponse({ active_agent: active });
        }
        if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
        if (url.startsWith("/events")) return jsonResponse({ events: [] });
        return jsonResponse({ character: {} });
      }),
    );

    const { state, unmount } = mountComposable();
    await flush();
    state.selectAgent("agent-b");
    await flush();
    expect(state.viewedAgent.value).toBe("agent-b");

    active = "agent-a"; // the other window clicked its tab
    await vi.advanceTimersByTimeAsync(400);
    await flush();
    expect(state.viewedAgent.value).toBe("agent-a");
    unmount();
  });

  it("shows who the daemon actually gave the mic to when it refuses a click", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.startsWith("/status")) return jsonResponse({ ...STATUS, active_agent: "agent-a" });
        if (url.startsWith("/active-agent")) return jsonResponse({ active_agent: "agent-a" });
        if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
        if (url.startsWith("/events")) return jsonResponse({ events: [] });
        return jsonResponse({ character: {} });
      }),
    );

    const { state, unmount } = mountComposable();
    await flush();
    state.selectAgent("agent-gone");
    expect(state.viewedAgent.value).toBe("agent-gone");
    await flush();
    expect(state.viewedAgent.value).toBe("agent-a");
    unmount();
  });
});

describe("useDaemonState over the state stream", () => {
  const snapshot = {
    type: "snapshot", v: 2, seq: 1, status: STATUS,
    utterances: [{ id: 1, agent: "agent-a" }],
    events: [{ seq: 4, ts: 1, kind: "stt_error", detail: "old failure" }],
  };

  function countingFetch() {
    return vi.fn(async (url: string) => {
      if (url.startsWith("/status")) return jsonResponse({ ...STATUS, active_agent: "agent-b" });
      if (url.startsWith("/utterances")) return jsonResponse({ utterances: [] });
      if (url.startsWith("/events")) return jsonResponse({ events: [] });
      return jsonResponse({ character: {} });
    });
  }
  const stateFetches = (fetchMock: ReturnType<typeof countingFetch>) =>
    fetchMock.mock.calls.filter(([url]) => /^\/(status|utterances|events)/.test(url)).length;

  it("renders the pushed state and stops polling while the stream is live", async () => {
    const fetchMock = countingFetch();
    vi.stubGlobal("fetch", fetchMock);
    const { state, unmount } = mountComposable();
    await flush();
    const socket = FakeSocket.opened[0];
    socket.deliver(snapshot);
    socket.deliver({
      type: "patch", v: 2, seq: 2,
      status: [[["queued"], 3]],
      utterances: { remove: [], upsert: [{ id: 2, agent: "agent-a" }] },
      events: [{ seq: 5, ts: 2, kind: "tts_error", detail: "new failure" }],
    });
    const fetchesWhileLive = stateFetches(fetchMock);
    await vi.advanceTimersByTimeAsync(4000);
    await flush();

    expect({
      url: socket.url,
      queued: state.status.value?.queued,
      viewed: state.utterances.value.map((u) => u.id),
      errors: state.errors.value.map((e) => e.detail),
      extraFetches: stateFetches(fetchMock) - fetchesWhileLive,
    }).toEqual({
      url: "ws://localhost:3000/state?v=2",
      queued: 3,
      viewed: [1, 2],
      errors: ["old failure", "new failure"],
      extraFetches: 0,
    });
    unmount();
  });

  it("falls back to polling at once when the stream drops, then reconnects", async () => {
    const fetchMock = countingFetch();
    vi.stubGlobal("fetch", fetchMock);
    const { state, unmount } = mountComposable();
    await flush();
    FakeSocket.opened[0].deliver(snapshot);
    FakeSocket.opened[0].close();
    await flush();
    const polledActive = state.status.value?.active_agent;
    await vi.advanceTimersByTimeAsync(500);
    FakeSocket.opened[1].deliver({ ...snapshot, seq: 9 });
    await flush();

    expect([polledActive, FakeSocket.opened.length, state.status.value?.active_agent])
      .toEqual(["agent-b", 2, "agent-a"]);
    unmount();
  });

  it("drops a stream that skipped a patch and takes a fresh snapshot", async () => {
    vi.stubGlobal("fetch", countingFetch());
    const { unmount } = mountComposable();
    await flush();
    const first = FakeSocket.opened[0];
    first.deliver(snapshot);
    first.deliver({ type: "patch", v: 2, seq: 5, status: [[["queued"], 1]] });
    await vi.advanceTimersByTimeAsync(500);

    expect([first.closed, FakeSocket.opened.length]).toEqual([true, 2]);
    unmount();
  });

  it("keeps pulling events beside a v1 stream that does not carry them", async () => {
    const fetchMock = countingFetch();
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = mountComposable();
    await flush();
    FakeSocket.opened[0].deliver({ type: "snapshot", status: STATUS, utterances: [] });
    fetchMock.mockClear();
    await vi.advanceTimersByTimeAsync(800);
    await flush();

    const urls = fetchMock.mock.calls.map(([url]) => url.split("?")[0]);
    expect(urls).toEqual(["/events", "/events"]);
    unmount();
  });

  it("closes the stream with the last subscriber", async () => {
    vi.stubGlobal("fetch", countingFetch());
    const { unmount } = mountComposable();
    await flush();
    unmount();
    await vi.advanceTimersByTimeAsync(5000);

    expect([FakeSocket.opened.length, FakeSocket.opened[0].closed]).toEqual([1, true]);
  });
});
