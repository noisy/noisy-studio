/** Poll the daemon's REST API into reactive state (legacy cadence: 400 ms). */

import { onMounted, onUnmounted, ref, type Ref } from "vue";
import {
  getEvents, getStatus, getUtterances, setActiveAgent, dismissAgent as apiDismissAgent, reorderAgents as apiReorderAgents, type DaemonEvent,
} from "../api/client";
import { openStateStream, type StateSnapshot, type StreamHandle } from "../api/stateStream";
import { validStatusChange } from "../machines/chat";
import type { Character, DaemonStatus, Utterance } from "../types";
import { canonicalCharacter } from "../character";

import { conversationCharacter } from "./conversationCharacter";

import { conversationTimeline } from "./conversationTimeline";

const ERROR_LOG_SIZE = 20;

export interface DaemonState {
  status: Ref<DaemonStatus | null>;
  utterances: Ref<Utterance[]>; // the viewed agent's slice
  /** Which agent `utterances` was filtered for - set ATOMICALLY with the
   * list, unlike viewedAgent which can change mid-poll (#33 race). */
  utterancesFor: Ref<string | null>;
  allUtterances: Ref<Utterance[]>; // every agent — feeds unread badges
  character: Ref<Character | null>;
  characterPending: Readonly<Ref<boolean>>;
  characterError: Ref<string>;
  changeCharacter: (patch: Partial<Character>) => void;
  offline: Ref<boolean>;
  viewedAgent: Ref<string | null>;
  errors: Ref<DaemonEvent[]>; // newest last, errors only
  selectAgent: (name: string) => void;
  dismissAgent: (name: string) => void;
  reorderAgents: (order: string[]) => void;
}

const CHARACTER_CACHE_KEY = "noisy.lastCharacter";

