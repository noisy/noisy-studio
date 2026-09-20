/** Map utterance lifecycle states onto HUD status chips. */

import { statusToState, type ClaudeState, type Role, type UserState } from "../machines/chat";

export type StatusKind = "done" | "work" | "rec" | "spoken" | "fail" | "off";

export interface StatusChip {
  kind: StatusKind;
  label: string;
}

const USER_CHIPS: Record<UserState, StatusChip> = {
  recording: { kind: "rec", label: "● RECORDING" },
  transcribing: { kind: "work", label: "◌ TRANSCRIBING" },
  // Transcribed, sitting in the queue until Claude is free to pick it up.
  // Name WHO we're waiting for: "transmitting" reads like a transfer in
  // trouble when Claude is just busy, and "ready" begs ready-for-what.
  ready: { kind: "work", label: "◌ AWAITING AGENT" },
  delivered: { kind: "done", label: "✓ DELIVERED" },
  sent: { kind: "off", label: "◌ SENT · UNCONFIRMED" },
  uncertain: { kind: "fail", label: "! UNCERTAIN · NOT RETRIED" },
  unavailable: { kind: "fail", label: "! REGISTRATION REQUIRED" },
  rejected: { kind: "fail", label: "✕ REJECTED" },
  accepted: { kind: "off", label: "◌ ACCEPTED · UNCONFIRMED" },
  confirmed: { kind: "done", label: "✓ CONFIRMED" },
  empty: { kind: "fail", label: "✕ NO SPEECH" },
  dropped: { kind: "fail", label: "✕ DROPPED" },
  error: { kind: "fail", label: "✕ ERROR" },
  cancelled: { kind: "off", label: "✕ CANCELLED" },
  // Loud by design: the user spoke into a tab whose session is offline.
  undelivered: { kind: "fail", label: "✕ NO LISTENER" },
};

const CLAUDE_CHIPS: Record<ClaudeState, StatusChip> = {
  queued: { kind: "work", label: "◌ QUEUED" },
  holding: { kind: "work", label: "◌ HOLDING" },
  synthesizing: { kind: "work", label: "◌ SYNTHESIZING" },
  // Audio in hand — the clip only waits for the speaker to free up.
  ready: { kind: "work", label: "✓ READY" },
  playing: { kind: "spoken", label: "▶ PLAYING" },
  played: { kind: "done", label: "✓ PLAYED" },
  unheard: { kind: "off", label: "◌ UNHEARD" },
  skipped: { kind: "off", label: "⏭ SKIPPED" },
  error: { kind: "fail", label: "✕ ERROR" },
};

export function statusChip(status: string, role: Role): StatusChip {
  const state = statusToState(role, status);
  // A status outside the machine's vocabulary still renders (raw, as a
  // work chip) — the live transition audit is what flags it as a bug.
  if (state === null) return { kind: "work", label: status.toUpperCase() };
  return role === "user"
    ? USER_CHIPS[state as UserState]
    : CLAUDE_CHIPS[state as ClaudeState];
}

export function formatCost(costUsd: number): string {
  return costUsd > 0 ? `$${costUsd.toFixed(4)}` : "—";
}

/** Recover speakable text from a Claude card („text” — or the legacy
 * "[voice] „text”" format from before voice tags were dropped). */
export function replaySpeechText(cardText: string): string {
  const match = cardText.match(/^(?:\[[^\]]+\]\s*)?[„"]?([\s\S]*?)[”"]?$/);
  return (match ? match[1] : cardText).trim();
}

export function formatTime(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}
