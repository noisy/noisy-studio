import 'package:flutter/material.dart';

import '../core/models.dart';

ThemeData studioTheme(Brightness brightness) => ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color(0xffb8ef65),
    brightness: brightness,
  ),
  useMaterial3: true,
);

class AudioNotice extends StatelessWidget {
  const AudioNotice({super.key});
  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(12),
      child: Row(
        children: [
          Icon(Icons.computer),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Sound stays on your desktop\nUse your computer’s microphone and speakers.',
            ),
          ),
        ],
      ),
    ),
  );
}

class AgentsView extends StatelessWidget {
  const AgentsView({super.key, required this.snapshot, required this.onSelect});
  final Snapshot snapshot;
  final ValueChanged<Agent> onSelect;
  @override
  Widget build(BuildContext context) => snapshot.agents.isEmpty
      ? const Center(
          child: Text(
            'No conversations yet\nOpen an agent on your desktop.',
            textAlign: TextAlign.center,
          ),
        )
      : GridView.builder(
          padding: const EdgeInsets.all(16),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
            maxCrossAxisExtent: 230,
            mainAxisExtent: 184,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: snapshot.agents.length,
          itemBuilder: (context, i) {
            final agent = snapshot.agents[i];
            final speaking = agent.state == AgentState.speaking;
            return Card(
              color: speaking
                  ? Theme.of(context).colorScheme.primaryContainer
                  : null,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () => onSelect(agent),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Badge(
                        isLabelVisible: agent.unread > 0,
                        label: Text('${agent.unread} queued'),
                        child: CircleAvatar(
                          radius: 27,
                          child: Text(
                            agent.name.substring(0, 1),
                            style: const TextStyle(fontSize: 26),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        agent.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text('${agent.harness} · ${agent.state.name}'),
                      if (speaking) const Icon(Icons.graphic_eq, size: 20),
                    ],
                  ),
                ),
              ),
            );
          },
        );
}

class MessagesView extends StatelessWidget {
  const MessagesView({super.key, required this.messages});
  final List<Message> messages;
  @override
  Widget build(BuildContext context) => messages.isEmpty
      ? const Center(child: Text('Your conversation will appear here.'))
      : ListView.builder(
          reverse: true,
          padding: const EdgeInsets.all(16),
          itemCount: messages.length,
          itemBuilder: (context, index) {
            final m = messages[messages.length - index - 1];
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      m.author,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(m.text),
                  ],
                ),
              ),
            );
          },
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
  });
  final Snapshot snapshot;
  final Agent? agent;
  final bool held, connected;
  final VoidCallback onHold, onRelease, onToggle, onMute, onStop;
  final ValueChanged<bool> onAuto;
  @override
  Widget build(BuildContext context) {
    final enabled =
        connected && agent != null && agent!.state != AgentState.offline;
    return Column(
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 12),
          child: AudioNotice(),
        ),
        Expanded(
          child: MessagesView(
            messages: snapshot.messages
                .where((m) => m.agentId == agent?.id)
                .toList(),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                agent?.name ?? 'Choose an agent',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Auto detection'),
                value: snapshot.auto,
                onChanged: enabled ? onAuto : null,
              ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: enabled ? onMute : null,
                      icon: Icon(snapshot.muted ? Icons.mic_off : Icons.mic),
                      label: Text(snapshot.muted ? 'Unmute' : 'Mute'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: connected ? onStop : null,
                      icon: const Icon(Icons.stop),
                      label: const Text('Stop speech'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Listener(
                onPointerDown: enabled && !snapshot.auto && !snapshot.muted
                    ? (_) => onHold()
                    : null,
                onPointerUp: (_) => onRelease(),
                onPointerCancel: (_) => onRelease(),
                child: Semantics(
                  button: true,
                  label: 'Hold to control desktop microphone',
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: enabled && !snapshot.auto && !snapshot.muted
                          ? Theme.of(context).colorScheme.primaryContainer
                          : Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: Text(
                      held ? 'Recording · release to send' : 'Hold to talk',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                ),
              ),
              TextButton(
                onPressed: enabled && !snapshot.auto && !snapshot.muted
                    ? onToggle
                    : null,
                child: Text(held ? 'Finish recording' : 'Tap to start instead'),
              ),
            ],
          ),
        ),
      ],
    );
  }
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
      const AudioNotice(),
      const SizedBox(height: 20),
      Text('Your desktop', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 12),
      TextField(
        controller: address,
        keyboardType: TextInputType.url,
        autocorrect: false,
        decoration: const InputDecoration(
          labelText: 'Daemon address',
          hintText: 'http://192.168.1.20:7765',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: busy ? null : onConnect,
        child: Text(busy ? 'Connecting…' : 'Connect'),
      ),
      if (error != null)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(
            error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ),
      TextButton(onPressed: onDemo, child: const Text('Explore demo agents')),
      const Divider(height: 36),
      const ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(Icons.link_off),
        title: Text('Pairing · coming later'),
        subtitle: Text(
          'Pairing codes and phone microphone audio are not available yet. This preview requires an already reachable daemon. It does not change your desktop’s network settings.',
        ),
      ),
      const SizedBox(height: 12),
      const Text(
        'Only connect to your own trusted desktop. Current daemon connections are not authenticated.',
      ),
    ],
  );
}
