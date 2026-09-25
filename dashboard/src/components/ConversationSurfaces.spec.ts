import { mount } from '@vue/test-utils';
import { ref } from 'vue';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useConversationFeed } from '../composables/useConversationFeed';
import { limitSettledHistory } from '../conversationCard';
import { voiceMessageStates } from '../storybook/voiceMessageStates';
import Bubble from './Bubble.vue';
import Companion from './Companion.vue';
import ConversationLog from './ConversationLog.vue';

beforeEach(() => {
  vi.stubGlobal('requestAnimationFrame', () => 1);
  vi.stubGlobal('cancelAnimationFrame', vi.fn());
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
});
afterEach(() => vi.unstubAllGlobals());

it('keeps one voice message visible across recording, transcription, pickup and delivery on both surfaces', async () => {
  const utterances = ref([voiceMessageStates.Recording]);
  const feed = useConversationFeed(utterances);
  const dashboard = mount(ConversationLog, { props: { utterances: utterances.value } });
  const widget = mount(Companion, { props: { feed: feed.cards.value, mode: 'idle' } });
  const expected = [
    ['active', '● RECORDING', 'Listening…', true],
    ['active', '◌ TRANSCRIBING', 'Transcribing your message…', true],
    ['active', '◌ TRANSCRIBING', 'Please check the latest changes', true],
    ['pending', '◌ AWAITING AGENT', 'Please check the latest changes.', false],
    ['done', '✓ DELIVERED', 'Please check the latest changes.', false],
  ];
  for (const [index, utterance] of Object.values(voiceMessageStates).entries()) {
    utterances.value = [utterance];
    await dashboard.setProps({ utterances: utterances.value });
    await widget.setProps({ feed: feed.cards.value });
    const card = feed.cards.value[0];
    expect([feed.zoneOf(utterance), card.statusLabel, card.text, card.inFlight]).toEqual(expected[index]);
    expect(widget.findAll('.msg')).toHaveLength(1);
    expect(widget.get('.txt').text()).toBe(dashboard.get('.txt').text());
    expect(widget.getComponent(Bubble).props("statusLabel")).toBe(card.statusLabel);
    expect(dashboard.text()).toContain(card.statusLabel);
    expect(widget.find('.in-flight').exists()).toBe(card.inFlight);
    expect(dashboard.find('.liveslot .msg').exists()).toBe(card.inFlight);
  }
  dashboard.unmount(); widget.unmount();
});

it('retains an old voice turn and pending reply when newer played replies fill widget history', async () => {
  const replies = Array.from({ length: 13 }, (_, index) => ({
    ...voiceMessageStates.Delivered, id: index + 3, role: 'claude' as const,
    status: 'played', text: `Reply ${index + 3}`, committed_at: index + 3,
  }));
  const pendingReply = {
    ...voiceMessageStates.Delivered, id: 2, role: 'claude' as const,
    status: 'queued', text: 'Waiting reply', committed_at: 2,
  };
  const utterances = ref([voiceMessageStates.Recording, pendingReply, ...replies]);
  const feed = useConversationFeed(utterances);
  const widget = mount(Companion, { props: { mode: 'idle' } });
  for (const voiceTurn of [voiceMessageStates.Recording, voiceMessageStates.Transcribing, voiceMessageStates.AwaitingAgent]) {
    utterances.value = [voiceTurn, pendingReply, ...replies];
    const visible = limitSettledHistory(feed.cards.value, 12);
    await widget.setProps({ feed: visible });
    expect(visible.map(card => card.id)).toEqual([1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
    expect(widget.findAllComponents(Bubble).map(bubble => bubble.props('statusLabel'))).toContain(feed.cards.value[0].statusLabel);
    expect(widget.text()).toContain('Waiting reply');
  }
  widget.unmount();
});
