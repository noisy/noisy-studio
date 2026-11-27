/** Synthetic projects for the OrgTree stories and spec. The clock is frozen
 *  on Friday 27 Nov 2026, 11:42 local time, so wait and wake times read the
 *  same on every machine. */
import type { Project } from "./orgModel";

export const NOW = Math.floor(new Date(2026, 10, 27, 11, 42).getTime() / 1000);
const ago = (minutes: number) => NOW - minutes * 60;
const at = (hour: number, minute = 0, dayOffset = 0) =>
  Math.floor(new Date(2026, 10, 27 + dayOffset, hour, minute).getTime() / 1000);
const CLAUDE_5H = { window: "Claude · 5 h", windowUsed: 0.62, resetsAt: at(14, 0) };

/** One manager, three delegated agents: one running, one blocked, one
 *  waiting for review (and finished work folded under them). The mic is on
 *  this manager. */
export const STUDIO: Project = {
  id: "~/Developer/noisy-studio", name: "noisy-studio", path: "~/Developer/noisy-studio",
  goal: "Ship 3.1 with the project list", worktrees: 2,
  usage: { ...CLAUDE_5H, share: 0.24, weeklyShare: 0.11, cap: 0.4, tokens: 1_840_000, costUsd: 6.1 },
  managers: [{
    id: "studio", title: "Studio manager", harness: "Claude Code", branch: "main", shortcut: 1,
    startedAt: at(9, 12, -4), status: "idle", waitingSince: ago(2), tokens: 610_000,
    agents: [
      { id: "s1", title: "Org tree lab", state: "working", who: "subagent · Opus", completed: 3, total: 5, worktree: "t3-ee49e38e", tokens: 720_000 },
      { id: "s2", title: "TestFlight upload", state: "blocked", who: "subagent · Sonnet", note: "needs your Apple login", tokens: 90_000 },
      { id: "s3", title: "Settle button spec", state: "review", who: "Codex thread", tokens: 380_000 },
      { id: "s4", title: "Bump versions", state: "done", who: "subagent · Haiku", tokens: 40_000 },
    ],
  }],
};

/** Two managers on one project: one speaking to you, one working. */
export const BUCKY: Project = {
  id: "~/Developer/bucky", name: "bucky", path: "~/Developer/bucky",
  goal: "Voice tiles in the iOS beta", worktrees: 1,
  usage: { window: "Codex · 5 h", windowUsed: 0.35, resetsAt: at(15, 30), share: 0.18, weeklyShare: 0.07, cap: null, tokens: 1_210_000, costUsd: 3.4 },
  managers: [
    {
      id: "bucky-app", title: "Bucky app", harness: "Codex", branch: "feat/voice-tiles", shortcut: 2,
      startedAt: at(8, 47, -3), status: "idle", speaking: true, queued: 1, waitingSince: ago(1), tokens: 420_000, agents: [],
    },
    {
      id: "bucky-api", title: "Bucky backend", harness: "Claude Code", branch: "auth-tables", shortcut: 3,
      startedAt: at(10, 5), status: "working", activity: "Reading CI logs", tokens: 330_000,
      agents: [
        { id: "b1", title: "Migrate auth tables", state: "working", who: "Codex thread", completed: 2, total: 4, worktree: "bucky-auth", tokens: 460_000 },
      ],
    },
  ],
};

/** Nothing running, nothing waiting, no usage today: the quiet case. */
export const WEBSITE: Project = {
  id: "~/Developer/website", name: "website", path: "~/Developer/website",
  goal: "Pricing page refresh", worktrees: 0,
  usage: { ...CLAUDE_5H, share: 0, weeklyShare: 0.02, cap: null, tokens: 0, costUsd: 0 },
  managers: [{
    id: "web", title: "Website & marketing", harness: "Claude Code", branch: "main", shortcut: 4,
    startedAt: at(10, 5, -2), status: "idle", waitingSince: ago(26 * 60), tokens: 0, agents: [],
  }],
};

/** Over its cap: four benchmark agents eat the plan window. The broken cap
 *  is one of the things waiting for you, next to two unheard messages. */
export const BENCH: Project = {
  id: "~/Developer/stt-bench", name: "stt-bench", path: "~/Developer/stt-bench",
  goal: "Pick the default speech model", worktrees: 4,
  usage: { ...CLAUDE_5H, share: 0.46, weeklyShare: 0.19, cap: 0.3, tokens: 3_900_000, costUsd: 14.2 },
  managers: [{
    id: "bench", title: "Speech benchmark", harness: "Claude Code", branch: "bench/nov", shortcut: 5,
    startedAt: at(7, 30), status: "working", activity: "Scoring run 3 of 4", queued: 2, tokens: 520_000,
    agents: [
      { id: "x1", title: "Whisper large v3", state: "working", who: "subagent · Sonnet", completed: 38, total: 50, worktree: "bench-a", tokens: 980_000 },
      { id: "x2", title: "Parakeet", state: "working", who: "subagent · Sonnet", completed: 21, total: 50, worktree: "bench-b", tokens: 910_000 },
      { id: "x3", title: "Canary", state: "working", who: "subagent · Sonnet", completed: 12, total: 50, worktree: "bench-c", tokens: 870_000 },
      { id: "x4", title: "Moonshine", state: "pending", who: "subagent · Haiku", worktree: "bench-d", tokens: 0 },
    ],
  }],
};

