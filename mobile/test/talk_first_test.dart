import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/talk_first.dart';

const a1 = TalkAgent(
  id: 'conversation-1',
  name: 'A very long conversation name that must fit on a small phone',
  topic: 'A very long conversation name that must fit on a small phone',
  voice: 'unknown',
);
Widget view({
  List<TalkAgent> agents = const [a1],
  List<Message> messages = const [],
  int tab = 0,
  bool enabled = true,
  ValueChanged<String>? hold,
  ValueChanged<bool>? finish,
}) => MaterialApp(
  home: TalkFirstView(
    agents: agents,
    messages: messages,
    selectedId: 'deleted-conversation',
    auto: true,
    onSelect: (_) {},
    onMode: (_) {},
    onHold: hold ?? (_) {},
    onFinish: finish ?? (_) {},
    settings: const Text('Connection settings'),
    enabled: enabled,
    initialTab: tab,
  ),
);

void main() {
  testWidgets(
    'empty crew and deleted recipient remain usable without fake agents',
    (tester) async {
      await tester.pumpWidget(view(agents: []));
      expect(find.textContaining('No open conversations'), findsOneWidget);
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.text('Connection settings'), findsOneWidget);
    },
  );
  testWidgets('closed and system messages have no Reply action', (
    tester,
  ) async {
    await tester.pumpWidget(
      view(
        tab: 1,
        messages: const [
          Message('closed-2', 'Closed', 'Old conversation', id: 1),
          Message('', 'System', 'Daemon restarted', id: 2, role: 'daemon'),
          Message('conversation-1', 'Agent', 'Ready', id: 3),
        ],
      ),
    );
    expect(find.byKey(const ValueKey('reply-1')), findsNothing);
    expect(find.byKey(const ValueKey('reply-2')), findsNothing);
    expect(find.byKey(const ValueKey('reply-3')), findsOneWidget);
  });
  testWidgets(
    'small phone supports long conversation and unknown avatar in detail',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 740));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(view());
      await tester.tap(find.byKey(const ValueKey('portrait-conversation-1')));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.byKey(const ValueKey('talk-conversation-1')), findsOneWidget);
    },
  );
  testWidgets(
    'pending routing disables new starts but preserves original release',
    (tester) async {
      final events = <String>[];
      var enabled = true;
      late StateSetter change;
      await tester.pumpWidget(
        StatefulBuilder(
          builder: (_, set) {
            change = set;
            return view(
              enabled: enabled,
              hold: (id) {
                events.add(id);
                change(() => enabled = false);
              },
              finish: (cancel) => events.add('end $cancel'),
            );
          },
        ),
      );
      final gesture = await tester.startGesture(
        tester.getCenter(find.byKey(const ValueKey('portrait-conversation-1'))),
      );
      await tester.pump(const Duration(milliseconds: 600));
      await tester.pump();
      await gesture.up();
      await tester.pumpAndSettle();
      expect(events, ['conversation-1', 'end false']);
    },
  );
  testWidgets('offline hold cannot start recording', (tester) async {
    final events = <String>[];
    await tester.pumpWidget(view(enabled: false, hold: events.add));
    await tester.longPress(
      find.byKey(const ValueKey('portrait-conversation-1')),
    );
    expect(events, isEmpty);
  });
}
