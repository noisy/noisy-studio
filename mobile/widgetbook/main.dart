import 'package:flutter/material.dart';
import 'package:widgetbook/widgetbook.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';
import 'package:noisy_studio_mobile/main.dart' show Companion;

void main() => runApp(const Catalog());

class Catalog extends StatelessWidget {
  const Catalog({super.key});
  @override
  Widget build(BuildContext context) => Widgetbook.material(
    directories: [
      WidgetbookComponent(
        name: 'Mobile app',
        useCases: [
          WidgetbookUseCase(
            name: 'Interactive companion',
            builder: (_) => const Companion(),
          ),
        ],
      ),
      WidgetbookComponent(
        name: 'Message contracts',
        useCases: [
          for (final status in [
            'ready — awaiting pickup',
            'transcribing…',
            'unavailable — reconnect',
            'playing through speakers…',
            'played',
            'unheard — voice muted',
          ])
            WidgetbookUseCase(
              name: status,
              builder: (_) => MessageStory(status: status),
            ),
        ],
      ),
      WidgetbookComponent(
        name: 'Agents',
        useCases: [
          for (final count in [0, 2, 4, 7])
            WidgetbookUseCase(
              name: '$count agents',
              builder: (_) => AgentsView(
                snapshot: fixture(count: count),
                onSelect: (_) {},
              ),
            ),
        ],
      ),
      WidgetbookComponent(
        name: 'Talk',
        useCases: [
          for (final state in [
            'Idle',
            'Holding',
            'Speaking',
            'Muted',
            'Offline',
          ])
            WidgetbookUseCase(
              name: state,
              builder: (_) {
                final data = fixture(
                  state: state == 'Offline'
                      ? AgentState.offline
                      : state == 'Speaking'
                      ? AgentState.speaking
                      : AgentState.waiting,
                );
                return TalkView(
                  snapshot: Snapshot(
                    agents: data.agents,
                    messages: data.messages
                        .map(
                          (m) =>
                              state == 'Speaking' &&
                                  m.role == 'claude' &&
                                  m.agentId == data.activeId
                              ? Message(
                                  m.agentId,
                                  m.author,
                                  m.text,
                                  id: m.id,
                                  role: m.role,
                                  voice: m.voice,
                                  status: 'playing through speakers…',
                                  time: m.time,
                                )
                              : m,
                        )
                        .toList(),
                    activeId: data.activeId,
                    muted: state == 'Muted',
                  ),
                  agent: data.agents.first,
                  held: state == 'Holding',
                  connected: state != 'Offline',
                  onHold: () {},
                  onRelease: () {},
                  onToggle: () {},
                  onAuto: (_) {},
                  onMute: () {},
                  onStop: () {},
                );
              },
            ),
        ],
      ),
      WidgetbookComponent(
        name: 'Recent',
        useCases: [
          WidgetbookUseCase(
            name: 'Messages',
            builder: (_) => MessagesView(messages: fixture().messages),
          ),
        ],
      ),
      WidgetbookComponent(
        name: 'Settings',
        useCases: [
          WidgetbookUseCase(
            name: 'Pairing unavailable',
            builder: (_) => const SettingsStory(),
          ),
        ],
      ),
    ],
    addons: [
      MaterialThemeAddon(
        themes: [
          WidgetbookTheme(name: 'Dark', data: studioTheme(Brightness.dark)),
          WidgetbookTheme(name: 'Light', data: studioTheme(Brightness.light)),
        ],
      ),
      ViewportAddon([
        const ViewportData(
          name: 'Small phone',
          pixelRatio: 2,
          platform: TargetPlatform.android,
          width: 360,
          height: 740,
        ),
        const ViewportData(
          name: 'Large phone',
          pixelRatio: 3,
          platform: TargetPlatform.iOS,
          width: 430,
          height: 932,
        ),
      ]),
    ],
    appBuilder: (context, child) => Scaffold(body: SafeArea(child: child)),
  );
}

class SettingsStory extends StatefulWidget {
  const SettingsStory({super.key});
  @override
  State<SettingsStory> createState() => _SettingsStoryState();
}

class _SettingsStoryState extends State<SettingsStory> {
  final address = TextEditingController();
  @override
  void dispose() {
    address.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      ConnectionSettings(address: address, onConnect: () {}, onDemo: () {});
}

class MessageStory extends StatefulWidget {
  const MessageStory({super.key, required this.status});
  final String status;
  @override
  State<MessageStory> createState() => _MessageStoryState();
}

class _MessageStoryState extends State<MessageStory> {
  String event = 'Actions emit the same message identity as desktop.';
  @override
  Widget build(BuildContext context) {
    final user =
        widget.status.startsWith('ready') ||
        widget.status.startsWith('transcribing') ||
        widget.status.startsWith('unavailable');
    final message = Message(
      'a1',
      user ? 'You' : 'Lux',
      user
          ? 'Could you check the latest changes?'
          : 'The checks passed. I’m reviewing the final changes.',
      id: 91,
      role: user ? 'user' : 'claude',
      voice: user ? '' : 'lux',
      status: widget.status,
      time: '14:32',
    );
    void emit(String action, Message value) =>
        setState(() => event = 'Preview event: $action · message ${value.id}');
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          MessageCard(
            message: message,
            onReplay: (m) => emit('replay', m),
            onPause: (m) => emit('pause', m),
            onSkip: (m) => emit('skip', m),
            onCancel: (m) => emit('cancel', m),
          ),
          const SizedBox(height: 16),
          Text(event, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}
