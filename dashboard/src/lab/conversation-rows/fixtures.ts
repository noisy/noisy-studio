/** Synthetic conversations for the ConversationRows lab boards.
 *
 * The user's model (product owner, 2026-11-27): a few long-lived "manager"
 * conversations, about four, one per area, spoken to like a CEO talks to
 * managers. Each manager delegates to subagents / child threads. So the
 * fixtures are four managers with delegated work, plus specimens for the
 * states the four do not cover.
 *
 * Data sources: agents_meta + conversations snapshot (label, project,
 * branch, harness, status, waiting_since, created_at, last_event_at,
 * last_activity, shortcut), queued/speaking/muted lists, active_agent (mic),
 * and task progress reports per thread (title, state, completed/total,
 * participant/role/model, review state) for the delegated work. Not sent
 * yet: the conversation's cwd (`path`) and snooze.
 */
import { projectHue, waitLabel } from "../../components/tabDetails";

export type LabSection = "yourTurn" | "working" | "settled";
/** Task-progress states, with "review" = done and waiting for your review. */
export type ChildState = "working" | "blocked" | "review" | "done" | "pending";

export interface LabChild {
  id: string;
  title: string;
  state: ChildState;
  who: string; // participant / role / model, as reported
  progress?: string; // "3/5" from completed/total
  note?: string; // blocked reason
}

export interface LabRow {
  id: string;
  caption: string; // board gutter label, never part of the row
  title: string;
  project: string | null;
  path: string | null;
  branch: string | null;
  harness: string | null;
  section: LabSection;
  shortcut: number | null;
  shortId: string;
  started: string;
  lastActivity: string;
  children: LabChild[];
  waitingSince?: number | null;
  activity?: string;
  queued?: number;
  speaking?: boolean;
  working?: boolean;
  muted?: boolean;
  mic?: boolean;
  viewed?: boolean;
  ended?: string; // "2h": how long ago the session ended
  snoozedUntil?: string; // "18:00"
  hover?: boolean; // forced hover for the static board
}

export const NOW = 1_800_000_000;
const ago = (minutes: number) => NOW - minutes * 60;

const STUDIO = { project: "noisy-studio", path: "~/Developer/noisy-studio" };

/** The desk: four managers in hotkey order, then two settled ones. */
export const DESK: LabRow[] = [
  {
    id: "product", caption: "mic · viewed · your turn", title: "Noisy Studio product", ...STUDIO,
    branch: "main", harness: "Claude Code", section: "yourTurn", shortcut: 1, shortId: "c41e",
    started: "Mon 09:12", lastActivity: "11:38", waitingSince: ago(2), mic: true, viewed: true,
    children: [
      { id: "p1", title: "Conversation rows lab", state: "working", who: "subagent · Opus", progress: "3/5" },
      { id: "p2", title: "Fix push-to-talk release", state: "working", who: "Codex thread", progress: "1/3" },
      { id: "p3", title: "Settle button spec", state: "review", who: "subagent · Sonnet" },
    ],
  },
  {
    id: "bucky", caption: "3 queued", title: "Bucky", project: "bucky", path: "~/Developer/bucky",
    branch: "feat/voice-tiles", harness: "Codex", section: "yourTurn", shortcut: 2, shortId: "77fa",
    started: "Tue 08:47", lastActivity: "11:34", waitingSince: ago(6), queued: 3,
    children: [
      { id: "b1", title: "TestFlight upload", state: "blocked", who: "subagent · Sonnet", note: "needs Apple login" },
    ],
  },
  {
    id: "web", caption: "speaking", title: "Website & marketing", project: "website", path: "~/Developer/website",
    branch: "main", harness: "Claude Code", section: "yourTurn", shortcut: 3, shortId: "9b02",
    started: "Wed 10:05", lastActivity: "11:40", speaking: true, children: [],
  },
  {
    id: "release", caption: "working", title: "Release 3.1", ...STUDIO,
    branch: "release/3.1.0", harness: "Claude Code", section: "working", shortcut: 4, shortId: "31c0",
    started: "10:20", lastActivity: "11:40", working: true, activity: "Reading CI logs",
    children: [
      { id: "r1", title: "Sign and notarize", state: "working", who: "subagent · Sonnet", progress: "2/4" },
      { id: "r2", title: "Release smoke tests", state: "working", who: "subagent · Haiku", progress: "5/9" },
      { id: "r3", title: "Bump versions", state: "done", who: "subagent · Haiku" },
    ],
  },
  {
    id: "snoozed", caption: "snoozed", title: "Company deck", project: "Downloads", path: "~/Downloads",
    branch: null, harness: "Claude Code", section: "settled", shortcut: null, shortId: "f0a2",
    started: "yesterday", lastActivity: "10:02", snoozedUntil: "18:00", children: [],
  },
  {
    id: "ended", caption: "settled · ended", title: "Issue 172 review", ...STUDIO,
    branch: "issue-172", harness: "Claude Code", section: "settled", shortcut: null, shortId: "4d77",
    started: "08:00", lastActivity: "09:41", ended: "2h",
    children: [{ id: "e1", title: "Reproduce on Linux", state: "done", who: "subagent · Sonnet" }],
  },
];

