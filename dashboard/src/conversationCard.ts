/** Shared lifecycle presentation; surfaces choose placement, not meaning. */
import type { Utterance } from "./types";
import { statusToState, timelineZone, type TimelineZone } from "./machines/chat";
import { statusChip } from "./components/bubbleStatus";

export function conversationCard(u: Utterance, zone?: TimelineZone) {
  const role: "user" | "claude" = u.role === "user" ? "user" : "claude";
  const state = statusToState(role, u.status);
  const inFlight = role === "user" && (state === "recording" || state === "transcribing");
  const chip = statusChip(u.status, role);
  const placeholder = state === "recording" ? "Listening…"
    : state === "transcribing" ? "Transcribing your message…" : u.status;
  return {
    id: u.id, role, zone: zone ?? timelineZone(role, u.status), inFlight,
    text: u.text.trim() ? u.text : placeholder,
    statusKind: chip.kind, statusLabel: chip.label,
  };
}

/** Limit history without hiding work that still needs attention. */
export function limitSettledHistory(cards: ReturnType<typeof conversationCard>[], limit: number) {
  const settled = cards.filter(card => card.zone === "done" && !card.inFlight);
  const recent = new Set(settled.slice(Math.max(0, settled.length - limit)));
  return cards.filter(card => card.inFlight || card.zone !== "done" || recent.has(card));
}
