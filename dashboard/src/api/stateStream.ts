/** The daemon's pushed state stream (#73).
 *
 * A WebSocket on the bridge port (HTTP port + 1), path /state; in `vite dev`
 * the same path on the page's own origin, which Vite proxies to the daemon.
 * Protocol v2: a full snapshot on connect, then numbered patches (status ops,
 * utterance upserts/removals, new event-log entries). A gap in the numbering,
 * or a patch that cannot apply, drops the socket and the reconnect brings a
 * fresh snapshot - the client never guesses. A v1 daemon sends full snapshots
 * only and no events; that still works, the caller polls /events beside it.
 * Polling /status remains the fallback while the socket is down.
 */
import type { DaemonEvent } from "./client";
import type { DaemonStatus, Utterance } from "../types";

export const STATE_PATH = "/state";
export const STATE_PROTOCOL_VERSION = 2;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 5000;
const RECONNECT_MAX_DOUBLINGS = 4;

export interface StateUpdate {
  status: DaemonStatus;
  utterances: Utterance[];
  /** New event-log entries; null when this daemon's stream carries none
   * (protocol v1), so the caller must keep pulling /events itself. */
  events: DaemonEvent[] | null;
  /** A full snapshot (a fresh connection), not a patch. */
  fresh: boolean;
}

type StatusPath = string[];
/** `[path, value]` sets, `[path]` deletes. */
export type StatusOp = [StatusPath, unknown] | [StatusPath];

export type UtterancePatch =
  | { replace: Utterance[] }
  | { remove: number[]; upsert: Utterance[] };

type Json = Record<string, unknown>;

function isRecord(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function writeAt(target: unknown, path: StatusPath, op: StatusOp): unknown {
  if (path.length === 0) return op[1];
  const [head, ...rest] = path;
  const copy: Json = isRecord(target) ? { ...target } : {};
  if (rest.length === 0 && op.length === 1) delete copy[head];
  else copy[head] = writeAt(copy[head], rest, op);
  return copy;
}

/** Apply the daemon's status ops without mutating `status`: changed branches
 * are new objects, untouched ones are shared. */
export function applyStatusOps<T>(status: T, ops: StatusOp[]): T {
  return ops.reduce<unknown>((current, op) => writeAt(current, op[0], op), status) as T;
}

/** Removals, then in-place replacements, then new items at the end - the only
 * reshapes the daemon sends as a patch; anything else arrives as `replace`. */
export function applyUtterancePatch(list: Utterance[], patch: UtterancePatch): Utterance[] {
  if ("replace" in patch) return patch.replace;
  const removed = new Set(patch.remove);
  const pending = new Map(patch.upsert.map((u) => [u.id, u]));
  const kept = list
    .filter((u) => !removed.has(u.id))
    .map((u) => {
      const next = pending.get(u.id);
      if (!next) return u;
      pending.delete(u.id);
      return next;
    });
  return [...kept, ...pending.values()];
}

export type DecodeResult = StateUpdate | "resync" | "unsupported" | null;

/** Turns the stream's messages into whole states. One per connection. */
export class StateStreamDecoder {
  private seq = -1;
  private status: DaemonStatus | null = null;
  private utterances: Utterance[] = [];

  decode(raw: unknown): DecodeResult {
    let message: unknown;
    try {
      message = typeof raw === "string" ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
    if (!isRecord(message)) return null;
    const version = message.v ?? 1;
    if (typeof version !== "number" || version > STATE_PROTOCOL_VERSION) return "unsupported";
    if (message.type === "snapshot") return this.snapshot(message, version);
    if (message.type === "patch") return this.patch(message);
    return null; // {"type": "error"} and anything newer: nothing to render
  }

  private snapshot(message: Json, version: number): DecodeResult {
    if (!isRecord(message.status) || !Array.isArray(message.utterances)) return null;
    this.status = message.status as unknown as DaemonStatus;
    this.utterances = message.utterances as Utterance[];
    if (version < STATE_PROTOCOL_VERSION) {
      return { status: this.status, utterances: this.utterances, events: null, fresh: true };
    }
    this.seq = Number(message.seq);
    const events = Array.isArray(message.events) ? (message.events as DaemonEvent[]) : [];
    return { status: this.status, utterances: this.utterances, events, fresh: true };
  }

  private patch(message: Json): DecodeResult {
    if (!this.status || this.seq < 0 || message.seq !== this.seq + 1) return "resync";
    try {
      if (Array.isArray(message.status)) this.status = applyStatusOps(this.status, message.status as StatusOp[]);
      if (isRecord(message.utterances)) {
        this.utterances = applyUtterancePatch(this.utterances, message.utterances as unknown as UtterancePatch);
      }
    } catch {
      return "resync";
    }
    this.seq += 1;
    const events = Array.isArray(message.events) ? (message.events as DaemonEvent[]) : [];
    return { status: this.status, utterances: this.utterances, events, fresh: false };
  }
}

type PageLocation = Pick<Location, "protocol" | "host" | "hostname" | "port">;

export function stateStreamUrl(location: PageLocation = window.location, viaDevProxy = import.meta.env.DEV): string {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const query = `?v=${STATE_PROTOCOL_VERSION}`;
  // `vite dev` proxies /state to the daemon it proxies HTTP to (vite.config).
  if (viaDevProxy) return `${scheme}://${location.host}${STATE_PATH}${query}`;
  const served = Number(location.port || (location.protocol === "https:" ? 443 : 80));
  return `${scheme}://${location.hostname}:${served + 1}${STATE_PATH}${query}`;
}

export function reconnectDelayMs(attempt: number): number {
  return Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** Math.min(attempt, RECONNECT_MAX_DOUBLINGS));
}

export interface StreamHandle {
  close(): void;
}

/** Open the stream and keep it open. `onUpdate` fires with the whole current
 * state per message; `onLive(true)` after the first valid snapshot and
 * `onLive(false)` when a live stream drops, so the caller can gate its
 * polling. Reconnects with backoff; the backoff resets only once state has
 * actually arrived, so a daemon that accepts and hangs up is not hammered. */
export function openStateStream(
  onUpdate: (update: StateUpdate) => void,
  onLive: (live: boolean) => void,
  url: () => string = () => stateStreamUrl(),
): StreamHandle | null {
  if (typeof WebSocket === "undefined") return null; // non-browser
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let attempts = 0;
  let closed = false;

  const schedule = () => {
    if (closed) return;
    timer = setTimeout(connect, reconnectDelayMs(attempts++));
  };

  function connect() {
    if (closed) return;
    const decoder = new StateStreamDecoder();
    let live = false;
    let current: WebSocket;
    try {
      current = new WebSocket(url());
    } catch {
      schedule();
      return;
    }
    socket = current;
    current.onmessage = (event) => {
      const result = decoder.decode(event.data);
      if (result === "resync" || result === "unsupported") {
        if (result === "unsupported") attempts = RECONNECT_MAX_DOUBLINGS; // slow retry, poll meanwhile
        current.close();
        return;
      }
      if (!result) return;
      if (!live) {
        live = true;
        attempts = 0;
        onLive(true);
      }
      onUpdate(result);
    };
    current.onerror = () => {
      /* onclose follows */
    };
    current.onclose = () => {
      if (socket === current) socket = null;
      const wasLive = live;
      live = false;
      if (closed) return; // the caller hung up; it wants no more callbacks
      if (wasLive) onLive(false);
      schedule();
    };
  }

  connect();
  return {
    close() {
      closed = true;
      if (timer) clearTimeout(timer);
      socket?.close();
      socket = null;
    },
  };
}
