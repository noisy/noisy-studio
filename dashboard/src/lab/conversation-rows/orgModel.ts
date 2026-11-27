/** The org tree's data model and the pure rules behind what a row shows.
 *
 * The product model (product owner, 2026-11-27): a CEO talks by voice to a
 * few long-lived "manager" conversations. The primary axis is the PROJECT,
 * what it is achieving right now; under it sit its manager conversation(s),
 * and under each manager the agents it delegated work to. The scarce
 * resources are the CEO's attention, the plan's usage windows (money) and
 * concurrency on the machine, so each project shows all three.
 *
 * Which of these fields the daemon sends today, and which it must add, is
 * listed in README.md in this folder.
 */
import { projectHue, waitLabel } from "../../components/tabDetails";

/** Task-progress states, plus "review" (done, waiting for your review) and
 *  "paused" (stopped by you, resumable). */
export type AgentState = "pending" | "working" | "blocked" | "review" | "paused" | "done";

/** A delegated agent: a subagent, a child thread or a Codex task, as it
 *  reports itself through task progress. */
export interface DelegatedAgent {
  id: string;
  title: string;
  state: AgentState;
  who: string; // participant / role / model, as reported
  completed?: number;
  total?: number;
  note?: string; // why it is blocked
  worktree?: string | null; // the checkout it works in, if not the manager's
  tokens?: number; // today
}

export interface ManagerConversation {
  id: string;
  title: string;
  harness: string | null;
  branch: string | null;
  shortcut: number | null; // the Tab N hotkey
  startedAt: number; // epoch s
  status: "idle" | "working" | "ended";
  activity?: string; // live activity line while working
  speaking?: boolean;
  queued?: number; // messages waiting to be heard
  muted?: boolean;
  waitingSince?: number | null; // epoch s; your move since then
  endedAt?: number | null;
  settled?: boolean; // you settled it
  snoozedUntil?: number | null; // epoch s
  tokens?: number; // today
  agents: DelegatedAgent[];
}

/** The project's share of a plan window. Shares are 0..1 of the window. */
export interface ProjectUsage {
  window: string; // "Claude · 5 h"
  share: number; // what this project used of the window
  windowUsed: number; // what everything used of the window
  resetsAt: number | null;
  weeklyShare: number;
  cap: number | null; // the CEO's cap on this project's share
  tokens: number; // today
  costUsd: number; // API-equivalent, today
}

export interface Project {
  id: string; // repository root; "" for conversations without project data
  name: string | null; // null: a legacy conversation, no project data
  path: string | null;
  goal: string | null; // what it is achieving right now
  focused?: boolean;
  worktrees?: number;
  usage: ProjectUsage | null;
  managers: ManagerConversation[];
}

export type Signal = "muted" | "speaking" | "queued" | "working" | null;

/** The ONE signal a manager row shows, the production ladder:
 *  mute > speaking > queued > working > nothing. Idle draws no glyph. */
export function signalOf(manager: ManagerConversation): Signal {
  if (manager.muted) return "muted";
  if (manager.speaking) return "speaking";
  if ((manager.queued ?? 0) > 0) return "queued";
  if (manager.status === "working") return "working";
  return null;
}

/** Settled and ended conversations leave the project for the Settled section. */
export const isLive = (manager: ManagerConversation) => !manager.settled && manager.status !== "ended";

export const isSnoozed = (manager: ManagerConversation, now: number) =>
  manager.snoozedUntil != null && manager.snoozedUntil > now;

/** What waits for the CEO, the scarcest resource. Only things that demand an
 *  action count: unheard messages, blocked agents (a decision or an
 *  approval), finished work to review, and a broken cap. A manager that is
 *  merely idle is not a demand: you heard it, it waits for your next order.
 *  A snoozed manager's own demands wait until it wakes. */
export interface Demand {
  kind: "listen" | "blocked" | "review" | "overCap";
  text: string;
  conversation?: string;
  agent?: string;
}

