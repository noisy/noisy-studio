/** The realistic conversation list the AgentTabs stories (and the Lab
 *  design boards comparing it) render: four projects, one conversation
 *  without a project, five ended sessions. Shared so every board shows the
 *  same data. */
const PROJECT_AGENTS: Record<string, string> = {
  dash: 'noisy-studio · dashboard', bucky: 'Bucky', qa: 'QA docs', diet: 'fitatu',
  bugs: 'Bug fixing', release: 'release 3.0.0', mobile: 'mobile TestFlight',
  cta: 'website CTA', grok: 'grok harness', deck: 'presentation', i152: 'issue 152 live', i172: 'issue 172 review',
};
const ENDED = ['cta', 'grok', 'deck', 'i152', 'i172'];
// Tab N hotkeys come from the daemon's stable order, not the grouping.
const SHORTCUTS: Record<string, number> = { dash: 1, bugs: 2, qa: 3, bucky: 4 };
// Project and branch come from the session's directory (no setup); legacy
// and Codex sessions may have neither, so 'diet' lands in "No project".
export const NOW = 1_800_000_000;
const WORKSPACE: Record<string, { project: string; branch: string | null }> = {
  dash: { project: 'noisy-studio', branch: 'main' }, bucky: { project: 'bucky', branch: 'feat/voice-tiles' },
  qa: { project: 'noisy-studio', branch: 'docs/qa' }, bugs: { project: 'noisy-studio', branch: 'fix/hold-release' },
  release: { project: 'noisy-studio', branch: 'release/3.0.0' }, mobile: { project: 'noisy-mobile', branch: 'main' },
  cta: { project: 'website', branch: 'main' }, grok: { project: 'noisy-studio', branch: 'grok-harness' },
  deck: { project: 'Downloads', branch: null }, i152: { project: 'noisy-studio', branch: 'issue-152' }, i172: { project: 'noisy-studio', branch: 'issue-172' },
};
const WAITING_SINCE: Record<string, number> = { dash: NOW - 30, bucky: NOW - 4 * 60, qa: NOW - 2 * 3600 };

/** Conversations the user settled (hidden), as the daemon's settled_agents
 *  sends them: the newest few, and the total for "+N older". */
export const SETTLED_AGENTS = {
  total: 34,
  items: [
    { name: 'spike', label: 'audio spike', project: 'noisy-studio', branch: 'spike/aec', last_active_at: 99, ended: true, talk_key: null },
    { name: 'pricing', label: 'pricing page copy', project: 'website', branch: 'copy/pricing', last_active_at: 97, ended: false, talk_key: 'F18' },
    { name: 'notes', label: 'meeting notes', project: null, branch: null, last_active_at: 90, ended: true, talk_key: null },
  ],
};

export const projectArgs = (settledOpen: boolean) => ({
  agents: PROJECT_AGENTS,
  meta: Object.fromEntries(Object.entries(PROJECT_AGENTS).map(([id, label], i) => [id, {
    label, online: !ENDED.includes(id), activated_at: i, offline_since: ENDED.includes(id) ? 100 - i : null,
    shortcut: SHORTCUTS[id] ?? null,
    project: WORKSPACE[id]?.project ?? null, branch: WORKSPACE[id]?.branch ?? null,
    waiting_since: WAITING_SINCE[id] ?? null,
  }])),
  active: 'dash', viewed: 'dash', speaking: ['qa'], queued: { bucky: 2, release: 1 },
  thinking: ['bugs', 'release', 'mobile'],
  activity: { bugs: 'Bash · pytest', release: 'Thinking…', mobile: 'Edit · App.swift' },
  settledOpen,
  now: NOW,
  // The rows show the real hotkey; unbound ones fall back to "Tab N".
  tabKeys: { 1: 'F16', 2: 'F17', 3: 'ctrl+alt+3' },
});
