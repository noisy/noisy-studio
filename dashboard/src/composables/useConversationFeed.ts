/** ONE feed logic for every conversation surface (day 4).
 *
 * The dashboard's ConversationLog and the companion widget used to decide
 * independently which utterances to show, in what order, and in which
 * timeline zone - and disagreed (statuses rendered differently, queued
 * replies missing from one surface). This composable is the dashboard's
 * logic, extracted verbatim; both surfaces consume it now. Styling may
 * differ per surface - the LOGIC may not.
 */
import { computed, type Ref } from "vue";
import { statusToState, timelineZone } from "../machines/chat";
import { conversationCard } from "../conversationCard";
import type { Utterance } from "../types";

// Noise guard: utterances that never became real speech (empty, dropped)
// or were recalled would flood the log in a loud room and bury the actual
// conversation - hide them entirely. STT errors stay visible: that's real
// speech that got lost.
const NOISE_STATES = new Set(["empty", "dropped", "cancelled"]);
function isNoise(u: Utterance): boolean {
  return u.role === "user" && NOISE_STATES.has(statusToState("user", u.status) ?? "");
}

// Order = when a message ENTERED the conversation (committed_at): a Claude
// reply that arrived while the user was still composing sits ABOVE their
// finished message, iMessage style.
function commitTime(u: Utterance): number {
  return u.committed_at || u.started_at;
}

// Dashboard placement: keep in-progress user utterances in the composer.
// The widget receives the same cards and renders them inline.
const LIVE_STATES = new Set(["recording", "transcribing"]);
function isLiveUser(u: Utterance): boolean {
  return u.role === "user" && LIVE_STATES.has(statusToState("user", u.status) ?? "");
}

export function useConversationFeed(utterances: Ref<Utterance[]>) {
  const ordered = computed(() =>
    utterances.value
      .filter((u) => !isNoise(u))
      .sort((a, b) => commitTime(a) - commitTime(b) || a.id - b.id),
  );

  // The composer holds ANY in-progress user utterance - even when a Claude
  // message arrived meanwhile and sorted after it.
  const liveTail = computed(() => {
    const live = ordered.value.filter(isLiveUser);
    return live.length ? live[live.length - 1] : null;
  });

  const settled = computed(() => ordered.value.filter((u) => !isLiveUser(u)));

  // Done is STICKY: a replayed card re-enters the pipeline but is history
  // being re-heard, not future work - it keeps its chronological slot.
  // Keyed by id:started_at because a daemon restart reuses ids from 1.
  const everDone = new Set<string>();
  function zoneOf(u: Utterance): "done" | "active" | "pending" {
    if (u.role === "system") return "done";
    const zone = timelineZone(u.role === "user" ? "user" : "claude", u.status);
    const key = `${u.id}:${u.started_at}`;
    if (zone === "done") everDone.add(key);
    else if (everDone.has(key)) return "done";
    return zone;
  }

  const processed = computed(() => settled.value.filter((u) => zoneOf(u) !== "pending"));
  const pending = computed(() => settled.value.filter((u) => zoneOf(u) === "pending"));

  const cards = computed(() => ordered.value
    .filter((u) => u.role === "user" || u.role === "claude")
    .map((u) => conversationCard(u, zoneOf(u))));

  return { ordered, liveTail, settled, processed, pending, zoneOf, cards };
}
