/** What the live dictation bubble shows: the words of the current session
 * and where they are on their way into the focused app. */
import type { DaemonStatus, Utterance } from "../types";

export type DictationPhase = "listening" | "inserting" | "inserted" | "failed";

export interface DictationView {
  text: string;
  phase: DictationPhase;
}

const FAILED = ["dictation — not inserted", "dictation — insertion failed"];

export function dictationView(status: DaemonStatus | null, utterances: Utterance[]): DictationView {
  const session = status?.dictation?.session ?? 0;
  const mine = session ? utterances.filter((u) => u.dictation === session).sort((a, b) => a.id - b.id) : [];
  const text = mine.map((u) => u.text.trim()).filter(Boolean).join(" ");
  if (status?.dictation?.active) return { text, phase: "listening" };
  if (mine.some((u) => FAILED.some((prefix) => u.status.startsWith(prefix)))) return { text, phase: "failed" };
  if (status?.dictation?.pending) return { text, phase: "inserting" };
  return { text, phase: "inserted" };
}