/** States the desk does not show, one row each. */
export const SPECIMENS: LabRow[] = [
  {
    id: "muted", caption: "muted", title: "Grok harness", ...STUDIO, branch: "grok-harness",
    harness: "Grok", section: "yourTurn", shortcut: 5, shortId: "5c6b", started: "11:02",
    lastActivity: "11:37", waitingSince: ago(3), muted: true,
    children: [{ id: "g1", title: "Protocol smoke check", state: "working", who: "subagent · Sonnet", progress: "1/2" }],
  },
  {
    id: "legacy", caption: "no project (legacy)", title: "fitatu", project: null, path: null, branch: null,
    harness: null, section: "yourTurn", shortcut: null, shortId: "legacy", started: "—",
    lastActivity: "11:18", waitingSince: ago(22), children: [],
  },
  {
    id: "long", caption: "long names",
    title: "Investigate why push-to-talk release swallows the last word on Bluetooth headsets",
    project: "noisy-studio-website-assets", path: "~/Developer/noisy-studio-website-assets",
    branch: "fix/ptt-release-bluetooth-last-word", harness: "Claude Code", section: "yourTurn",
    shortcut: 6, shortId: "aa19", started: "06:55", lastActivity: "09:12", waitingSince: ago(150),
    children: [{ id: "l1", title: "Capture Bluetooth HFP timing traces on three headsets", state: "working", who: "subagent · Opus", progress: "2/3" }],
  },
  {
    id: "hover", caption: "hovered · actions + card", title: "QA and docs", ...STUDIO, branch: "docs/qa",
    harness: "Claude Code", section: "yourTurn", shortcut: 7, shortId: "e310", started: "09:58",
    lastActivity: "11:26", waitingSince: ago(14), hover: true,
    children: [
      { id: "q1", title: "Rewrite local-dev guide", state: "working", who: "subagent · Sonnet", progress: "4/6" },
      { id: "q2", title: "Screenshot refresh", state: "done", who: "subagent · Haiku" },
    ],
  },
];

/** A copy of the hovered row, used to show the snooze menu open. */
export const MENU_ROW: LabRow = { ...SPECIMENS[3], id: "menu", caption: "snooze menu open" };

export const SECTION_TITLES: Record<Exclude<LabSection, "yourTurn">, string> = {
  working: "Working",
  settled: "Settled",
};

/** How long it has waited for you, T3-compact ("4m"); empty when it is not your move. */
export const waited = (row: LabRow) => waitLabel(row.waitingSince ?? null, NOW);

export const hueOf = (row: LabRow) => (row.project ? projectHue(row.project) : null);

export const initialOf = (row: LabRow) => (row.project ?? row.title).charAt(0).toUpperCase();

/** The text a row shows top-right: wait time, wake time or time since it ended. */
export function cornerTime(row: LabRow): string {
  if (row.snoozedUntil) return row.snoozedUntil;
  if (row.ended) return row.ended;
  return row.section === "yourTurn" ? waited(row) : "";
}

/** The ONE signal a row shows, same ladder as the production tabs:
 *  mute > speaking > queued > working > nothing. Idle has no glyph. */
export type Signal = "muted" | "speaking" | "queued" | "working" | null;
export function signalOf(row: LabRow): Signal {
  if (row.muted) return "muted";
  if (row.speaking) return "speaking";
  if ((row.queued ?? 0) > 0) return "queued";
  if (row.working) return "working";
  return null;
}

/** Delegated work in a few words: "2 running · 1 to review". */
export function childSummary(children: LabChild[]): { text: string; needsYou: boolean } {
  const count = (state: ChildState) => children.filter((child) => child.state === state).length;
  const parts = [
    count("working") && `${count("working")} running`,
    count("blocked") && `${count("blocked")} blocked`,
    count("review") && `${count("review")} to review`,
    count("done") && `${count("done")} done`,
  ].filter(Boolean) as string[];
  return { text: parts.join(" · "), needsYou: count("blocked") + count("review") > 0 };
}

export type Tone = "green" | "amber" | "violet" | "red" | "muted" | "ink";

/** What the manager needs from you, one sentence in the colour of its meaning. */
export function statusLine(row: LabRow): { text: string; tone: Tone } {
  if (row.muted) return { text: "Muted · speech held back", tone: "red" };
  if (row.speaking) return { text: "Speaking now", tone: "green" };
  if ((row.queued ?? 0) > 0) return { text: `${row.queued} messages to hear`, tone: "amber" };
  if (row.working) return { text: `Working · ${row.activity}`, tone: "violet" };
  if (row.snoozedUntil) return { text: `Snoozed until ${row.snoozedUntil}`, tone: "muted" };
  if (row.ended) return { text: `Ended ${row.ended} ago`, tone: "muted" };
  return { text: `Your turn · ${waited(row)}`, tone: "ink" };
}

export const CHILD_TONE: Record<ChildState, Tone> = {
  working: "violet", blocked: "amber", review: "amber", done: "muted", pending: "muted",
};