/** Long names everywhere, a paused agent, and a snoozed second manager. */
export const LONG: Project = {
  id: "~/Developer/noisy-studio-website-assets", name: "noisy-studio-website-assets",
  path: "~/Developer/noisy-studio-website-assets",
  goal: "Re-record every marketing screenshot for the 3.1 launch in both themes", worktrees: 1,
  usage: { ...CLAUDE_5H, share: 0.07, weeklyShare: 0.04, cap: 0.1, tokens: 520_000, costUsd: 1.9 },
  managers: [
    {
      id: "assets", title: "Investigate why push-to-talk release swallows the last word on Bluetooth headsets",
      harness: "Claude Code", branch: "fix/ptt-release-bluetooth-last-word", shortcut: 6,
      startedAt: at(6, 55), status: "idle", waitingSince: ago(150), tokens: 210_000,
      agents: [
        { id: "l1", title: "Capture Bluetooth HFP timing traces on three different headsets", state: "working", who: "subagent · Opus", completed: 2, total: 3, tokens: 260_000 },
        { id: "l2", title: "Regenerate synthetic screenshots for the companion widget", state: "paused", who: "subagent · Sonnet", completed: 4, total: 11, tokens: 50_000 },
      ],
    },
    {
      id: "export", title: "Asset export pipeline", harness: "Claude Code", branch: "main", shortcut: null,
      startedAt: at(9, 0), status: "idle", queued: 1, waitingSince: ago(40), snoozedUntil: at(18, 0), tokens: 0, agents: [],
    },
  ],
};

/** A conversation from an old daemon or harness: no folder, no project, no
 *  usage. Muted, so its speech is held back. */
export const LEGACY: Project = {
  id: "", name: null, path: null, goal: null, usage: null,
  managers: [{
    id: "fitatu", title: "fitatu", harness: null, branch: null, shortcut: null,
    startedAt: ago(200), status: "idle", muted: true, queued: 2, waitingSince: ago(22), agents: [],
  }],
};

/** Settled work: an ended project, and a conversation you settled. */
export const DECK: Project = {
  id: "~/Downloads", name: "Downloads", path: "~/Downloads", goal: null, usage: null,
  managers: [{
    id: "deck", title: "Company deck", harness: "Claude Code", branch: null, shortcut: null,
    startedAt: at(16, 0, -1), status: "ended", endedAt: ago(120), agents: [],
  }],
};
export const ISSUE: Project = {
  ...STUDIO, id: "~/Developer/noisy-studio#172",
  managers: [{
    id: "i172", title: "Issue 172 review", harness: "Claude Code", branch: "issue-172", shortcut: null,
    startedAt: at(8, 0), status: "idle", settled: true, endedAt: ago(45),
    agents: [{ id: "i1", title: "Reproduce on Linux", state: "done", who: "subagent · Sonnet" }],
  }],
};

/** The whole desk, in the order the daemon would send it. */
export const DESK: Project[] = [STUDIO, BUCKY, BENCH, WEBSITE, LONG, LEGACY, DECK, ISSUE];

/** One project whose managers show every row state side by side. */
export const MANAGER_STATES: Project = {
  ...STUDIO, goal: "Every manager row state", usage: { ...STUDIO.usage!, cap: null },
  managers: [
    { ...STUDIO.managers[0], id: "m-mic", title: "Mic · your turn", agents: [] },
    { ...STUDIO.managers[0], id: "m-speak", title: "Speaking", speaking: true, waitingSince: null, shortcut: 2, agents: [] },
    { ...STUDIO.managers[0], id: "m-queued", title: "3 to hear", queued: 3, waitingSince: ago(6), shortcut: 3, agents: [] },
    { ...STUDIO.managers[0], id: "m-work", title: "Working", status: "working", activity: "Bash · pytest", waitingSince: null, shortcut: 4, agents: [] },
    { ...STUDIO.managers[0], id: "m-muted", title: "Muted, 2 held back", muted: true, queued: 2, waitingSince: ago(9), shortcut: null, agents: [] },
    { ...STUDIO.managers[0], id: "m-snoozed", title: "Snoozed", snoozedUntil: at(9, 0, 1), waitingSince: ago(60), shortcut: null, agents: [] },
  ],
};

/** One manager with a delegated agent in every state. */
export const AGENT_STATES: Project = {
  ...STUDIO, goal: "Every delegated agent state", usage: { ...STUDIO.usage!, cap: null },
  managers: [{
    ...STUDIO.managers[0],
    agents: [
      { id: "a-work", title: "Running with progress", state: "working", who: "subagent · Opus", completed: 3, total: 5 },
      { id: "a-plain", title: "Running, no progress", state: "working", who: "subagent · Sonnet" },
      { id: "a-pend", title: "Queued, not started", state: "pending", who: "subagent · Haiku" },
      { id: "a-block", title: "Blocked on you", state: "blocked", who: "subagent · Sonnet", note: "approve the migration" },
      { id: "a-review", title: "Done, to review", state: "review", who: "Codex thread" },
      { id: "a-pause", title: "Paused by you", state: "paused", who: "subagent · Sonnet", completed: 1, total: 4 },
      { id: "a-done", title: "Finished", state: "done", who: "subagent · Haiku" },
    ],
  }],
};
