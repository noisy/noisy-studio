import { describe, expect, it } from "vitest";
import {
  canDeliverDuring,
  canFire,
  legalEvents,
  nextState,
  reachable,
  stateToStatus,
  statusAllows,
  statusToState,
  timelineZone,
  validStatusChange,
} from "./chat";

// Every status string the daemon actually emits (grep of listener/*.py).
// If a new wording appears there without a mapping here, the fallback path
// (null state) kicks in and the live audit starts warning — this test is
// the reminder to extend the model instead.
const REAL_USER_STATUSES: Array<[string, string]> = [
  ["recording…", "recording"],
  ["transcribing (Grok STT)…", "transcribing"],
  ["transcribing (live)…", "transcribing"],
  ["ready — awaiting pickup", "ready"],
  ["delivered to Claude", "delivered"],
  ["empty — no speech", "empty"],
  ["dropped — too short", "dropped"],
  ["dropped — mic changed", "dropped"],
  ["dropped — daemon restart", "dropped"],
  ["transcription error", "error"],
  ["cancelled by you", "cancelled"],
];

const REAL_CLAUDE_STATUSES: Array<[string, string]> = [
  ["queued", "queued"],
  ["queued — waiting for you to finish", "holding"],
  ["synthesizing (Grok TTS)…", "synthesizing"],
  ["ready — waiting for the speaker", "ready"],
  ["playing through speakers…", "playing"],
  ["played", "played"],
  ["unheard — voice muted", "unheard"],
  ["unheard — daemon restarted", "unheard"],
  ["unheard — no browser tab", "unheard"],
  ["error", "error"],
];

describe("statusToState", () => {
  it.each(REAL_USER_STATUSES)("user: %s → %s", (status, state) => {
    expect(statusToState("user", status)).toBe(state);
  });

  it.each(REAL_CLAUDE_STATUSES)("claude: %s → %s", (status, state) => {
    expect(statusToState("claude", status)).toBe(state);
  });

  it("returns null for statuses the model has never heard of", () => {
    expect(statusToState("user", "reticulating splines…")).toBeNull();
    expect(statusToState("user", "played")).toBeNull(); // claude-only status on a user card
  });
});

describe("stateToStatus round-trips through statusToState", () => {
  const userStates = REAL_USER_STATUSES.map(([, s]) => s);
  const claudeStates = REAL_CLAUDE_STATUSES.map(([, s]) => s);

  it.each([...new Set(userStates)])("user state %s", (state) => {
    expect(statusToState("user", stateToStatus("user", state))).toBe(state);
  });

  it.each([...new Set(claudeStates)])("claude state %s", (state) => {
    expect(statusToState("claude", stateToStatus("claude", state))).toBe(state);
  });
});

describe("user lifecycle", () => {
  it("walks the happy path recording → transcribing → ready → delivered", () => {
    expect(nextState("user", "recording", "TRANSCRIBE")).toBe("transcribing");
    expect(nextState("user", "transcribing", "TRANSCRIBE")).toBe("transcribing"); // next partial
    expect(nextState("user", "transcribing", "READY")).toBe("ready");
    expect(nextState("user", "ready", "DELIVER")).toBe("delivered");
  });

  it("lets live STT finalize without a partial ever showing", () => {
    expect(nextState("user", "recording", "READY")).toBe("ready");
  });

  it("allows recall only while awaiting pickup", () => {
    expect(canFire("user", "ready", "CANCEL")).toBe(true);
    expect(canFire("user", "recording", "CANCEL")).toBe(false);
    expect(canFire("user", "transcribing", "CANCEL")).toBe(false);
    expect(canFire("user", "delivered", "CANCEL")).toBe(false);
  });

  it("keeps terminal states terminal", () => {
    for (const state of ["delivered", "empty", "dropped", "error", "cancelled"]) {
      expect(legalEvents("user", state)).toEqual([]);
    }
  });

  it("rejects events on states that never accept them", () => {
    expect(nextState("user", "ready", "TRANSCRIBE")).toBeNull();
    expect(nextState("user", "recording", "DELIVER")).toBeNull();
    expect(nextState("user", "recording", "STT_ERROR")).toBeNull(); // errors only surface once transcription started
  });
});

