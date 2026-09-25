enum AgentState { working, speaking, waiting, offline }

class Agent {
  const Agent(
    this.id,
    this.name, {
    this.state = AgentState.waiting,
    this.harness = 'Agent',
    this.unread = 0,
  });
  final String id, name, harness;
  final AgentState state;
  final int unread;
}

class Message {
  const Message(this.agentId, this.author, this.text);
  final String agentId, author, text;
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
    return Snapshot(
      agents: ids.map((id) {
        final m = meta[id] as Map<String, dynamic>? ?? {};
        final conversation = conversations[id] as Map<String, dynamic>? ?? {};
        final label = labels[id] as String? ?? m['label'] as String? ?? '';
        return Agent(
          id,
          label.trim().isEmpty || label == id ? 'New conversation' : label,
          state: m['online'] == false
              ? AgentState.offline
              : speaking.contains(id)
              ? AgentState.speaking
              : conversation['status'] == 'live'
              ? AgentState.working
              : AgentState.waiting,
          harness: (conversation['harness'] as String? ?? 'Agent').replaceAll(
            '-hooks',
            '',
          ),
          unread: (queued[id] as num?)?.toInt() ?? 0,
        );
      }).toList(),
      messages: (data['utterances'] as List? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(
            (m) => Message(
              m['agent'] as String? ?? '',
              m['role'] == 'user'
                  ? 'You'
                  : (m['agent_label'] as String? ?? 'Agent'),
              (m['text'] as String? ?? '').isEmpty
                  ? (m['status'] as String? ?? 'Transcribing…')
                  : m['text'] as String,
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
    ),
  ),
  messages: const [
    Message('agent-1', 'You', 'How is the release looking?'),
    Message(
      'agent-1',
      'Lux',
      'The latest checks passed. I’m reviewing the final changes.',
    ),
    Message('agent-2', 'Flux', 'The interface is ready for a look.'),
  ],
);
