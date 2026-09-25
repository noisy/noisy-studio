import 'package:flutter/material.dart';

import '../core/models.dart';
import 'design.dart';
import 'voice_avatar.dart';
import 'message_status.dart';
export 'design.dart' show studioTheme;

String agentStateLabel(Agent agent) => switch (agent.state) {
  AgentState.working => 'Working',
  AgentState.speaking => 'Speaking',
  AgentState.offline => 'Offline',
  AgentState.waiting => 'Ready',
};

class AudioNotice extends StatelessWidget {
  const AudioNotice({super.key});
  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      const Icon(Icons.computer_outlined, size: 15),
      const SizedBox(width: 6),
      Flexible(
        child: Text(
          'Desktop microphone · desktop speakers',
          style: TextStyle(
            fontSize: 11,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    ],
  );
}

class AgentStateChip extends StatelessWidget {
  const AgentStateChip({super.key, required this.agent});
  final Agent agent;
  @override
  Widget build(BuildContext context) {
    final color = agent.state == AgentState.speaking
        ? StudioColors.accent(context)
        : agent.state == AgentState.working
        ? StudioColors.agentAccent(context)
        : Theme.of(context).colorScheme.onSurfaceVariant;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          agent.state == AgentState.speaking ? Icons.graphic_eq : Icons.circle,
          size: agent.state == AgentState.speaking ? 16 : 5,
          color: color,
        ),
        const SizedBox(width: 5),
        Text(
          agentStateLabel(agent),
          style: TextStyle(color: color, fontSize: 11),
        ),
      ],
    );
  }
}