describe("claude lifecycle", () => {
  it("walks the happy path queued → synthesizing → playing → played", () => {
    expect(nextState("claude", "queued", "SYNTHESIZE")).toBe("synthesizing");
    expect(nextState("claude", "synthesizing", "PLAY")).toBe("playing");
    expect(nextState("claude", "playing", "PLAYED")).toBe("played");
  });

  it("holds for the user's turn before synthesis", () => {
    expect(nextState("claude", "queued", "HOLD")).toBe("holding");
    expect(nextState("claude", "holding", "SYNTHESIZE")).toBe("synthesizing");
  });

  it("supports prefetch: synthesis may finish before the speaker frees", () => {
    // Synth runs ahead of playback — the turn gate can land AFTER the
    // render, and prefetched audio plays straight out of the hold.
    expect(nextState("claude", "synthesizing", "READY")).toBe("ready");
    expect(nextState("claude", "ready", "PLAY")).toBe("playing");
    expect(nextState("claude", "ready", "HOLD")).toBe("holding");
    expect(nextState("claude", "synthesizing", "HOLD")).toBe("holding");
    expect(nextState("claude", "holding", "PLAY")).toBe("playing");
  });

  it("keeps prefetched cards below the line until they actually play", () => {
    // Prefetch renders ahead of the queue — a synthesizing/ready card is
    // still WAITING, so it must not leapfrog its neighbours into the
    // active zone (queue order on screen = queue order in the speaker).
    expect(timelineZone("claude", "queued")).toBe("pending");
    expect(timelineZone("claude", "synthesizing (Grok TTS)…")).toBe("pending");
    expect(timelineZone("claude", "ready — waiting for the speaker")).toBe("pending");
    expect(timelineZone("claude", "playing through speakers…")).toBe("active");
    expect(timelineZone("claude", "played")).toBe("done");
  });

  it("skips synthesis entirely on a cache hit", () => {
    expect(nextState("claude", "queued", "READY")).toBe("ready");
    expect(nextState("claude", "played", "READY")).toBe("ready"); // replay from cache
    expect(nextState("claude", "unheard", "READY")).toBe("ready"); // catch-up from cache
  });

  it("re-enters the pipeline on replay and catch-up — mute park and hold included", () => {
    expect(nextState("claude", "played", "SYNTHESIZE")).toBe("synthesizing");
    expect(nextState("claude", "played", "HOLD")).toBe("holding");
    expect(nextState("claude", "played", "UNHEARD")).toBe("unheard");
    expect(nextState("claude", "unheard", "SYNTHESIZE")).toBe("synthesizing");
    expect(nextState("claude", "unheard", "HOLD")).toBe("holding");
  });

  it("parks in-flight speech when muted or after a daemon restart", () => {
    for (const state of ["queued", "holding", "synthesizing", "ready", "playing"]) {
      expect(nextState("claude", state, "UNHEARD")).toBe("unheard");
    }
  });

  it("lets error re-enter the pipeline like a replay — failures are often transient", () => {
    expect(nextState("claude", "error", "SYNTHESIZE")).toBe("synthesizing");
    expect(nextState("claude", "error", "READY")).toBe("ready"); // cached render → instant retry
    expect(nextState("claude", "error", "HOLD")).toBe("holding");
  });

  it("rejects nonsense", () => {
    expect(nextState("claude", "queued", "PLAY")).toBeNull();
    expect(nextState("claude", "played", "PLAYED")).toBeNull();
    expect(nextState("claude", "error", "PLAYED")).toBeNull();
  });
});