function readCachedCharacter(): Character | null {
  try {
    const raw = localStorage.getItem(CHARACTER_CACHE_KEY);
    return raw ? canonicalCharacter(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function cacheCharacter(c: Character | null) {
  try {
    if (c) localStorage.setItem(CHARACTER_CACHE_KEY, JSON.stringify(c));
  } catch {
    /* storage unavailable - the seed is a convenience, not state */
  }
}

type SharedDaemonState = DaemonState & { subscribe(): void; unsubscribe(): void };

function createDaemonState(pollMs: number): SharedDaemonState {
  const status = ref<DaemonStatus | null>(null);
  const utterances = ref<Utterance[]>([]);
  const utterancesFor = ref<string | null>(null);
  const allUtterances = ref<Utterance[]>([]);
  // Seed the avatar from the last session so the widget never opens on the
  // default (red) portrait while the first /character round-trip is in
  // flight - the swap read as a broken flash on every app start.
  const offline = ref(false);
  const viewedAgent = ref<string | null>(null);
  const errors = ref<DaemonEvent[]>([]);
  const characters = conversationCharacter(viewedAgent, readCachedCharacter(), cacheCharacter, (detail) => {
    errors.value = [...errors.value, {
      seq: 0, ts: Date.now() / 1000, kind: "character_save_error", detail,
    }].slice(-ERROR_LOG_SIZE);
  });
  const { character, pending: characterPending, error: characterError, change: changeCharacter } = characters;
  let lastEventSeq = 0;

  /* THE DAEMON'S active_agent IS THE SELECTION. There is no local pin.
   *
   * The dashboard and the companion are two Electron windows, so two renderer
   * processes, so two copies of this module - a module-level singleton can
   * only unify views inside ONE window (the browser float). A local "pinned"
   * flag that outlived the daemon's answer was therefore a second source of
   * truth per window, and the two windows drifted (#65). Now every window
   * follows the daemon; a click is an optimistic preview that holds only
   * until the daemon has answered, and status polled before that answer is
   * not allowed to overwrite it. */
  let selecting = 0; // in-flight selectAgent calls
  let settledAt = 0; // when the last selection was answered

  // Assumption detector: every observed status change must be a path in
  // the chat machine (see machines/chat.ts). A change the model can't
  // explain means the daemon and the model disagree — surface it in the
  // error ticker instead of silently rendering nonsense. Keyed by
  // id:started_at because a daemon restart reuses ids from 1.
  const lastStatuses = new Map<string, string>();
  let violationSeq = 0;
  function auditTransitions(all: Utterance[]) {
    for (const u of all) {
      if (u.role !== "user" && u.role !== "claude") continue;
      const key = `${u.id}:${u.started_at}`;
      const prev = lastStatuses.get(key);
      lastStatuses.set(key, u.status);
      if (prev === undefined || prev === u.status) continue;
      if (validStatusChange(u.role, prev, u.status)) continue;
      const detail = `#${u.id} ${u.role}: "${prev}" → "${u.status}"`;
      console.warn(`[chat-machine] unexpected transition ${detail}`);
      errors.value = [
        ...errors.value,
        { seq: --violationSeq, ts: Date.now() / 1000, kind: "machine_violation", detail },
      ].slice(-ERROR_LOG_SIZE);
    }
  }

  /* RENDER WHAT THE DAEMON SAYS. `apply` is the one place daemon state
   * enters this module - fed by the pushed WebSocket snapshot (#73) or, while
   * the socket is down, by the polling fallback. It replaces, never merges:
   * a tab the daemon no longer lists is gone from the strip on the next
   * frame, which is what made stale/duplicate tabs impossible. */
  function apply(s: DaemonStatus, all: Utterance[], askedAt: number) {
    status.value = s;
    offline.value = false;
    // A poll/snapshot that left before the daemon confirmed a click may
    // still carry the previous agent; only one issued afterwards may speak.
    if (!selecting && askedAt >= settledAt) viewedAgent.value = s.active_agent;
    if (viewedAgent.value && !(viewedAgent.value in s.agents)) {
      viewedAgent.value = s.active_agent;
    }
    const agent = viewedAgent.value ?? undefined;
    auditTransitions(all);
    allUtterances.value = all;
    utterances.value = conversationTimeline(all, agent, agent ? s.conversations?.[agent]?.created_at : undefined);
    utterancesFor.value = agent ?? null;
    characters.apply(s, askedAt);
  }

  /* Failures (STT/TTS errors) live in the daemon's event log, not in the
   * snapshot; fetch them on the side at a relaxed cadence. */
  async function pullEvents() {
    try {
      const fresh = await getEvents(lastEventSeq);
      if (fresh.length) {
        lastEventSeq = fresh[fresh.length - 1].seq;
        const failures = fresh.filter((e) => e.kind.endsWith("_error"));
        if (failures.length) {
          errors.value = [...errors.value, ...failures].slice(-ERROR_LOG_SIZE);
        }
      }
    } catch {
      /* the next pull will try again */
    }
  }

  /* Polling fallback: used until the state stream is open, and again
   * whenever it drops. One unfiltered fetch serves both the viewed log and
   * the unread badges on background tabs. */
  async function tick() {
    if (streamOpen) {
      await pullEvents();
      return;
    }
    try {
      const askedAt = Date.now();
      const s = await getStatus();
      const all = await getUtterances();
      apply(s, all, askedAt);
      await pullEvents();
    } catch {
      offline.value = true;
    }
  }

  let streamOpen = false;
  let stream: StreamHandle | null = null;
  function onSnapshot(snapshot: StateSnapshot) {
    apply(snapshot.status, snapshot.utterances, Date.now());
  }
  function onStreamState(open: boolean) {
    streamOpen = open;
    if (!open) tick(); // fall back at once, do not wait for the next interval
  }

  function selectAgent(name: string) {
    selecting += 1;
    viewedAgent.value = name; // preview; the daemon's answer replaces it
    // The daemon has the last word on who holds the mic, and it can refuse
    // (an agent that dropped out of its table). Believing the click instead
    // of the answer is what let the dashboard tab and the companion widget
    // drift apart - and worse, the mic then fed the OTHER agent.
    setActiveAgent(name)
      .then((active) => {
        if (active) viewedAgent.value = active;
      })
      .catch(() => {})
      .finally(() => {
        selecting -= 1;
        settledAt = Date.now();
      });
  }

  function reorderAgents(order: string[]) {
    apiReorderAgents(order)
      .catch(() => {})
      .finally(() => tick());
  }

  function dismissAgent(name: string) {
    if (viewedAgent.value === name) viewedAgent.value = null;
    apiDismissAgent(name)
      .catch((error: unknown) => {
        // A refused close must be VISIBLE. Swallowing it made the ✕ look
        // broken whenever the daemon said no (or was mid-restart).
        errors.value = [
          ...errors.value,
          { seq: 0, ts: Date.now() / 1000, kind: "tab_close_failed",
            detail: `Could not close '${status.value?.agent_labels?.[name] ?? name}': ${(error as Error)?.message ?? error}` },
        ].slice(-ERROR_LOG_SIZE);
      })
      .finally(() => tick());
  }

  let timer: ReturnType<typeof setInterval> | undefined;
  let subscribers = 0;
  function subscribe() {
    if (subscribers++ === 0) {
      tick();
      timer = setInterval(tick, pollMs);
      stream = openStateStream(onSnapshot, onStreamState);
    }
  }
  function unsubscribe() {
    if (--subscribers === 0) {
      clearInterval(timer);
      timer = undefined;
      stream?.close();
      stream = null;
      streamOpen = false;
    }
  }

  return { status, utterances, utterancesFor, allUtterances, character, characterPending, characterError, changeCharacter, offline, viewedAgent, errors, selectAgent, dismissAgent, reorderAgents, subscribe, unsubscribe };
}

/* ONE state per window, not one per component.
 *
 * This used to be a plain factory, so App.vue, CompanionView and
 * CompanionFloat each built their own refs and their own poller. Sharing the
 * instance drops the redundant 400ms polling loops and keeps the views inside
 * a window in step. It does NOT make the dashboard and the desktop companion
 * agree - those are separate Electron windows and separate processes, each
 * with its own copy of `shared`. Agreement between windows comes from the
 * daemon's active_agent alone (see createDaemonState). */
let shared: SharedDaemonState | null = null;

export function useDaemonState(pollMs = 400): DaemonState {
  if (!shared) shared = createDaemonState(pollMs);
  const instance = shared;
  onMounted(() => instance.subscribe());
  onUnmounted(() => instance.unsubscribe());
  return instance;
}

/** Tests only: drop the shared instance so each case starts clean. */
export function resetDaemonState(): void {
  shared = null;
}