class AgentsView extends StatelessWidget {
  const AgentsView({super.key, required this.snapshot, required this.onSelect});
  final Snapshot snapshot;
  final ValueChanged<Agent> onSelect;
  @override
  Widget build(BuildContext context) => CustomScrollView(
    slivers: [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 18),
        sliver: SliverToBoxAdapter(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Eyebrow('Conversations'),
              const SizedBox(height: 6),
              Text(
                'Your crew',
                style: Theme.of(context).textTheme.headlineMedium
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 5),
              Text(
                '${snapshot.agents.length} open · Tap an agent to talk',
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
      if (snapshot.agents.isEmpty)
        const SliverFillRemaining(
          child: Center(child: Text('Open an agent on your desktop to begin.')),
        )
      else
        SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          sliver: SliverGrid.builder(
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 240,
              mainAxisExtent: 220,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: snapshot.agents.length,
            itemBuilder: (context, i) {
              final a = snapshot.agents[i];
              final selected = a.id == snapshot.activeId;
              final color = StudioColors.accent(context);
              final scheme = Theme.of(context).colorScheme;
              return Material(
                color: selected
                    ? Color.alphaBlend(
                        color.withValues(alpha: .06),
                        scheme.surface,
                      )
                    : scheme.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(
                    color: selected ? color : scheme.outline,
                    width: selected ? 1.5 : 1,
                  ),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => onSelect(a),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Eyebrow(
                              a.harness,
                              color: a.harness.toLowerCase().contains('claude')
                                  ? const Color(0xffc19477)
                                  : color,
                            ),
                            const Spacer(),
                            if (selected)
                              Icon(Icons.mic, size: 14, color: color),
                          ],
                        ),
                        const SizedBox(height: 12),
                        VoiceAvatar(voice: a.voice, size: 88),
                        const SizedBox(height: 12),
                        Text(
                          a.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 5),
                        AgentStateChip(agent: a),
                        if (a.unread > 0)
                          Padding(
                            padding: const EdgeInsets.only(top: 5),
                            child: Text(
                              '${a.unread} awaiting agent',
                              style: TextStyle(fontSize: 10, color: color),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      const SliverPadding(padding: EdgeInsets.only(bottom: 20)),
    ],
  );
}

class MessageCard extends StatelessWidget {
  const MessageCard({
    super.key,
    required this.message,
    this.onReplay,
    this.onPause,
    this.onSkip,
    this.onCancel,
    this.paused = false,
  });
  final Message message;
  final bool paused;
  final ValueChanged<Message>? onReplay, onPause, onSkip, onCancel;
  @override
  Widget build(BuildContext context) {
    final user = message.role == 'user';
    final speech = message.role == 'claude' || message.role == 'daemon';
    final color = user
        ? StudioColors.accent(context)
        : StudioColors.agentAccent(context);
    final scheme = Theme.of(context).colorScheme;
    final chip = messageChip(message.role, message.status);
    final state = messageState(message.role, message.status);
    return Container(
      decoration: BoxDecoration(
        color: Color.alphaBlend(color.withValues(alpha: .04), scheme.surface),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: .3)),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (!user && message.voice.isNotEmpty) ...[
                VoiceAvatar(voice: message.voice, size: 26),
                const SizedBox(width: 8),
              ],
              Expanded(child: Eyebrow(message.author, color: color)),
              if (speech &&
                  const {
                    'played',
                    'unheard',
                    'skipped',
                    'error',
                  }.contains(state) &&
                  message.text.trim().isNotEmpty &&
                  onReplay != null)
                IconButton(
                  tooltip: 'Play this message again',
                  onPressed: () => onReplay!(message),
                  icon: const Icon(Icons.replay, size: 17),
                ),
              if (speech && state == 'playing') ...[
                if (onPause != null)
                  IconButton(
                    tooltip: paused ? 'Resume playback' : 'Pause playback',
                    onPressed: () => onPause!(message),
                    icon: Icon(
                      paused ? Icons.play_arrow : Icons.pause,
                      size: 17,
                    ),
                  ),
                if (onSkip != null)
                  IconButton(
                    tooltip: 'Skip the rest of this message',
                    onPressed: () => onSkip!(message),
                    icon: const Icon(Icons.skip_next, size: 17),
                  ),
              ],
              if (user &&
                  const {
                    'ready',
                    'undelivered',
                    'unavailable',
                    'rejected',
                  }.contains(state) &&
                  onCancel != null)
                IconButton(
                  tooltip: 'Recall this message',
                  onPressed: () => onCancel!(message),
                  icon: const Icon(Icons.close, size: 17),
                ),
              if (message.time.isNotEmpty)
                Text(
                  message.time,
                  style: TextStyle(
                    fontSize: 10,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 9),
          Text(message.text, style: const TextStyle(fontSize: 14, height: 1.5)),
          if (message.status.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Row(
                children: [
                  Icon(
                    chip.$1 == 'done'
                        ? Icons.check
                        : chip.$1 == 'spoken'
                        ? Icons.play_arrow
                        : chip.$1 == 'warn' || chip.$1 == 'fail'
                        ? Icons.error_outline
                        : Icons.circle_outlined,
                    size: 12,
                    color: color,
                  ),
                  const SizedBox(width: 4),
                  Flexible(
                    child: Text(
                      chip.$2.replaceFirst(RegExp(r'^[^A-Z]+'), ''),
                      style: TextStyle(
                        fontSize: 9,
                        letterSpacing: .6,
                        color: color,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class MessagesView extends StatelessWidget {
  const MessagesView({
    super.key,
    required this.messages,
    this.onReplay,
    this.onPause,
    this.onSkip,
    this.onCancel,
    this.pausedId = 0,
  });
  final List<Message> messages;
  final ValueChanged<Message>? onReplay, onPause, onSkip, onCancel;
  final int pausedId;
  @override
  Widget build(BuildContext context) => messages.isEmpty
      ? const Center(child: Text('Ready when you are'))
      : ListView.builder(
          reverse: true,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          itemCount: messages.length,
          itemBuilder: (context, index) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: MessageCard(message: messages[messages.length - index - 1]),
          ),
        );
}

class TalkView extends StatelessWidget {
  const TalkView({
    super.key,
    required this.snapshot,
    this.agent,
    this.held = false,
    this.connected = true,
    required this.onHold,
    required this.onRelease,
    required this.onToggle,
    required this.onAuto,
    required this.onMute,
    required this.onStop,
    this.onReplay,
    this.onPause,
    this.onSkip,
    this.onCancel,
    this.pausedId = 0,
  });
  final Snapshot snapshot;
  final Agent? agent;
  final bool held, connected;
  final VoidCallback onHold, onRelease, onToggle, onMute, onStop;
  final ValueChanged<bool> onAuto;
  final ValueChanged<Message>? onReplay, onPause, onSkip, onCancel;
  final int pausedId;
  @override
  Widget build(BuildContext context) {
    final enabled =
        connected && agent != null && agent!.state != AgentState.offline;
    final ptt = enabled && !snapshot.auto && !snapshot.muted;
    final scheme = Theme.of(context).colorScheme;
    final accent = StudioColors.accent(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 14),
          child: Row(
            children: [
              VoiceAvatar(voice: agent?.voice ?? '', size: 58),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      agent?.name ?? 'Choose an agent',
                      style: const TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 5),
                    if (agent != null) AgentStateChip(agent: agent!),
                  ],
                ),
              ),
              if (agent != null) Eyebrow(agent!.harness),
            ],
          ),
        ),
        Divider(height: 1, color: scheme.outline),
        Expanded(
          child: MessagesView(
            onReplay: onReplay,
            onPause: onPause,
            onSkip: onSkip,
            onCancel: onCancel,
            pausedId: pausedId,
            messages: snapshot.messages
                .where((m) => m.agentId == agent?.id)
                .toList(),
          ),
        ),
        Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          decoration: BoxDecoration(
            color: scheme.surface,
            border: Border(top: BorderSide(color: scheme.outline)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  const Eyebrow('Turn detection'),
                  const Spacer(),
                  _Choice(
                    label: 'Auto',
                    selected: snapshot.auto,
                    onTap: enabled ? () => onAuto(true) : null,
                  ),
                  const SizedBox(width: 6),
                  _Choice(
                    label: 'Push to talk',
                    selected: !snapshot.auto,
                    onTap: enabled ? () => onAuto(false) : null,
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: enabled ? onMute : null,
                      icon: Icon(
                        snapshot.muted
                            ? Icons.mic_off_outlined
                            : Icons.mic_none,
                        size: 17,
                      ),
                      label: Text(
                        snapshot.muted ? 'Unmute mic' : 'Mute mic',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: connected ? onStop : null,
                      icon: const Icon(Icons.stop_rounded, size: 17),
                      label: const Text(
                        'Stop speech',
                        style: TextStyle(fontSize: 12),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Listener(
                onPointerDown: ptt ? (_) => onHold() : null,
                onPointerUp: (_) => onRelease(),
                onPointerCancel: (_) => onRelease(),
                child: Semantics(
                  button: true,
                  label: 'Hold to control desktop microphone',
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: held
                          ? accent
                          : accent.withValues(alpha: ptt ? 0.1 : 0.03),
                      border: Border.all(color: ptt ? accent : scheme.outline),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          held ? Icons.graphic_eq : Icons.mic_none,
                          color: held
                              ? const Color(0xff132624)
                              : ptt
                              ? accent
                              : scheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          held
                              ? 'Release to send'
                              : snapshot.auto
                              ? 'Auto detection on'
                              : 'Hold to talk',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: held
                                ? const Color(0xff132624)
                                : ptt
                                ? accent
                                : scheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              SizedBox(
                height: 38,
                child: TextButton(
                  onPressed: ptt ? onToggle : null,
                  child: Text(
                    held ? 'Finish recording' : 'Tap to start instead',
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
              ),
              const AudioNotice(),
            ],
          ),
        ),
      ],
    );
  }
}

class _Choice extends StatelessWidget {
  const _Choice({required this.label, required this.selected, this.onTap});
  final String label;
  final bool selected;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => OutlinedButton(
    onPressed: onTap,
    style: OutlinedButton.styleFrom(
      minimumSize: const Size(48, 40),
      padding: const EdgeInsets.symmetric(horizontal: 9),
      side: BorderSide(
        color: selected
            ? StudioColors.accent(context)
            : Theme.of(context).colorScheme.outline,
      ),
      backgroundColor: selected
          ? StudioColors.accent(context).withValues(alpha: .08)
          : null,
    ),
    child: Text(label, style: const TextStyle(fontSize: 11)),
  );
}

class ConnectionSettings extends StatelessWidget {
  const ConnectionSettings({
    super.key,
    required this.address,
    required this.onConnect,
    required this.onDemo,
    this.busy = false,
    this.error,
  });
  final TextEditingController address;
  final VoidCallback onConnect, onDemo;
  final bool busy;
  final String? error;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      const Eyebrow('Settings'),
      const SizedBox(height: 7),
      Text(
        'Your desktop',
        style: Theme.of(context).textTheme.headlineMedium
            ?.copyWith(fontWeight: FontWeight.w600),
      ),
      const SizedBox(height: 8),
      Text(
        'The same agents. A little closer.',
        style: TextStyle(
          fontSize: 13,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
      const SizedBox(height: 24),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.computer_outlined, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'Desktop connection',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              TextField(
                controller: address,
                keyboardType: TextInputType.url,
                autocorrect: false,
                style: const TextStyle(fontSize: 13),
                decoration: const InputDecoration(
                  labelText: 'Daemon address',
                  hintText: 'http://192.168.1.20:7765',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: busy ? null : onConnect,
                  child: Text(busy ? 'Connecting…' : 'Connect to desktop'),
                ),
              ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    error!,
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              const SizedBox(height: 14),
              const Text(
                'Use an already reachable desktop on your trusted network.',
                style: TextStyle(fontSize: 12, height: 1.5),
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 16),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Eyebrow('Audio'),
              const SizedBox(height: 12),
              const AudioNotice(),
              const SizedBox(height: 10),
              Text(
                'Speak near your computer. Phone audio and pairing are not available in this preview.',
                style: TextStyle(
                  fontSize: 12,
                  height: 1.5,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 16),
      OutlinedButton.icon(
        onPressed: onDemo,
        icon: const Icon(Icons.explore_outlined, size: 18),
        label: const Text('Explore demo agents'),
      ),
      const SizedBox(height: 16),
      Text(
        'Current daemon connections are not authenticated. This app does not change your desktop’s network settings.',
        style: TextStyle(
          fontSize: 11,
          height: 1.5,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    ],
  );
}