export function demandsOf(project: Project, now: number): Demand[] {
  const demands: Demand[] = [];
  for (const manager of project.managers.filter(isLive)) {
    const queued = manager.queued ?? 0;
    if (queued > 0 && !isSnoozed(manager, now)) {
      demands.push({ kind: "listen", conversation: manager.id, text: `${queued} ${queued === 1 ? "message" : "messages"} to hear · ${manager.title}` });
    }
    for (const agent of manager.agents) {
      if (agent.state === "blocked") demands.push({ kind: "blocked", conversation: manager.id, agent: agent.id, text: `${agent.title} · ${agent.note ?? "blocked"}` });
      if (agent.state === "review") demands.push({ kind: "review", conversation: manager.id, agent: agent.id, text: `Review · ${agent.title}` });
    }
  }
  if (isOverCap(project.usage)) demands.push({ kind: "overCap", text: `Over its cap · ${percent(project.usage!.share)} of ${percent(project.usage!.cap!)}` });
  return demands;
}

/** Concurrency: what is running on the machine for this project right now. */
export function runningOf(project: Project): { agents: number; paused: number; managers: number } {
  const live = project.managers.filter(isLive);
  const agents = live.flatMap((manager) => manager.agents);
  return {
    agents: agents.filter((agent) => agent.state === "working").length,
    paused: agents.filter((agent) => agent.state === "paused").length,
    managers: live.filter((manager) => manager.status === "working").length,
  };
}

export const isOverCap = (usage: ProjectUsage | null) => usage != null && usage.cap != null && usage.share > usage.cap;

export const percent = (share: number) => `${Math.round(share * 100)}%`;

/** Live projects in a stable order (focused first, then as given: the list
 *  never re-sorts on state, so a project stays where the eye left it), the
 *  conversations without project data gathered into one "No project"
 *  group, and the settled conversations. */
export function arrange(projects: Project[]) {
  const live = projects.filter((project) => project.managers.some(isLive));
  const unassigned = live.filter((project) => !project.name).flatMap((project) => project.managers.filter(isLive));
  return {
    projects: [...live.filter((p) => p.name && p.focused), ...live.filter((p) => p.name && !p.focused)]
      .map((project) => ({ ...project, managers: project.managers.filter(isLive) })),
    unassigned: unassigned.length ? { ...NO_PROJECT, managers: unassigned } : null,
    settled: projects.flatMap((project) =>
      project.managers.filter((manager) => !isLive(manager)).map((manager) => ({ project, manager })),
    ),
  };
}

const NO_PROJECT: Project = { id: "", name: null, path: null, goal: null, usage: null, managers: [] };

/** Everything a row can ask the list to do. The list keeps the overlay
 *  ones (menu, card) and re-emits the rest as its own events. */
export type OrgAction =
  | { type: "select" | "settle" | "restore" | "toggleSnooze"; conversation: string }
  | { type: "snooze"; conversation: string; until: number }
  | { type: "pause" | "resume" | "stop" | "review"; agent: string }
  | { type: "focus"; project: string; focused: boolean }
  | { type: "pauseProject" | "cap" | "peek" | "unpeek" | "holdPeek"; project: string };

/** Open work first, finished work last; finished work folds. */
export function orderAgents(agents: DelegatedAgent[]): { open: DelegatedAgent[]; done: DelegatedAgent[] } {
  return { open: agents.filter((agent) => agent.state !== "done"), done: agents.filter((agent) => agent.state === "done") };
}

/** What a delegated agent's right-hand slot says. */
export function agentStatus(agent: DelegatedAgent): string {
  if (agent.state === "working" || agent.state === "pending") {
    if (agent.completed != null && agent.total != null) return `${agent.completed}/${agent.total}`;
    return agent.state === "pending" ? "queued" : "";
  }
  return { blocked: "blocked", review: "review", paused: "paused", done: "done" }[agent.state];
}

/** The corner of a manager row: wake time when snoozed, how long it has
 *  waited for you otherwise. */
export function cornerOf(manager: ManagerConversation, now: number): string {
  if (isSnoozed(manager, now)) return clockLabel(manager.snoozedUntil!, now);
  return waitLabel(manager.waitingSince ?? null, now);
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const pad = (value: number) => String(value).padStart(2, "0");

/** "18:00" today, "Sat 09:00" on another day (local time). */
export function clockLabel(at: number, now: number): string {
  const date = new Date(at * 1000);
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return date.toDateString() === new Date(now * 1000).toDateString() ? time : `${DAY_NAMES[date.getDay()]} ${time}`;
}

/** "1.2M", "340k" tokens. */
export function tokensLabel(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}k`;
  return String(tokens);
}

export const hueOf = (project: Project) => (project.name ? projectHue(project.name) : null);
export const initialOf = (project: Project) => (project.name ?? "?").charAt(0).toUpperCase();
