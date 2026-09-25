import type { DaemonStatus, Utterance } from '../types';
import type { StagePerson, StageLine } from '../components/Stage.vue';
import { AVATAR_VOICES } from '../avatars/catalog';
import { conversationLabel } from '../conversationLabel';
import { orderAgents } from '../components/agentOrder';
import { statusToState } from '../machines/chat';
import type { StagePreferences } from './preferences';

export function stageModel(status: DaemonStatus | null, utterances: Utterance[], labels: StagePreferences['labels']) {
  const people: StagePerson[] = [];
  const lines: StageLine[] = [];
  if (!status) return { people, lines, speaking: '', caption: null };
  const current = utterances.find(u => u.id === status.playing_utterance_id && u.role === 'claude' && (status.speaking_agents ?? []).includes(u.agent ?? ''));
  const title = (id: string) => conversationLabel(status.agent_labels?.[id] ?? status.agents_meta?.[id]?.label, id);
  function persona(id: string, voice: string, speaker?: string) {
    const speakerName = speaker ? conversationLabel(status!.speaker_labels?.[speaker] ?? speaker, id) : 'New conversation';
    if (speakerName !== 'New conversation') return speakerName;
    const named = conversationLabel(status!.voice_labels?.[voice], id, voice);
    if (named !== 'New conversation') return named;
    return AVATAR_VOICES.includes(voice) ? voice.charAt(0).toUpperCase() + voice.slice(1) : title(id);
  }
  for (const id of orderAgents(Object.keys(status.agents), status.agents_meta)) {
    const speakingHere = current?.agent === id ? current : undefined;
    const voice = speakingHere?.voice || status.agent_voices?.[id] || '';
    people.push({ id, voice, name: labels === 'conversation' ? title(id) : persona(id, voice, speakingHere?.speaker), offline: status.agents_meta?.[id]?.online === false, muted: (status.muted_agents ?? []).includes(id) });
  }
  const open = new Set(people.map(p => p.id));
  for (const u of [...utterances].sort((a,b) => (a.updated_at || a.committed_at || a.started_at) - (b.updated_at || b.committed_at || b.started_at) || a.id - b.id)) {
    if (u.role !== 'claude' || !u.agent || !open.has(u.agent) || !u.text.trim()) continue;
    if (u.id !== current?.id && statusToState('claude', u.status) !== 'played') continue;
    lines.push({ id: u.id, person: u.agent, text: u.text, label: labels === 'conversation' ? title(u.agent) : persona(u.agent, u.voice || status.agent_voices?.[u.agent] || '', u.speaker) });
  }
  const currentIndex = lines.findIndex(line => line.id === current?.id);
  if (currentIndex >= 0) lines.push(...lines.splice(currentIndex, 1));
  return { people, lines, speaking: current && open.has(current.agent ?? '') ? current.agent! : '', caption: lines.find(line => line.id === current?.id) ?? null };
}
