import { expect, it } from 'vitest';
import { stageModel } from './model';
import type { DaemonStatus, Utterance } from '../types';
const status = {
  agents: { a1: 1, a2: 2 }, agent_labels: { a1: 'Release work', a2: 'Ideas' },
  agent_voices: { a1: 'lux', a2: 'luna' }, voice_labels: { lux: 'Lux', luna: 'Luna' },
  agents_meta: { a1: { online: true }, a2: { online: false } },
  speaking_agents: ['a1'], playing_utterance_id: 1, muted_agents: ['a2'],
} as unknown as DaemonStatus;
const row = (id: number, state: string, patch: Partial<Utterance> = {}): Utterance => ({
  id, status: state, role: 'claude', agent: 'a1', text: `Reply ${id}`, detail: '', cost_usd: 0,
  started_at: id, committed_at: id, updated_at: id, ...patch,
});
it('uses the playing card for subagent identity and excludes future or closed conversation speech', () => {
  const model = stageModel(status, [row(1, 'playing through speakers…', { voice: 'iris', speaker: 'Reviewer' }), row(2, 'queued'), row(3, 'unheard'), row(4, 'played', { agent: 'closed' }), row(5, 'played', { agent: 'a2' })], 'persona');

  expect(model.people).toEqual([
    { id: 'a1', name: 'Reviewer', voice: 'iris', offline: false, muted: false },
    { id: 'a2', name: 'Luna', voice: 'luna', offline: true, muted: true },
  ]);
  expect(model.lines.map(line => line.id)).toEqual([5, 1]);
  expect(model.caption).toEqual({ id: 1, person: 'a1', text: 'Reply 1', label: 'Reviewer' });
  expect(stageModel(status, [], 'conversation').people.map(p => p.name)).toEqual(['Release work', 'Ideas']);
});
it('clears captions when playback stops and keeps an older replay visible at the transcript end', () => {
  const rows = Array.from({length:8}, (_, i) => row(i + 1, 'played'));
  const replay = stageModel(status, rows, 'persona');
  const stopped = stageModel({ ...status, playing_utterance_id: 0, speaking_agents: [] }, rows, 'persona');

  expect(replay.lines.slice(-5).map(line => line.id)).toEqual([5,6,7,8,1]);
  expect({ speaker: stopped.speaking, caption: stopped.caption }).toEqual({ speaker: '', caption: null });
});
it('never exposes paths or routing IDs as titles or persona names', () => {
  const unsafe = { ...status, agent_labels: { a1: '/private/transcript.json', a2: 'a2' }, agent_voices: { a1: 'unknown', a2: 'unknown' }, voice_labels: { unknown: '/private/voice' } };
  expect(stageModel(unsafe, [], 'persona').people.map(p => p.name)).toEqual(['New conversation', 'New conversation']);
  expect(stageModel(unsafe, [], 'conversation').people.map(p => p.name)).toEqual(['New conversation', 'New conversation']);
});