describe("statusAllows (UI affordances)", () => {
  it("cancel is offered exactly on ready cards", () => {
    expect(statusAllows("user", "ready — awaiting pickup", "CANCEL")).toBe(true);
    expect(statusAllows("user", "recording…", "CANCEL")).toBe(false);
    expect(statusAllows("user", "delivered to Claude", "CANCEL")).toBe(false);
  });

  it("replay is offered on settled speech — played, parked unheard, or failed", () => {
    expect(statusAllows("claude", "played", "SYNTHESIZE")).toBe(true);
    expect(statusAllows("claude", "unheard — voice muted", "SYNTHESIZE")).toBe(true);
    expect(statusAllows("claude", "error — likely transient, tap ↻ to retry", "SYNTHESIZE")).toBe(true);
    expect(statusAllows("claude", "synthesizing (Grok TTS)…", "SYNTHESIZE")).toBe(false);
  });

  it("allows nothing on unknown statuses", () => {
    expect(statusAllows("user", "reticulating splines…", "CANCEL")).toBe(false);
  });
});

describe("validStatusChange (live transition audit)", () => {
  it("accepts single legal hops", () => {
    expect(validStatusChange("user", "recording…", "transcribing (live)…")).toBe(true);
    expect(validStatusChange("claude", "queued", "unheard — voice muted")).toBe(true);
  });

  it("accepts multi-hop changes — the poller can skip states", () => {
    expect(validStatusChange("claude", "queued", "playing through speakers…")).toBe(true);
    expect(validStatusChange("user", "recording…", "delivered to Claude")).toBe(true);
  });

  it("accepts same-state rewording (longer partials, detail refreshes)", () => {
    expect(
      validStatusChange("user", "transcribing (Grok STT)…", "transcribing (live)…"),
    ).toBe(true);
  });

  it("rejects resurrections from terminal states", () => {
    expect(validStatusChange("user", "delivered to Claude", "recording…")).toBe(false);
    expect(validStatusChange("user", "cancelled by you", "ready — awaiting pickup")).toBe(false);
    expect(validStatusChange("claude", "error", "queued")).toBe(false);
  });

  it("rejects changes involving unknown statuses", () => {
    expect(validStatusChange("user", "recording…", "beamed to the mothership")).toBe(false);
  });
});

describe("canDeliverDuring (cross-machine invariant)", () => {
  it("allows delivery between tools and at turn end — hooks run there", () => {
    expect(canDeliverDuring("THINKING…")).toBe(true); // PostToolUse just drained
    expect(canDeliverDuring(null)).toBe(true); // Stop cleared the line, then drained
  });

  it("forbids delivery while a tool is executing — no hook can drain", () => {
    expect(canDeliverDuring("Edit · App.vue")).toBe(false);
  });
});

describe("reachable", () => {
  it("never escapes terminal states", () => {
    expect(reachable("user", "delivered", "recording")).toBe(false);
    expect(reachable("claude", "error", "queued")).toBe(false);
  });

  it("replay makes playing reachable again from played", () => {
    expect(reachable("claude", "played", "playing")).toBe(true);
  });
});


describe("inbox delivery receipts", () => {
  it("keeps unconfirmed writes distinct from delivery and prevents recall", () => {
    expect(statusToState("user", "sent — unconfirmed")).toBe("sent");
    expect(statusAllows("user", "sent — unconfirmed", "CANCEL")).toBe(false);
    expect(statusAllows("user", "delivery uncertain — not retried", "CANCEL")).toBe(false);
  });
  it("allows recovery before a write and recognizes skipped polling transitions", () => {
    expect(statusAllows("user", "unavailable — registration required", "CANCEL")).toBe(true);
    expect(validStatusChange("user", "ready — awaiting pickup", "sent — unconfirmed")).toBe(true);
    expect(statusAllows("user", "sent — unconfirmed", "DELIVER")).toBe(false);
  });
});
