import type { Utterance } from '../types';

const base: Utterance = {
  id: 1, role: 'user', status: 'recording…', text: '', detail: '',
  cost_usd: 0, agent: 'session-1', started_at: 1, updated_at: 1, committed_at: 0,
};
export const voiceMessageStates = {
  Recording: base,
  Transcribing: { ...base, status: 'transcribing…' },
  LivePartial: { ...base, status: 'transcribing…', text: 'Please check the latest changes' },
  AwaitingAgent: { ...base, status: 'ready — awaiting pickup', text: 'Please check the latest changes.', committed_at: 2 },
  Delivered: { ...base, status: 'delivered to Claude', text: 'Please check the latest changes.', committed_at: 2 },
};
