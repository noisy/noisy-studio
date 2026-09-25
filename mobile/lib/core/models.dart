enum AgentState { working, speaking, waiting, offline }

class Agent {
  const Agent(
    this.id,
    this.name, {
    this.state = AgentState.waiting,
    this.harness = 'Agent',
    this.unread = 0,
    this.voice = '',
  });
  final String id, name, harness, voice;
  final AgentState state;
  final int unread;
}

class Message {
  const Message(
    this.agentId,
    this.author,
    this.text, {
    this.id = 0,
    this.role = 'claude',
    this.status = '',
    this.voice = '',
    this.time = '',
  });
  final int id;
  final String agentId, author, text, role, status, voice, time;
}

class Snapshot {
  const Snapshot({
    this.agents = const [],
    this.messages = const [],
    this.activeId,
    this.muted = false,
    this.auto = false,
    this.recording = false,
  });
  final List<Agent> agents;
  final List<Message> messages;
  final String? activeId;
  final bool muted, auto, recording;

  factory Snapshot.fromJson(Map<String, dynamic> data) {
    final s = data['status'] as Map<String, dynamic>;
    final ids = (s['agents'] as Map<String, dynamic>? ?? {}).keys;
    final meta = s['agents_meta'] as Map<String, dynamic>? ?? {};
    final labels = s['agent_labels'] as Map<String, dynamic>? ?? {};
    final speaking = s['speaking_agents'] as List? ?? [];
    final queued = s['queued_by_agent'] as Map<String, dynamic>? ?? {};
    final conversations = s['conversations'] as Map<String, dynamic>? ?? {};
    final activity = s['activity'] as Map<String, dynamic>? ?? {};
    final now = DateTime.now().millisecondsSinceEpoch / 1000;
    return Snapshot(
      agents: ids.map((id) {
        final m = meta[id] as Map<String, dynamic>? ?? {};
        final conversation = conversations[id] as Map<String, dynamic>? ?? {};
        final a = activity[id] as Map<String, dynamic>? ?? {};
        const workingFreshSeconds =
            20; // Same activity window as the desktop tabs.
        final working =
            (a['text'] as String? ?? '').isNotEmpty &&
            now - ((a['at'] as num?)?.toDouble() ?? 0) < workingFreshSeconds;
        final label = labels[id] as String? ?? m['label'] as String? ?? '';
        return Agent(
          id,
          label.trim().isEmpty || label == id ? 'New conversation' : label,
          state: m['online'] == false
              ? AgentState.offline
              : speaking.contains(id)
              ? AgentState.speaking
              : working
              ? AgentState.working
              : AgentState.waiting,
          harness: (conversation['harness'] as String? ?? 'Agent').replaceAll(
            '-hooks',
            '',
          ),
          unread: (queued[id] as num?)?.toInt() ?? 0,
          voice:
              (s['agent_voices'] as Map<String, dynamic>? ?? {})[id]
                  as String? ??
              '',
        );
      }).toList(),
      messages: (data['utterances'] as List? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(
            (m) => Message(
              m['agent'] as String? ?? '',
              messageAuthor(
                m,
                s['speaker_labels'] as Map<String, dynamic>? ?? {},
              ),
              (m['text'] as String? ?? '').isEmpty
                  ? (m['status'] as String? ?? 'Transcribing…')
                  : m['text'] as String,
              id: (m['id'] as num?)?.toInt() ?? 0,
              role: m['role'] as String? ?? 'claude',
              status: m['status'] as String? ?? '',
              voice: m['voice'] as String? ?? '',
              time: messageTime(m['started_at'] as num?),
            ),
          )
          .toList(),
      activeId: s['active_agent'] as String?,
      muted: s['muted'] == true,
      auto: s['detection_mode'] == 'auto',
      recording: s['recording'] == true,
    );
  }
}

Snapshot fixture({int count = 4, AgentState? state}) => Snapshot(
  activeId: 'agent-1',
  agents: List.generate(
    count,
    (i) => Agent(
      'agent-${i + 1}',
      ['Lux', 'Flux', 'Atlas', 'Nova', 'Echo', 'Pixel', 'Sage'][i % 7],
      state: state ?? AgentState.values[i % 4],
      harness: i.isEven ? 'Claude' : 'Codex',
      unread: i == 2 ? 3 : 0,
      voice: ['lux', 'luna', 'atlas', 'eve', 'rex', 'ara', 'orion'][i % 7],
    ),
  ),
  messages: const [
    Message(
      'agent-1',
      'You',
      'How is the release looking?',
      role: 'user',
      status: 'delivered',
      time: '14:32',
    ),
    Message(
      'agent-1',
      'Lux',
      'The latest checks passed. I’m reviewing the final changes.',
      status: 'played',
      voice: 'lux',
      time: '14:33',
    ),
    Message(
      'agent-2',
      'Flux',
      'The interface is ready for a look.',
      status: 'unheard',
      voice: 'luna',
      time: '14:34',
    ),
  ],
);

String messageAuthor(
  Map<String, dynamic> message,
  Map<String, dynamic> speakerLabels,
) {
  final role = message['role'];
  if (role == 'user') return 'You';
  if (role == 'daemon') return 'Noisy Studio';
  if (role == 'system') return 'System';
  final agent = (message['agent_label'] as String? ?? '').trim();
  final label = agent.isEmpty ? 'Agent' : agent;
  final speaker = (message['speaker'] as String? ?? '').trim();
  if (speaker.isEmpty) return label;
  return speakerLabels[speaker] as String? ?? '$speaker · $label';
}

String messageTime(num? seconds) {
  if (seconds == null || seconds <= 0) return '';
  final time = DateTime.fromMillisecondsSinceEpoch((seconds * 1000).round());
  return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
}
