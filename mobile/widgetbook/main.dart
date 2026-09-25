import 'package:flutter/material.dart';
import 'package:widgetbook/widgetbook.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';

void main() => runApp(const Catalog());

class Catalog extends StatelessWidget {
  const Catalog({super.key});
  @override
  Widget build(BuildContext context) => Widgetbook.material(
    directories: [
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
                    messages: data.messages,
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
